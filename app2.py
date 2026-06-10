"""
Data Detective — Nguyên Lý Data Observability
Narrative-driven single-page Streamlit app
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(
    page_title="Data Detective · Data Observability",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── palette ───────────────────────────────────────────────────────
C = "#FF7043"      # coral
CD = "#BF360C"     # coral dark
CB = "#FFF3EF"     # coral bg
GR = "#43A047"     # green
RD = "#E53935"     # red
AM = "#FFB300"     # amber
BG = "#0F1117"     # dark bg
S1 = "#1A1D27"     # surface 1
S2 = "#22263A"     # surface 2
TX = "#E8EAF0"     # text light
TM = "#9EA7C0"     # text muted

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
    background-color: {BG};
    color: {TX};
}}
.stApp {{ background: {BG}; }}

/* scrollbar */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-thumb {{ background: {C}; border-radius: 3px; }}

/* ── hero ── */
.hero {{
    background: linear-gradient(140deg, {S1} 0%, {S2} 50%, #2D1A0E 100%);
    border: 1px solid rgba(255,112,67,.25);
    border-radius: 20px; padding: 2.8rem 3rem; margin-bottom: 2rem;
    position: relative; overflow: hidden;
}}
.hero::before {{
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 300px; height: 300px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,112,67,.15), transparent 70%);
    pointer-events: none;
}}
.hero-eye  {{ font-size: 3.5rem; margin-bottom: .5rem; }}
.hero-title {{
    font-size: 2.6rem; font-weight: 800; color: white;
    line-height: 1.1; margin: 0 0 .5rem;
}}
.hero-title span {{ color: {C}; }}
.hero-sub {{ font-size: 1rem; color: {TM}; max-width: 600px; line-height: 1.6; }}

/* ── section ── */
.act {{
    display: flex; align-items: center; gap: .7rem;
    margin: 2.5rem 0 1rem;
}}
.act-num {{
    background: {C}; color: white; border-radius: 50%;
    width: 32px; height: 32px; display: flex; align-items: center;
    justify-content: center; font-weight: 700; font-size: .85rem;
    flex-shrink: 0;
}}
.act-title {{ font-size: 1.3rem; font-weight: 700; color: white; }}
.act-sub   {{ font-size: .85rem; color: {TM}; margin-top: .15rem; }}
.act-divider {{ border-top: 1px solid rgba(255,112,67,.2); margin: 2rem 0; }}

/* ── glass card ── */
.gcard {{
    background: {S1}; border: 1px solid rgba(255,255,255,.07);
    border-radius: 14px; padding: 1.3rem 1.5rem;
}}
.gcard-accent {{ border-left: 4px solid {C}; }}

/* ── big metric ── */
.bmet {{
    text-align: center;
    background: {S2}; border-radius: 12px; padding: 1.4rem;
    border: 1px solid rgba(255,255,255,.06);
}}
.bmet-icon {{ font-size: 1.8rem; }}
.bmet-val  {{ font-size: 2.4rem; font-weight: 800; line-height: 1; margin: .3rem 0 .2rem; }}
.bmet-lbl  {{ font-size: .75rem; color: {TM}; font-weight: 600;
               text-transform: uppercase; letter-spacing: .06em; }}

/* ── timeline ── */
.tl {{
    border-left: 3px solid rgba(255,112,67,.35);
    padding-left: 1.5rem; margin-left: .5rem;
}}
.tl-item {{ position: relative; margin-bottom: 1.3rem; }}
.tl-dot {{
    position: absolute; left: -2.1rem; top: .3rem;
    width: 14px; height: 14px; border-radius: 50%;
    border: 2px solid {C};
}}
.tl-dot-ok   {{ background: {GR}; border-color: {GR}; }}
.tl-dot-bad  {{ background: {RD}; border-color: {RD}; }}
.tl-dot-warn {{ background: {AM}; border-color: {AM}; }}
.tl-dot-fix  {{ background: {C};  border-color: {C};  }}
.tl-title {{ font-weight: 700; font-size: .95rem; color: white; }}
.tl-body  {{ font-size: .83rem; color: {TM}; margin-top: .2rem; line-height: 1.5; }}

/* ── alert box ── */
.alert {{
    border-radius: 10px; padding: 1rem 1.2rem;
    display: flex; gap: .8rem; align-items: flex-start;
    margin-bottom: .8rem;
}}
.alert-crit {{ background: rgba(229,57,53,.12); border: 1px solid rgba(229,57,53,.35); }}
.alert-warn {{ background: rgba(255,179,0,.10); border: 1px solid rgba(255,179,0,.30); }}
.alert-ok   {{ background: rgba(67,160,71,.10); border: 1px solid rgba(67,160,71,.30); }}
.alert-icon {{ font-size: 1.3rem; flex-shrink: 0; }}
.alert-title {{ font-weight: 700; font-size: .88rem; color: white; }}
.alert-body  {{ font-size: .8rem; color: {TM}; margin-top: .15rem; }}

/* ── answer card ── */
.ans {{
    background: {S2}; border-radius: 10px; padding: 1rem 1.2rem;
    border: 1px solid rgba(255,255,255,.06); margin-bottom: .6rem;
}}
.ans-hit  {{ border-left: 4px solid {GR}; }}
.ans-miss {{ border-left: 4px solid {RD}; }}
.ans-q   {{ font-size: .8rem; color: {TM}; margin-bottom: .5rem; }}
.ans-body {{ font-size: .85rem; color: {TX}; }}

/* ── badge ── */
.badge {{ display:inline-block; border-radius:20px; padding:.18rem .6rem;
           font-size:.72rem; font-weight:700; }}
.bd-ok  {{ background:rgba(67,160,71,.2);  color:#A5D6A7; }}
.bd-bad {{ background:rgba(229,57,53,.2);  color:#EF9A9A; }}
.bd-am  {{ background:rgba(255,179,0,.2);  color:#FFE082; }}
.bd-neu {{ background:rgba(255,255,255,.1);color:#B0BEC5; }}

/* ── progress bar ── */
.pbar-wrap {{ background: rgba(255,255,255,.06); border-radius: 20px; height: 10px; }}
.pbar      {{ border-radius: 20px; height: 10px; transition: width .5s; }}

/* ── table override ── */
.stDataFrame {{ background: {S1} !important; }}

/* fix streamlit default white backgrounds */
div[data-testid="metric-container"] {{
    background: {S2}; border-radius: 10px; padding: .6rem;
    border: 1px solid rgba(255,255,255,.07);
}}
</style>
""", unsafe_allow_html=True)


