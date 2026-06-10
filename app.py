"""
Streamlit App: Nguyên Lý Data Observability
Coral theme
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── paths ─────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# ── page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Nguyên Lý Data Observability",
    page_icon="🔍",
    layout="wide",
)

# ── colors ────────────────────────────────────────────────────────
CORAL  = "#FF7043"
CDARK  = "#E64A19"
CBG    = "#FFF3EF"
GREEN  = "#43A047"
RED    = "#E53935"
GRAY   = "#78909C"
DARK   = "#1C1C2E"

# ── CSS ───────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: #FAFAFA; }}

.hero {{
    background: linear-gradient(135deg, {CORAL}, {CDARK});
    border-radius: 14px; padding: 2rem 2.5rem; color: white; margin-bottom: 1.2rem;
}}
.hero h1 {{ font-size: 2rem; font-weight: 700; margin: 0 0 .3rem; }}
.hero p  {{ font-size: .95rem; opacity: .88; margin: 0; }}

.sec {{ font-size: 1.1rem; font-weight: 700; color: {CDARK};
        border-left: 5px solid {CORAL}; padding-left: .6rem;
        margin: 1.4rem 0 .7rem; }}

.card {{
    background: white; border-radius: 12px; padding: 1.1rem 1.3rem;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
    text-align: center; border-top: 4px solid {CORAL};
}}
.card .lbl  {{ font-size: .72rem; color: {GRAY}; font-weight: 600;
               text-transform: uppercase; letter-spacing: .05em; }}
.card .val  {{ font-size: 2rem; font-weight: 700; color: {DARK}; }}
.card .dlt  {{ font-size: .82rem; margin-top: .15rem; }}
.up   {{ color: {GREEN}; }}
.dn   {{ color: {RED}; }}
.neut {{ color: {GRAY}; }}

.badge  {{ display: inline-block; border-radius: 20px; padding: .2rem .65rem;
           font-size: .75rem; font-weight: 600; }}
.b-base {{ background: #E3F2FD; color: #1565C0; }}
.b-cor  {{ background: #FFEBEE; color: {RED}; }}
.b-rep  {{ background: #E8F5E9; color: #2E7D32; }}

.pipe {{
    background: white; border-radius: 10px; padding: .9rem 1.1rem;
    border-left: 4px solid {CORAL}; margin-bottom: .45rem;
    box-shadow: 0 1px 5px rgba(0,0,0,.06);
}}
.pipe .pnum {{ font-size: .7rem; color: {CORAL}; font-weight: 700; }}
.pipe .ptitle {{ font-size: .92rem; font-weight: 600; color: {DARK}; }}
.pipe .pdesc  {{ font-size: .8rem; color: #607D8B; margin-top: .15rem; }}

.opbox {{
    border-radius: 10px; padding: .9rem 1.1rem; margin-bottom: .6rem;
}}

.stTabs [data-baseweb="tab"] {{ font-weight: 600 !important; }}
.stTabs [aria-selected="true"] {{
    background: {CBG} !important; color: {CDARK} !important;
}}
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────
def load_json(rel: str):
    p = DATA / rel
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def load_csv(rel: str) -> pd.DataFrame:
    p = DATA / rel
    if p.exists():
        try:
            return pd.read_csv(p)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def pct(v):
    return f"{v:.1%}" if v is not None else "N/A"


def flt(v, d=3):
    return f"{v:.{d}f}" if v is not None else "N/A"


def delta_html(new, ref, as_pct=True):
    if new is None or ref is None:
        return '<span class="neut">–</span>'
    d = new - ref
    if abs(d) < 0.001:
        return '<span class="neut">≈ 0</span>'
    sign = "+" if d > 0 else ""
    cls = "up" if d > 0 else "dn"
    txt = pct(d) if as_pct else flt(d)
    return f'<span class="{cls}">{sign}{txt}</span>'


# ── load data ─────────────────────────────────────────────────────
bm = load_json("results/baseline_metrics.json")
cm = load_json("results/corrupted_metrics.json")
rm = load_json("results/repaired_metrics.json")
bq = load_json("quality/baseline_quality.json")
cq = load_json("quality/corrupted_quality.json")
rq = load_json("quality/repaired_quality.json")
fr = load_json("quality/freshness_report.json")
cl = load_json("results/corruption_log.json")
ba = load_json("results/baseline_answers.json")
ca = load_json("results/corrupted_answers.json")
df_clean = load_csv("clean/papers_clean.csv")
df_corr  = load_csv("clean/papers_clean_corrupted.csv")

if not isinstance(ba, list): ba = []
if not isinstance(ca, list): ca = []

# ── hero ──────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🔍 Nguyên Lý Data Observability</h1>
  <p>RAG pipeline: thu thập → làm sạch → embed → evaluate &nbsp;·&nbsp;
     Chứng minh: <strong>data xấu → agent kém · fix data → agent phục hồi</strong></p>
</div>
""", unsafe_allow_html=True)

