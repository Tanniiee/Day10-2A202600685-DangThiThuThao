# Báo Cáo Lab Day 10 — Data Pipeline & Data Observability

**Sinh viên:** Đặng Thị Thu Thảo — 2A202600685  
**Ngày thực hiện:** 10/06/2026  
**Model LLM:** GPT-4o-mini (OpenAI)  
**Embedding model:** sentence-transformers/all-MiniLM-L6-v2  
**Vector store:** ChromaDB (persistent)

---

## 1. Tổng quan

Lab này xây dựng một ETL pipeline hoàn chỉnh cho hệ thống RAG (Retrieval-Augmented Generation) trên dữ liệu bài báo học thuật. Mục tiêu chính là **chứng minh nguyên lý Data Observability**: chất lượng dữ liệu ảnh hưởng trực tiếp đến hiệu suất của agent, và việc giám sát + sửa chữa dữ liệu có thể phục hồi hoàn toàn performance mà không cần thay đổi model.

Pipeline được chia làm 2 pha:
- **Phase 1 (Baseline):** Thu thập → làm sạch → embed → evaluate → report
- **Phase 2 (Corruption):** Corrupt → evaluate → repair → compare

---

## 2. Cấu trúc Project

```
src/
├── core/           # config, utils
├── ingestion/      # crossref.py, cleaning.py, corruption.py
├── retrieval/      # embeddings.py, index.py, llm.py, agent.py, qa.py
├── evaluation/     # testset.py, metrics.py
├── observability/  # quality.py, reporting.py
└── pipelines/      # phase1.py, corruption_flow.py

data/
├── raw/            # crossref_response.json, crossref_records.json
├── clean/          # papers_clean.csv/json (+ corrupted, repaired)
├── embeddings/     # ChromaDB manifests
├── chroma/         # vector store
├── eval/           # test_set.json
├── results/        # metrics, answers, corruption_log
├── quality/        # quality checks, freshness reports
└── reports/        # phase1_report.md, corruption_report.md

script/
├── run_phase1.py
└── run_corruption_flow.py
```

---

## 3. Phase 1 — Baseline Pipeline

### 3.1 Thu thập dữ liệu (`crossref.py`)

Dữ liệu được lấy từ **Crossref REST API** — nguồn metadata bài báo học thuật mở.