# ── data helpers ──────────────────────────────────────────────────
@st.cache_data
def jload(rel):
    p = DATA / rel
    if not p.exists():
        return {}
    try:
        v = json.loads(p.read_text("utf-8"))
        return v if isinstance(v, (dict, list)) else {}
    except Exception:
        return {}

@st.cache_data
def cload(rel):
    p = DATA / rel
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()

def pct(v, d=1):
    return f"{v:.{d}%}" if v is not None else "—"

def num(v, d=3):
    return f"{v:.{d}f}" if v is not None else "—"

bm  = jload("results/baseline_metrics.json")
cm  = jload("results/corrupted_metrics.json")
rm  = jload("results/repaired_metrics.json")
bq  = jload("quality/baseline_quality.json")
cq  = jload("quality/corrupted_quality.json")
rq  = jload("quality/repaired_quality.json")
fr  = jload("quality/freshness_report.json")
cl  = jload("results/corruption_log.json")
ba  = jload("results/baseline_answers.json");  ba = ba if isinstance(ba, list) else []
ca  = jload("results/corrupted_answers.json"); ca = ca if isinstance(ca, list) else []
df  = cload("clean/papers_clean.csv")
dfc = cload("clean/papers_clean_corrupted.csv")


# ══════════════════════════════════════════════════════════════════
# HERO
# ══════════════════════════════════════════════════════════════════
bh = bm.get("retrieval_hit_rate", 1) or 1
ch = cm.get("retrieval_hit_rate", 1) or 1
rh = rm.get("retrieval_hit_rate", 1) or 1
drop_pct = (bh - ch) * 100
recovered = (rh - ch) * 100