# ── tabs ──────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs([
    "📊 Tổng quan",
    "⚙️ Pipeline",
    "🔬 Metrics",
    "💀 Corruption",
    "💬 Q&A Trace",
])


# ══════════════════════════════════════════════════════════════════
# TAB 1 – TỔNG QUAN
# ══════════════════════════════════════════════════════════════════
with t1:
    st.markdown('<div class="sec">Kết quả 3 giai đoạn</div>', unsafe_allow_html=True)

    def three_cards(label, key, as_pct=True):
        bv = bm.get(key)
        cv = cm.get(key)
        rv = rm.get(key)
        fmt = pct if as_pct else flt
        c1, c2, c3 = st.columns(3)
        for col, title, v, badge, ref in [
            (c1, "Baseline",  bv, '<span class="badge b-base">CLEAN</span>',   None),
            (c2, "Corrupted", cv, '<span class="badge b-cor">CORRUPTED</span>', bv),
            (c3, "Repaired",  rv, '<span class="badge b-rep">REPAIRED</span>',  bv),
        ]:
            with col:
                st.markdown(f"""
                <div class="card" style="border-top-color:{'#FF7043' if title=='Baseline' else ('#E53935' if title=='Corrupted' else '#43A047')}">
                  <div class="lbl">{title}</div>
                  <div class="val">{fmt(v)}</div>
                  <div class="dlt">{delta_html(v, ref, as_pct) if ref is not None else badge}</div>
                  <div style="font-size:.72rem;color:#90A4AE;margin-top:.3rem">{label}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    three_cards("Retrieval Hit Rate", "retrieval_hit_rate", True)
    three_cards("Mean Token F1",      "mean_token_f1",      False)
    three_cards("Judge Accuracy",     "judge_accuracy",     True)

    # insight
    bh = bm.get("retrieval_hit_rate", 1) or 1
    ch = cm.get("retrieval_hit_rate", 1) or 1
    drop = (bh - ch) * 100
    st.markdown(f"""
    <div style="background:{CBG};border-radius:12px;padding:1.1rem 1.4rem;
                border-left:5px solid {CORAL};margin-top:.5rem">
      <div style="font-weight:700;color:{CDARK}">💡 Kết luận</div>
      <div style="color:#37474F;margin-top:.4rem;font-size:.9rem">
        Corruption nhẹ (drop 3 papers, blank abstract, thêm noise...) làm
        <strong>Retrieval Hit Rate giảm {drop:.1f}%</strong> ({bh:.1%} → {ch:.1%}).
        Repair từ raw source → <strong>phục hồi hoàn toàn</strong>.
        <br>→ Data quality quan trọng hơn model — đây là nền tảng của <em>Data Observability</em>.
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec">Freshness</div>', unsafe_allow_html=True)
    fa, fb, fc, fd = st.columns(4)
    fa.metric("Latest Published",   fr.get("latest_published", "N/A"))
    fb.metric("Oldest Published",   fr.get("oldest_published", "N/A"))
    fc.metric("Stale Rows",         f"{fr.get('stale_rows', 0)} / {fr.get('total_rows', 0)}")
    fd.metric("Is Fresh",           "✅ Yes" if fr.get("is_fresh") else "❌ No")


# ══════════════════════════════════════════════════════════════════
# TAB 2 – PIPELINE
# ══════════════════════════════════════════════════════════════════
with t2:
    st.markdown('<div class="sec">Các bước Pipeline</div>', unsafe_allow_html=True)

    steps = [
        ("01", "Thu thập dữ liệu — crossref.py",
         "Gọi Crossref REST API · query: RAG/LLM papers · retry 429/503 · lưu raw JSON"),
        ("02", "Làm sạch & Transform — cleaning.py",
         "Strip JATS XML · normalize whitespace · tính age_days · tạo text_for_embedding · drop duplicates"),
        ("03", "Embedding — MiniLM + ChromaDB",
         "sentence-transformers/all-MiniLM-L6-v2 · 384-dim · cosine similarity · PersistentClient"),
        ("04", "Evaluation — metrics.py",
         "Test set 24 câu hỏi · retrieval hit rate · token F1 · GPT-4o-mini judge"),
        ("05", "Data Quality & Freshness — quality.py",
         "6 quality checks (null, unique, length, freshness) · JSON + Markdown report"),
        ("06", "Corruption — corruption.py",
         "Drop rows · blank summary · inject noise · truncate title · stale date · add duplicates"),
        ("07", "Repair & Compare — corruption_flow.py",
         "Re-clean từ raw · rebuild index · re-evaluate · comparison markdown report"),
    ]
    for num, title, desc in steps:
        st.markdown(f"""
        <div class="pipe">
          <div class="pnum">STEP {num}</div>
          <div class="ptitle">{title}</div>
          <div class="pdesc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    if not df_clean.empty:
        st.markdown('<div class="sec">Clean Dataset ({} papers)</div>'.format(len(df_clean)),
                    unsafe_allow_html=True)
        show = [c for c in ["title", "authors_joined", "published", "age_days", "summary_chars"] if c in df_clean.columns]
        st.dataframe(df_clean[show].head(10), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# TAB 3 – METRICS
# ══════════════════════════════════════════════════════════════════
with t3:
    st.markdown('<div class="sec">So sánh Metrics</div>', unsafe_allow_html=True)

    cats   = ["Baseline", "Corrupted", "Repaired"]
    colors = [CORAL, RED, GREEN]

    for key, label, as_pct in [
        ("retrieval_hit_rate", "Retrieval Hit Rate", True),
        ("mean_token_f1",      "Mean Token F1",      False),
        ("judge_accuracy",     "Judge Accuracy",     True),
        ("mean_judge_score",   "Mean Judge Score",   False),
    ]:
        vals = [bm.get(key, 0) or 0, cm.get(key, 0) or 0, rm.get(key, 0) or 0]
        texts = [pct(v) if as_pct else flt(v) for v in vals]
        ymax  = 1.1 if as_pct else max(vals) * 1.25 + 0.05

        fig = go.Figure(go.Bar(
            x=cats, y=vals, text=texts, textposition="outside",
            marker_color=colors, marker_line_color="white", marker_line_width=1.5,
            width=0.42,
        ))
        fig.update_layout(
            title=dict(text=label, font=dict(size=14, color=DARK)),
            yaxis=dict(range=[0, ymax], showgrid=True, gridcolor="#F0F0F0",
                       tickformat=".0%" if as_pct else ""),
            xaxis=dict(showgrid=False),
            plot_bgcolor="white", paper_bgcolor="white",
            height=260, margin=dict(t=45, b=10, l=10, r=10),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Quality checks
    st.markdown('<div class="sec">Data Quality Checks</div>', unsafe_allow_html=True)
    qcols = st.columns(3)
    for col, qd, badge_cls, label in [
        (qcols[0], bq, "b-base", "BASELINE"),
        (qcols[1], cq, "b-cor",  "CORRUPTED"),
        (qcols[2], rq, "b-rep",  "REPAIRED"),
    ]:
        with col:
            passed = qd.get("checks_passed", 0)
            total  = passed + qd.get("checks_failed", 0)
            rows   = qd.get("total_rows", 0)
            st.markdown(
                f'<span class="badge {badge_cls}">{label}</span> '
                f'<span style="font-size:.8rem;color:{GRAY}">{rows} rows · {passed}/{total} pass</span>',
                unsafe_allow_html=True,
            )
            for c in qd.get("checks", []):
                icon = "✅" if c["status"] == "PASS" else "❌"
                detail = c.get("detail", "")
                st.markdown(
                    f'<div style="padding:.3rem 0;border-bottom:1px solid #F5F5F5;font-size:.82rem">'
                    f'{icon} <b>{c["check"]}</b><br>'
                    f'<span style="color:{GRAY}">{detail}</span></div>',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════
# TAB 4 – CORRUPTION
# ══════════════════════════════════════════════════════════════════
with t4:
    st.markdown('<div class="sec">6 loại Corruption đã simulate</div>', unsafe_allow_html=True)

    op_meta = {
        "drop_latest_records":  ("🗑️", "#FFCDD2", "#C62828",
                                 "Drop Latest Records",
                                 "Xóa 3 papers mới nhất → agent mất kiến thức về papers gần đây"),
        "blank_summary":        ("📭", "#FFF9C4", "#F57F17",
                                 "Blank Summary",
                                 "Xóa abstract → text_for_embedding rỗng → embedding không chính xác"),
        "inject_noise":         ("🔊", "#FCE4EC", "#880E4F",
                                 "Inject Noise",
                                 "Thêm chuỗi random vào abstract → embedding bị nhiễu → sai paper"),
        "truncate_title":       ("✂️", "#E8EAF6", "#283593",
                                 "Truncate Title",
                                 "Cắt title còn 15 ký tự → lookup theo title fail"),
        "stale_published_date": ("📅", "#E0F2F1", "#004D40",
                                 "Stale Published Date",
                                 "Lùi published year 2 năm → freshness check fail"),
        "add_duplicates":       ("👯", "#F3E5F5", "#4A148C",
                                 "Add Duplicates",
                                 "Duplicate rows → paper_id_unique FAIL → bias trong ranking"),
    }

    for op in cl.get("operations", []):
        name  = op.get("op", "")
        n     = op.get("rows_dropped") or op.get("rows_affected") or op.get("rows_added") or 0
        icon, bg, color, title, impact = op_meta.get(name, ("⚠️", "#FFF", "#555", name, ""))
        st.markdown(f"""
        <div class="opbox" style="background:{bg};border-left:5px solid {color}">
          <div style="display:flex;align-items:center;gap:.5rem">
            <span style="font-size:1.3rem">{icon}</span>
            <span style="font-weight:700;color:{color}">{title}</span>
            <span style="margin-left:auto;background:{color};color:white;
                         border-radius:20px;padding:.15rem .55rem;font-size:.75rem;font-weight:600">
              {n} rows
            </span>
          </div>
          <div style="font-size:.83rem;color:#37474F;margin-top:.35rem">{impact}</div>
        </div>
        """, unsafe_allow_html=True)

    # Row count funnel
    st.markdown('<div class="sec">Row count flow</div>', unsafe_allow_html=True)
    rb = cl.get("rows_before", 24)
    ra = cl.get("rows_after", 22)
    fig_f = go.Figure(go.Funnel(
        y=["Raw (fetched)", "Baseline (clean)", "Corrupted", "Repaired"],
        x=[rb, rb, ra, rb],
        marker_color=[CORAL, GREEN, RED, GREEN],
        textinfo="value",
    ))
    fig_f.update_layout(height=260, margin=dict(t=10, b=10),
                        plot_bgcolor="white", paper_bgcolor="white")
    st.plotly_chart(fig_f, use_container_width=True)

    # Before / after abstract sample
    st.markdown('<div class="sec">Abstract trước vs sau corruption</div>', unsafe_allow_html=True)
    if not df_clean.empty and not df_corr.empty:
        try:
            m = df_clean[["paper_id", "title", "summary"]].merge(
                df_corr[["paper_id", "summary"]].rename(columns={"summary": "s2"}),
                on="paper_id", how="inner",
            )
            changed = m[m["summary"].fillna("") != m["s2"].fillna("")].head(3)
            if changed.empty:
                st.info("Không tìm được row có summary thay đổi (có thể cột index thay đổi sau corruption).")
            for _, row in changed.iterrows():
                st.markdown(f"**📄 {str(row['title'])[:80]}...**")
                c1, c2 = st.columns(2)
                c1.markdown("✅ **Clean**")
                c1.info(str(row["summary"])[:300])
                c2.markdown("❌ **Corrupted**")
                val = str(row["s2"]) if row["s2"] else ""
                if not val.strip():
                    c2.error("(blank — abstract bị xóa)")
                else:
                    c2.error(val[:300])
        except Exception as e:
            st.caption(f"Không load được sample: {e}")


# ══════════════════════════════════════════════════════════════════
# TAB 5 – Q&A TRACE
# ══════════════════════════════════════════════════════════════════
with t5:
    st.markdown('<div class="sec">So sánh câu trả lời: Baseline vs Corrupted</div>', unsafe_allow_html=True)

    col_f, col_d, col_n = st.columns([2, 2, 2])
    q_type   = col_f.selectbox("Loại câu hỏi", ["all", "summary", "authors", "date", "categories"])
    only_bad = col_d.checkbox("Chỉ hiện câu bị ảnh hưởng", value=True)
    max_q    = col_n.slider("Số câu", 3, 20, 8)

    base_map = {a["id"]: a for a in ba if isinstance(a, dict)}
    corr_map = {a["id"]: a for a in ca if isinstance(a, dict)}

    shown = 0
    for qid, b in base_map.items():
        if shown >= max_q:
            break
        if q_type != "all" and b.get("question_type") != q_type:
            continue
        c = corr_map.get(qid, {})
        bh = b.get("retrieval_hit", False)
        ch = c.get("retrieval_hit", False)
        if only_bad and bh == ch:
            continue

        shown += 1
        label = "❌ HIT→MISS" if bh and not ch else ("✅ MISS→HIT" if not bh and ch else ("✅ HIT" if bh else "❌ MISS"))
        qt    = b.get("question_type", "?").upper()
        q_txt = b.get("question", "")[:100]

        with st.expander(f"{label}  [{qt}]  {q_txt}..."):
            cb, cc = st.columns(2)

            with cb:
                st.markdown('<span class="badge b-base">BASELINE</span>', unsafe_allow_html=True)
                j = b.get("judge", {})
                st.markdown(f"Retrieval: {'✅ HIT' if bh else '❌ MISS'}  |  "
                            f"F1: `{b.get('token_f1',0):.3f}`  |  "
                            f"Judge: {j.get('score','-')}/5")
                ans_b = b.get("answer", "")
                st.success(ans_b[:250] if ans_b else "(empty)")

            with cc:
                st.markdown('<span class="badge b-cor">CORRUPTED</span>', unsafe_allow_html=True)
                jc = c.get("judge", {})
                st.markdown(f"Retrieval: {'✅ HIT' if ch else '❌ MISS'}  |  "
                            f"F1: `{c.get('token_f1',0):.3f}`  |  "
                            f"Judge: {jc.get('score','-')}/5")
                ans_c = c.get("answer", "")
                if ch:
                    st.success(ans_c[:250] if ans_c else "(empty)")
                else:
                    st.error(ans_c[:250] if ans_c else "(empty — paper bị drop hoặc abstract bị xóa)")

            st.caption(f"Ground truth: {b.get('ground_truth','')[:200]}")

    if shown == 0:
        st.info("Không có câu phù hợp. Bỏ chọn 'Chỉ hiện câu bị ảnh hưởng' để xem tất cả.")

    # Chart by question type
    st.markdown('<div class="sec">Hit Rate theo Question Type</div>', unsafe_allow_html=True)
    stats: dict = defaultdict(lambda: {"b": 0, "c": 0, "n": 0})
    for qid, b in base_map.items():
        qt = b.get("question_type", "other")
        c  = corr_map.get(qid, {})
        stats[qt]["n"] += 1
        if b.get("retrieval_hit"):
            stats[qt]["b"] += 1
        if c.get("retrieval_hit"):
            stats[qt]["c"] += 1

    types = list(stats.keys())
    br    = [stats[t]["b"] / max(stats[t]["n"], 1) for t in types]
    cr    = [stats[t]["c"] / max(stats[t]["n"], 1) for t in types]

    fig_qt = go.Figure([
        go.Bar(name="Baseline",  x=types, y=br, marker_color=CORAL,
               text=[pct(v) for v in br], textposition="outside"),
        go.Bar(name="Corrupted", x=types, y=cr, marker_color=RED,
               text=[pct(v) for v in cr], textposition="outside"),
    ])
    fig_qt.update_layout(
        barmode="group",
        yaxis=dict(range=[0, 1.18], tickformat=".0%", showgrid=True, gridcolor="#F0F0F0"),
        xaxis=dict(showgrid=False),
        plot_bgcolor="white", paper_bgcolor="white",
        height=300, margin=dict(t=20, b=10),
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig_qt, use_container_width=True)