- **Endpoint:** `https://api.crossref.org/works`
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:2025-12-12, has-abstract:true`
- **Số records:** 24 papers

Mỗi `PaperRecord` gồm: `paper_id` (DOI), `title`, `summary` (abstract), `authors`, `categories`, `published`, `updated`, `abs_url`, `pdf_url`, `comment` (journal name).

Raw response được lưu tại `data/raw/crossref_response.json` để có thể replay mà không cần gọi lại API.

### 3.2 Làm sạch dữ liệu (`cleaning.py`)

Các bước transform được thực hiện:

| Bước | Mô tả |
|------|-------|
| Strip XML tags | Loại bỏ JATS tags (`<jats:p>`, `<jats:italic>`...) trong abstract từ Crossref |
| Normalize whitespace | Chuẩn hóa toàn bộ text fields |
| Filter invalid | Bỏ record thiếu `paper_id` hoặc `title` |
| Tính `age_days` | Số ngày từ ngày published đến ngày chạy pipeline |
| Helper columns | `authors_joined`, `categories_joined`, `summary_chars` |
| `text_for_embedding` | Ghép `Title + Authors + Categories + Published + Abstract + Journal` thành chuỗi context đầy đủ |
| Deduplication | Drop duplicate theo `paper_id` |
| Sort | Mới nhất lên đầu (sort by `published` descending) |

**Kết quả:** 24 records sạch, lưu tại `data/clean/papers_clean.csv`.

### 3.3 Embedding & Vector Store (`index.py`)

- Mỗi paper được embed cột `text_for_embedding` thành vector 384 chiều bằng `all-MiniLM-L6-v2`
- Nạp vào ChromaDB collection `papers-baseline` với cosine similarity
- Persist tại `data/chroma/`
- Khi query: câu hỏi được embed → tìm top-k paper gần nhất

### 3.4 Evaluation Set (`testset.py`)

Từ 24 papers, sinh 24 câu hỏi — 4 loại:

| Loại | Ví dụ câu hỏi | Ground truth |
|------|---------------|--------------|
| `summary` | "What is the paper 'X' about?" | Abstract |
| `authors` | "Who authored 'X'?" | Danh sách tác giả |
| `date` | "When was 'X' published?" | Ngày published |
| `categories` | "What categories does 'X' belong to?" | Subject list |

Mỗi sample có `ground_truth_doc_ids` để đánh giá retrieval hit/miss.

### 3.5 Kết quả Evaluation

| Metric | Giá trị | Ý nghĩa |
|--------|---------|---------|
| **Retrieval hit rate** | **100.0%** | Mọi câu hỏi đều retrieve đúng paper |
| **Mean token F1** | **0.862** | Câu trả lời khớp 86.2% từ với ground truth |
| **Judge accuracy** | **70.8%** | GPT-4o-mini đánh giá 70.8% câu trả lời đúng |
| **Mean judge score** | **4.33/5** | Điểm trung bình khá cao |

### 3.6 Data Quality & Freshness

**6/6 quality checks PASS:**

| Check | Kết quả |
|-------|---------|
| row_count ≥ 5 | ✅ 24 rows |
| paper_id not null | ✅ 0 null |
| paper_id unique | ✅ 0 duplicate |
| title not null | ✅ 0 null |
| summary length ok | ✅ chỉ 1 row ngắn (4.2%) |
| freshness ok | ✅ 0 stale rows |

**Freshness:** Latest paper: `2026-06-02` · Oldest: `2025-12-19` · `is_fresh = True`

---

## 4. Phase 2 — Corruption Flow

### 4.1 Mục đích

Simulate các tình huống data corruption thực tế để đo impact lên RAG agent, sau đó chứng minh repair có thể phục hồi performance.

### 4.2 Các loại Corruption (`corruption.py`)

| Loại | Rows affected | Tác động |
|------|:---:|---------|
| **Drop latest records** | −3 rows | Agent mất kiến thức về papers gần đây nhất |
| **Blank summary** | 3 rows | `text_for_embedding` mất nội dung chính → embedding sai |
| **Inject noise** | 2 rows | Chuỗi random thêm vào abstract → embedding bị nhiễu |
| **Truncate title** | 2 rows | Title bị cắt còn 15 ký tự → lookup by title thất bại |
| **Stale published date** | 2 rows | Published year lùi 2 năm → freshness alarm |
| **Add duplicates** | +1 row | `paper_id_unique` check FAIL → bias ranking |

**Kết quả:** 24 rows → 22 rows (sau corruption)

### 4.3 Kết quả sau Corruption

| Metric | Baseline | Corrupted | Δ |
|--------|:--------:|:---------:|:--:|
| Retrieval hit rate | 100.0% | **87.5%** | **−12.5%** |
| Mean token F1 | 0.862 | **0.717** | **−0.145** |
| Judge accuracy | 70.8% | 70.8% | 0% |
| Mean judge score | 4.333 | 4.125 | −0.208 |
| Quality checks | 6/6 ✅ | **5/6 ❌** | 1 FAIL |
| Stale rows | 0 | **2** | +2 |

**Quality check FAIL:** `paper_id_unique` → `duplicate_paper_ids=1`

Chỉ 6 thao tác nhỏ đã làm **Retrieval Hit Rate giảm 12.5%** và Token F1 giảm 14.5%. Agent bắt đầu trả lời sai cho 3/24 câu hỏi — những câu liên quan đến papers bị drop hoặc abstract bị xóa.

### 4.4 Repair từ Raw Source

Thay vì gọi lại API, pipeline re-clean trực tiếp từ `data/raw/crossref_records.json`:

```
load_raw_records() → build_clean_dataframe() → LocalEmbeddingIndex.build()
```

### 4.5 Kết quả sau Repair

| Metric | Baseline | Corrupted | Repaired | Recovery |
|--------|:--------:|:---------:|:--------:|:--------:|
| Retrieval hit rate | 100.0% | 87.5% | **100.0%** | ✅ Full |
| Mean token F1 | 0.862 | 0.717 | **0.862** | ✅ Full |
| Judge accuracy | 70.8% | 70.8% | **70.8%** | ✅ Same |
| Quality checks | 6/6 | 5/6 | **6/6** | ✅ Full |
| Stale rows | 0 | 2 | **0** | ✅ Full |

**Tất cả metrics phục hồi hoàn toàn** mà không cần thay đổi model hay re-fetch API.

---

## 5. Kết luận

### Nguyên lý Data Observability được chứng minh

> **"Không phải model kém — mà là data xấu."**

Thí nghiệm này cho thấy:

1. **Data quality → RAG quality:** Chỉ 3 papers bị drop + 3 abstract bị blank đã làm hệ thống mất 12.5% khả năng tìm đúng tài liệu. Agent không "biết" mình đang dùng data xấu.

2. **Monitor early, fix fast:** Quality checks phát hiện ngay `paper_id_unique FAIL` và stale dates — đây là signal để trigger repair trước khi user nhận ra agent đang trả lời sai.

3. **Raw source là source of truth:** Repair từ raw records (không cần re-fetch API) khôi phục hoàn toàn mọi metrics. Điều này nhấn mạnh tầm quan trọng của việc lưu trữ raw data.

4. **Data Observability > Model tuning:** Thời gian giải quyết vấn đề bằng cách fix data nhanh hơn và hiệu quả hơn nhiều so với fine-tune hay thay đổi model.

### Artifacts đầu ra

| File | Mô tả |
|------|-------|
| `data/raw/crossref_response.json` | Raw API response |
| `data/raw/crossref_records.json` | Parsed records |
| `data/clean/papers_clean.csv` | Baseline clean dataset |
| `data/clean/papers_clean_corrupted.csv` | Corrupted dataset |
| `data/clean/papers_clean_repaired.csv` | Repaired dataset |
| `data/eval/test_set.json` | 24 evaluation questions |
| `data/results/baseline_metrics.json` | Baseline evaluation metrics |
| `data/results/corrupted_metrics.json` | Corrupted evaluation metrics |
| `data/results/repaired_metrics.json` | Repaired evaluation metrics |
| `data/results/corruption_log.json` | Log các thao tác corruption |
| `data/quality/baseline_quality.json` | Quality checks baseline |
| `data/quality/corrupted_quality.json` | Quality checks corrupted |
| `data/quality/freshness_report.json` | Freshness report |
| `data/reports/phase1_report.md` | Báo cáo Phase 1 |
| `data/reports/corruption_report.md` | Báo cáo so sánh 3 trạng thái |
| `app.py` | Streamlit dashboard (tab-based) |
| `app2.py` | Streamlit dashboard (narrative/dark theme) |