# compute health score (0–100) based on quality + metrics
qp = bq.get("checks_passed", 6)
qt = qp + bq.get("checks_failed", 0)
health = int((qp / max(qt, 1)) * 50 + bh * 50)

health_color = GR if health >= 80 else (AM if health >= 50 else RD)
health_label = "HEALTHY" if health >= 80 else ("DEGRADED" if health >= 50 else "CRITICAL")

st.markdown(f"""
<div class="hero">
  <div class="hero-eye">🕵️</div>
  <div class="hero-title">Data <span>Detective</span></div>
  <div class="hero-title" style="font-size:1.4rem;font-weight:400;color:{TM};margin-top:-.2rem">
    Nguyên Lý Data Observability
  </div>
  <div class="hero-sub" style="margin-top:.8rem">
    Một RAG pipeline không chỉ phụ thuộc vào model —
    <strong style="color:{C}">chất lượng data</strong> mới là yếu tố quyết định.
    Lab này chứng minh điều đó bằng số liệu thực tế.
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# ACT 1 — SYSTEM HEALTH
# ══════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="act">
  <div class="act-num">1</div>
  <div>
    <div class="act-title">Trạng thái hệ thống</div>
    <div class="act-sub">Baseline pipeline — data sạch, agent hoạt động tốt</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Health gauge
gauge_fig = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=health,
    delta={"reference": 70},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": TM, "tickfont": {"color": TM}},
        "bar":  {"color": health_color, "thickness": .25},
        "bgcolor": S2,
        "bordercolor": "rgba(0,0,0,0)",
        "steps": [
            {"range": [0, 50],  "color": "rgba(229,57,53,.15)"},
            {"range": [50, 80], "color": "rgba(255,179,0,.12)"},
            {"range": [80, 100],"color": "rgba(67,160,71,.12)"},
        ],
        "threshold": {"line": {"color": C, "width": 3}, "value": 80},
    },
    number={"suffix": "", "font": {"color": health_color, "size": 52}},
    title={"text": f"Data Health Score<br><span style='font-size:.8rem;color:{TM}'>{health_label}</span>",
           "font": {"color": TX, "size": 15}},
))
gauge_fig.update_layout(
    height=260, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=30, b=10, l=20, r=20),
    font=dict(family="Inter", color=TM),
)

col_g, col_m = st.columns([1.2, 2])
with col_g:
    st.plotly_chart(gauge_fig, use_container_width=True)

with col_m:
    m1, m2, m3, m4 = st.columns(2), st.columns(2), None, None
    pairs = [
        (f"{pct(bh)}",        "Retrieval Hit Rate", GR),
        (f"{num(bm.get('mean_token_f1'))}",  "Token F1",          C),
        (f"{pct(bm.get('judge_accuracy'))}", "Judge Accuracy",    AM),
        (f"{bm.get('samples','—')}",         "Test Samples",      TM),
    ]
    for i, (val, lbl, color) in enumerate(pairs):
        col = st.columns(4)[i]
        with col:
            st.markdown(f"""
            <div class="bmet">
              <div class="bmet-val" style="color:{color}">{val}</div>
              <div class="bmet-lbl">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="margin-top:1rem" class="gcard gcard-accent">
      <div style="font-size:.8rem;color:{TM};margin-bottom:.5rem;font-weight:600">
        DATA QUALITY — {bq.get('checks_passed',0)}/{bq.get('checks_passed',0)+bq.get('checks_failed',0)} CHECKS PASS
      </div>
    """, unsafe_allow_html=True)
    for c in bq.get("checks", []):
        ok = c["status"] == "PASS"
        bar_w = 100 if ok else 0
        st.markdown(f"""
      <div style="display:flex;align-items:center;gap:.5rem;padding:.25rem 0;
                  border-bottom:1px solid rgba(255,255,255,.05)">
        <span style="font-size:.85rem">{'✅' if ok else '❌'}</span>
        <span style="font-size:.78rem;color:{'#A5D6A7' if ok else '#EF9A9A'};flex:1">{c['check']}</span>
        <span style="font-size:.72rem;color:{TM}">{c.get('detail','')}</span>
      </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# ACT 2 — WHAT WENT WRONG
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="act-divider"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="act">
  <div class="act-num">2</div>
  <div>
    <div class="act-title">Điều gì đã xảy ra?</div>
    <div class="act-sub">Timeline của sự cố — 6 loại corruption được inject vào dataset</div>
  </div>
</div>
""", unsafe_allow_html=True)

col_tl, col_al = st.columns([1.1, 1])

with col_tl:
    st.markdown('<div class="gcard">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:.8rem;font-weight:700;color:{};margin-bottom:1rem;letter-spacing:.05em">CORRUPTION TIMELINE</div>'.format(TM), unsafe_allow_html=True)

    ops_detail = {
        "drop_latest_records":  ("bad",  "🗑️", "Drop 3 latest records",
                                 "Papers mới nhất bị xóa → agent mù quáng với kiến thức gần đây"),
        "blank_summary":        ("bad",  "📭", "Blank abstract (3 rows)",
                                 "Abstract bị xóa → text_for_embedding rỗng → vector sai hoàn toàn"),
        "inject_noise":         ("bad",  "🔊", "Noise injection (2 rows)",
                                 "Random text thêm vào abstract → embedding bị nhiễu"),
        "truncate_title":       ("warn", "✂️", "Title truncated (2 rows)",
                                 "Title bị cắt còn 15 ký tự → lookup by title thất bại"),
        "stale_published_date": ("warn", "📅", "Date shifted –2 years (2 rows)",
                                 "Published date lùi 2 năm → freshness alarm, agent ưu tiên sai"),
        "add_duplicates":       ("warn", "👯", "Duplicate rows added (+1)",
                                 "paper_id_unique check FAIL → ranking bị bias"),
    }

    rb = cl.get("rows_before", 24)
    ra = cl.get("rows_after", 22)

    st.markdown(f"""
    <div class="tl">
      <div class="tl-item">
        <div class="tl-dot tl-dot-ok"></div>
        <div class="tl-title">✅ Baseline clean — {rb} rows</div>
        <div class="tl-body">Data sạch · 6/6 quality checks pass · Hit rate 100%</div>
      </div>
    """, unsafe_allow_html=True)

    for op in cl.get("operations", []):
        name = op.get("op", "")
        n    = op.get("rows_dropped") or op.get("rows_affected") or op.get("rows_added") or 0
        dot_type, icon, title, body = ops_detail.get(name, ("warn", "⚠️", name, ""))
        st.markdown(f"""
      <div class="tl-item">
        <div class="tl-dot tl-dot-{dot_type}"></div>
        <div class="tl-title">{icon} {title} <span style="font-size:.75rem;color:{TM}">· {n} rows</span></div>
        <div class="tl-body">{body}</div>
      </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
      <div class="tl-item">
        <div class="tl-dot tl-dot-bad"></div>
        <div class="tl-title">❌ Corrupted state — {ra} rows</div>
        <div class="tl-body">Hit rate giảm {drop_pct:.1f}% · 1 quality check FAIL · 2 stale rows</div>
      </div>
      <div class="tl-item">
        <div class="tl-dot tl-dot-fix"></div>
        <div class="tl-title">🔧 Repaired — {rb} rows</div>
        <div class="tl-body">Re-clean từ raw source · tất cả metrics phục hồi hoàn toàn</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_al:
    st.markdown('<div class="gcard">', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:.8rem;font-weight:700;color:{TM};margin-bottom:1rem;letter-spacing:.05em">ALERTS TRIGGERED</div>', unsafe_allow_html=True)

    alerts = [
        ("crit", "🚨", "Retrieval Hit Rate giảm 12.5%",
         f"100% → 87.5% — agent không tìm được đúng document cho 3/24 câu hỏi"),
        ("crit", "🚨", "paper_id_unique FAIL",
         "1 duplicate record làm bias retrieval ranking"),
        ("warn", "⚠️", "5 abstracts quá ngắn (22.7%)",
         "Embedding của 5 papers gần như vô nghĩa do abstract bị blank/truncate"),
        ("warn", "⚠️", "2 stale dates phát hiện",
         "Published date bị lùi → freshness monitoring báo động"),
        ("ok",   "✅", "Token F1 vẫn chấp nhận được",
         "F1 giảm từ 0.862 → 0.717 nhưng judge accuracy không đổi nhiều"),
    ]

    for level, icon, title, body in alerts:
        st.markdown(f"""
    <div class="alert alert-{'crit' if level=='crit' else ('ok' if level=='ok' else 'warn')}">
      <span class="alert-icon">{icon}</span>
      <div>
        <div class="alert-title">{title}</div>
        <div class="alert-body">{body}</div>
      </div>
    </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════
# ACT 3 — IMPACT ON AGENT
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="act-divider"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="act">
  <div class="act-num">3</div>
  <div>
    <div class="act-title">Impact lên Agent</div>
    <div class="act-sub">Câu trả lời thay đổi như thế nào khi data bị corrupt?</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Metrics comparison chart (dark theme)
cats   = ["Baseline", "Corrupted", "Repaired"]
colors_bar = [C, RD, GR]

metric_rows = [
    ("retrieval_hit_rate", "Retrieval Hit Rate", True),
    ("mean_token_f1",      "Mean Token F1",      False),
    ("judge_accuracy",     "Judge Accuracy",     True),
]

fig_cmp = go.Figure()
for key, label, _ in metric_rows:
    vals = [bm.get(key, 0) or 0, cm.get(key, 0) or 0, rm.get(key, 0) or 0]
    fig_cmp.add_trace(go.Bar(name=label, x=cats, y=vals, marker_color=colors_bar))

fig_cmp.update_layout(
    barmode="group",
    plot_bgcolor=S1, paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color=TM),
    legend=dict(orientation="h", y=1.1, font=dict(color=TX)),
    yaxis=dict(range=[0, 1.12], tickformat=".0%", gridcolor="rgba(255,255,255,.06)", color=TM),
    xaxis=dict(gridcolor="rgba(0,0,0,0)", color=TM),
    height=320, margin=dict(t=40, b=10, l=10, r=10),
)
st.plotly_chart(fig_cmp, use_container_width=True)

# Q&A side-by-side — pick 3 most impactful (hit→miss)
st.markdown(f'<div style="font-size:.85rem;font-weight:700;color:{TM};margin:.5rem 0 .8rem;letter-spacing:.05em">CÂU TRẢ LỜI THAY ĐỔI DO CORRUPTION</div>', unsafe_allow_html=True)

base_map = {a["id"]: a for a in ba if isinstance(a, dict)}
corr_map = {a["id"]: a for a in ca if isinstance(a, dict)}

impacted = [
    (qid, b, corr_map.get(qid, {}))
    for qid, b in base_map.items()
    if b.get("retrieval_hit") and not corr_map.get(qid, {}).get("retrieval_hit")
][:3]

if impacted:
    for qid, b, c in impacted:
        qt  = b.get("question_type", "").upper()
        q   = b.get("question", "")
        ans_b = b.get("answer", "(no answer)")
        ans_c = c.get("answer", "(empty — paper bị drop/corrupt)")
        f1_b = b.get("token_f1", 0)
        f1_c = c.get("token_f1", 0)

        st.markdown(f"""
        <div class="gcard" style="margin-bottom:.8rem">
          <div style="font-size:.72rem;font-weight:700;color:{C};margin-bottom:.4rem">
            <span class="badge bd-am">{qt}</span>
            &nbsp;HIT → MISS after corruption
          </div>
          <div style="font-size:.83rem;color:{TX};margin-bottom:.8rem">{q[:120]}...</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem">
            <div style="background:rgba(67,160,71,.08);border-radius:8px;padding:.8rem;
                        border-left:3px solid {GR}">
              <div style="font-size:.7rem;font-weight:700;color:#A5D6A7;margin-bottom:.4rem">
                ✅ BASELINE · F1: {f1_b:.3f}
              </div>
              <div style="font-size:.82rem;color:{TX}">{ans_b[:200]}</div>
            </div>
            <div style="background:rgba(229,57,53,.08);border-radius:8px;padding:.8rem;
                        border-left:3px solid {RD}">
              <div style="font-size:.7rem;font-weight:700;color:#EF9A9A;margin-bottom:.4rem">
                ❌ CORRUPTED · F1: {f1_c:.3f}
              </div>
              <div style="font-size:.82rem;color:{TX}">{ans_c[:200] if ans_c else '(empty)'}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
else:
    # show random samples with score diff
    samples = [(qid, b, corr_map.get(qid, {})) for qid, b in list(base_map.items())[:3]]
    for qid, b, c in samples:
        qt  = b.get("question_type", "").upper()
        q   = b.get("question", "")
        ans_b = b.get("answer", "(no answer)")
        ans_c = c.get("answer", "(no answer)")
        f1_b = b.get("token_f1", 0)
        f1_c = c.get("token_f1", 0)
        diff_color = GR if f1_b <= f1_c else RD
        st.markdown(f"""
        <div class="gcard" style="margin-bottom:.8rem">
          <div style="font-size:.72rem;font-weight:700;color:{C};margin-bottom:.4rem">
            <span class="badge bd-neu">{qt}</span>
            &nbsp;F1: {f1_b:.3f} → <span style="color:{diff_color}">{f1_c:.3f}</span>
          </div>
          <div style="font-size:.83rem;color:{TX};margin-bottom:.8rem">{q[:120]}...</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem">
            <div style="background:rgba(67,160,71,.08);border-radius:8px;padding:.8rem;border-left:3px solid {GR}">
              <div style="font-size:.7rem;font-weight:700;color:#A5D6A7;margin-bottom:.4rem">✅ BASELINE</div>
              <div style="font-size:.82rem;color:{TX}">{ans_b[:200]}</div>
            </div>
            <div style="background:rgba(229,57,53,.08);border-radius:8px;padding:.8rem;border-left:3px solid {RD}">
              <div style="font-size:.7rem;font-weight:700;color:#EF9A9A;margin-bottom:.4rem">❌ CORRUPTED</div>
              <div style="font-size:.82rem;color:{TX}">{ans_c[:200]}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

# interactive explorer
with st.expander("🔍 Xem tất cả Q&A (có thể filter)"):
    q_type_sel = st.selectbox("Loại câu hỏi", ["all", "summary", "authors", "date", "categories"], key="qt_sel")
    only_impact = st.checkbox("Chỉ câu bị ảnh hưởng", True, key="oi_sel")

    shown = 0
    for qid, b in list(base_map.items()):
        if shown >= 12:
            break
        if q_type_sel != "all" and b.get("question_type") != q_type_sel:
            continue
        c   = corr_map.get(qid, {})
        bhi = b.get("retrieval_hit", False)
        chi = c.get("retrieval_hit", False)
        if only_impact and bhi == chi:
            continue
        shown += 1
        lbl = "❌ HIT→MISS" if bhi and not chi else ("✅ MISS→HIT" if not bhi and chi else ("✅" if bhi else "❌"))
        st.markdown(f"**{lbl}** `{b.get('question_type','?').upper()}` — {b.get('question','')[:90]}...")
        cc1, cc2 = st.columns(2)
        cc1.success(b.get("answer", "")[:200] or "(empty)")
        cc2.error(c.get("answer", "")[:200] or "(empty)")
        st.caption(f"Ground truth: {b.get('ground_truth','')[:150]}")
        st.divider()


# ══════════════════════════════════════════════════════════════════
# ACT 4 — REPAIR & RECOVERY
# ══════════════════════════════════════════════════════════════════
st.markdown('<div class="act-divider"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="act">
  <div class="act-num">4</div>
  <div>
    <div class="act-title">Repair & Recovery</div>
    <div class="act-sub">Re-clean từ raw source → mọi metrics phục hồi hoàn toàn</div>
  </div>
</div>
""", unsafe_allow_html=True)

rc1, rc2, rc3 = st.columns(3)
for col, title, val_b, val_r, as_pct in [
    (rc1, "Retrieval Hit Rate", bh, rh, True),
    (rc2, "Mean Token F1",      bm.get("mean_token_f1"), rm.get("mean_token_f1"), False),
    (rc3, "Judge Accuracy",     bm.get("judge_accuracy"), rm.get("judge_accuracy"), True),
]:
    fmt = pct if as_pct else num
    diff = (val_r or 0) - (val_b or 0)
    diff_txt = f"+{pct(diff)}" if as_pct else f"+{num(diff)}"
    diff_col = GR if abs(diff) < 0.005 else (GR if diff > 0 else RD)
    with col:
        st.markdown(f"""
        <div class="bmet" style="border:1px solid rgba(67,160,71,.25)">
          <div class="bmet-icon">{'✅' if abs(diff)<0.005 else '📈'}</div>
          <div style="font-size:1rem;color:{TM};margin:.2rem 0 .1rem">{fmt(val_b)} → <strong style="color:{GR}">{fmt(val_r)}</strong></div>
          <div style="color:{diff_col};font-size:.82rem">{diff_txt if abs(diff)>0.001 else '≈ fully recovered'}</div>
          <div class="bmet-lbl" style="margin-top:.3rem">{title}</div>
        </div>
        """, unsafe_allow_html=True)

# Final verdict
cf, cr = cm.get("retrieval_hit_rate", 0) or 0, rm.get("retrieval_hit_rate", 0) or 0
cq_p = cq.get("checks_passed", 0)
cq_t = cq_p + cq.get("checks_failed", 0)
rq_p = rq.get("checks_passed", 0)
rq_t = rq_p + rq.get("checks_failed", 0)

st.markdown(f"""
<div style="background:linear-gradient(135deg,{S1},{S2});border-radius:16px;
            padding:1.8rem 2rem;margin-top:1.5rem;
            border:1px solid rgba(255,112,67,.3)">
  <div style="font-size:1.4rem;font-weight:800;color:white;margin-bottom:.8rem">
    🔍 Verdict
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:1rem;margin-bottom:1rem">
    <div style="text-align:center">
      <div style="font-size:2rem;font-weight:800;color:{RD}">{pct(drop_pct/100)}</div>
      <div style="font-size:.75rem;color:{TM}">Hit rate drop khi corrupt</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:2rem;font-weight:800;color:{AM}">{cq_t - cq_p}</div>
      <div style="font-size:.75rem;color:{TM}">Quality check FAIL</div>
    </div>
    <div style="text-align:center">
      <div style="font-size:2rem;font-weight:800;color:{GR}">100%</div>
      <div style="font-size:.75rem;color:{TM}">Recovery sau repair</div>
    </div>
  </div>
  <div style="font-size:.88rem;color:{TM};line-height:1.7;border-top:1px solid rgba(255,255,255,.08);padding-top:.8rem">
    <strong style="color:white">Kết luận:</strong>
    Chỉ 6 thao tác corruption nhỏ (drop 3 rows, blank 3 abstracts...) đã làm hệ thống RAG
    mất đi <strong style="color:{RD}">{drop_pct:.1f}%</strong> khả năng tìm đúng tài liệu.
    Không cần retrain model — chỉ cần <strong style="color:{GR}">repair data từ raw source</strong>
    là mọi thứ phục hồi. Đây là bằng chứng rõ ràng nhất cho
    <strong style="color:{C}">Data Observability</strong>:
    monitor → detect → repair, không phải tune model mãi.
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div style="text-align:center;color:{TM};font-size:.75rem;margin-top:2rem;padding-bottom:1rem">Day 10 · Data Pipeline & Data Observability · RAG Evaluation Lab</div>', unsafe_allow_html=True)
