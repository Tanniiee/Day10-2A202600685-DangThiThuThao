"""
System Monitoring Dashboard — Data Observability
Giám sát data pipeline + xuất reporting
Run: streamlit run app3.py
"""
from __future__ import annotations

import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

st.set_page_config(page_title="System Monitoring · Data Observability", page_icon="📡", layout="wide")

# ── palette ───────────────────────────────────────────────────────
BLUE, TEAL, GREEN, RED, AMBER, GRAY, DARK = "#2E75B6", "#00897B", "#43A047", "#E53935", "#FFB300", "#78909C", "#1C2733"
STATE_COLORS = {"baseline": BLUE, "corrupted": RED, "repaired": GREEN}
STATE_LABELS = {"baseline": "Baseline", "corrupted": "Corrupted", "repaired": "Repaired"}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: #F4F7FA; }}
.hero {{ background: linear-gradient(135deg, {DARK}, #2E4057); border-radius: 14px;
         padding: 1.6rem 2.2rem; color: white; margin-bottom: 1.2rem;
         display: flex; justify-content: space-between; align-items: center; }}
.hero h1 {{ font-size: 1.55rem; font-weight: 800; margin: 0; }}
.hero p  {{ font-size: .85rem; opacity: .75; margin: .25rem 0 0; }}
.status  {{ border-radius: 24px; padding: .45rem 1.2rem; font-weight: 700; font-size: .95rem; }}
.s-ok    {{ background: {GREEN}; color: white; }}
.s-warn  {{ background: {RED}; color: white; }}
.kpi {{ background: white; border-radius: 12px; padding: .95rem 1.1rem; text-align: center;
        box-shadow: 0 2px 6px rgba(0,0,0,.06); border-top: 4px solid {BLUE}; }}
.kpi .lbl {{ font-size: .7rem; color: {GRAY}; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }}
.kpi .val {{ font-size: 1.7rem; font-weight: 800; color: {DARK}; }}
.kpi .sub {{ font-size: .78rem; color: {GRAY}; }}
.alert {{ border-radius: 10px; padding: .75rem 1rem; margin-bottom: .5rem; font-size: .88rem;
          background: white; box-shadow: 0 1px 4px rgba(0,0,0,.05); }}
.a-crit {{ border-left: 5px solid {RED}; }}
.a-warn {{ border-left: 5px solid {AMBER}; }}
.a-ok   {{ border-left: 5px solid {GREEN}; }}
.sec {{ font-size: 1.05rem; font-weight: 700; color: {DARK};
        border-left: 5px solid {TEAL}; padding-left: .6rem; margin: 1.3rem 0 .7rem; }}
</style>
""", unsafe_allow_html=True)


# ── data loading ──────────────────────────────────────────────────
FILES = {
    "baseline": {"clean": "clean/papers_clean.csv", "quality": "quality/baseline_quality.json",
                 "fresh": "quality/freshness_report.json", "metrics": "results/baseline_metrics.json",
                 "answers": "results/baseline_answers.json"},
    "corrupted": {"clean": "clean/papers_clean_corrupted.csv", "quality": "quality/corrupted_quality.json",
                  "fresh": "quality/corrupted_freshness.json", "metrics": "results/corrupted_metrics.json",
                  "answers": "results/corrupted_answers.json"},
    "repaired": {"clean": "clean/papers_clean_repaired.csv", "quality": "quality/repaired_quality.json",
                 "fresh": "quality/repaired_freshness.json", "metrics": "results/repaired_metrics.json",
                 "answers": "results/repaired_answers.json"},
}


@st.cache_data(show_spinner=False)
def jload(rel: str):
    p = DATA / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def cload(rel: str) -> pd.DataFrame | None:
    p = DATA / rel
    if not p.exists():
        return None
    return pd.read_csv(p)


def bundle(state: str) -> dict:
    f = FILES[state]
    return {k: (cload(v) if k == "clean" else jload(v)) for k, v in f.items()}


def pct(v, d=1):
    return "N/A" if v is None else f"{v * 100:.{d}f}%"


def num(v, d=3):
    return "N/A" if v is None else f"{v:.{d}f}"


ALL = {s: bundle(s) for s in FILES}
missing = [s for s, b in ALL.items() if b["metrics"] is None or b["quality"] is None]
if missing:
    st.error(f"Thiếu artifacts cho: {', '.join(missing)}. Hãy chạy `script/run_phase1.py` và `script/run_corruption_flow.py` trước.")
    st.stop()


# ── health evaluation ─────────────────────────────────────────────
def build_alerts(state: str) -> list[tuple[str, str]]:
    """Return list of (level, message). level: crit | warn | ok"""
    b = ALL[state]
    alerts = []
    for c in b["quality"].get("checks", []):
        if c["status"] == "FAIL":
            alerts.append(("crit", f"Quality check **{c['check']}** FAIL — {c.get('detail', '')}"))
    fr = b["fresh"] or {}
    if fr.get("stale_rows", 0) > 0:
        alerts.append(("warn", f"Freshness: **{fr['stale_rows']} stale rows** (> {fr.get('freshness_threshold_days', '?')} ngày)"))
    if not fr.get("is_fresh", True):
        alerts.append(("crit", "Freshness: dataset **không fresh**"))
    m = b["metrics"]
    base = ALL["baseline"]["metrics"]
    if state != "baseline" and m["retrieval_hit_rate"] < base["retrieval_hit_rate"] - 1e-9:
        d = m["retrieval_hit_rate"] - base["retrieval_hit_rate"]
        alerts.append(("crit", f"Retrieval hit rate giảm **{pct(d)}** so với baseline"))
    if state != "baseline" and m["mean_token_f1"] < base["mean_token_f1"] - 0.05:
        alerts.append(("warn", f"Token F1 giảm còn **{num(m['mean_token_f1'])}** (baseline {num(base['mean_token_f1'])})"))
    if not alerts:
        alerts.append(("ok", "Tất cả checks PASS — hệ thống hoạt động bình thường"))
    return alerts


def health_status(state: str) -> bool:
    return all(lv == "ok" for lv, _ in build_alerts(state))


# ── sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📡 Monitoring")
    state = st.radio("Dataset state", list(FILES), format_func=lambda s: STATE_LABELS[s])
    st.divider()
    fr = ALL[state]["fresh"] or {}
    st.caption(f"Freshness threshold: **{fr.get('freshness_threshold_days', 'N/A')} ngày**")
    st.caption(f"Generated: {datetime.now():%d/%m/%Y %H:%M}")
    if st.button("🔄 Reload data"):
        st.cache_data.clear()
        st.rerun()

B = ALL[state]
healthy = health_status(state)

# ── hero ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
  <div>
    <h1>📡 System Monitoring — Data Observability</h1>
    <p>RAG pipeline · Crossref papers · state: <b>{STATE_LABELS[state]}</b></p>
  </div>
  <div class="status {'s-ok' if healthy else 's-warn'}">{'● HEALTHY' if healthy else '● DEGRADED'}</div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────
m, q = B["metrics"], B["quality"]
cols = st.columns(6)
kpis = [
    ("Rows", q.get("total_rows", "N/A"), "clean dataset"),
    ("Quality checks", f"{q['checks_passed']}/{q['checks_passed'] + q['checks_failed']}", "passed"),
    ("Stale rows", fr.get("stale_rows", "N/A"), f"> {fr.get('freshness_threshold_days', '?')}d"),
    ("Hit rate", pct(m.get("retrieval_hit_rate")), "retrieval"),
    ("Token F1", num(m.get("mean_token_f1")), "mean"),
    ("Judge", f"{num(m.get('mean_judge_score'), 2)}/5", pct(m.get("judge_accuracy")) + " acc"),
]
for col, (lbl, val, sub) in zip(cols, kpis):
    col.markdown(f'<div class="kpi"><div class="lbl">{lbl}</div><div class="val">{val}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)

st.markdown("")

# ── tabs ──────────────────────────────────────────────────────────
t_alert, t_quality, t_fresh, t_metrics, t_answers, t_export = st.tabs(
    ["🚨 Alerts", "📋 Data Quality", "⏱ Freshness", "📈 Metrics", "🔍 Answers", "📤 Export Report"])

# ── alerts ────────────────────────────────────────────────────────
with t_alert:
    st.markdown('<div class="sec">Cảnh báo hiện tại</div>', unsafe_allow_html=True)
    icon = {"crit": "🔴", "warn": "🟡", "ok": "🟢"}
    for lv, msg in build_alerts(state):
        st.markdown(f'<div class="alert a-{lv}">{icon[lv]} {msg.replace("**", "<b>", 1).replace("**", "</b>", 1) if "**" in msg else msg}</div>', unsafe_allow_html=True)

    st.markdown('<div class="sec">Health qua 3 trạng thái</div>', unsafe_allow_html=True)
    hcols = st.columns(3)
    for col, s in zip(hcols, FILES):
        ok = health_status(s)
        col.markdown(
            f'<div class="kpi" style="border-top-color:{STATE_COLORS[s]}">'
            f'<div class="lbl">{STATE_LABELS[s]}</div>'
            f'<div class="val">{"🟢" if ok else "🔴"}</div>'
            f'<div class="sub">{"HEALTHY" if ok else "DEGRADED"}</div></div>',
            unsafe_allow_html=True)

# ── quality ───────────────────────────────────────────────────────
with t_quality:
    st.markdown(f'<div class="sec">Quality checks — {STATE_LABELS[state]}</div>', unsafe_allow_html=True)
    qdf = pd.DataFrame(q["checks"])
    qdf["status"] = qdf["status"].map(lambda s_: "✅ PASS" if s_ == "PASS" else "❌ FAIL")
    st.dataframe(qdf, use_container_width=True, hide_index=True)

    st.markdown('<div class="sec">So sánh pass/fail</div>', unsafe_allow_html=True)
    fig = go.Figure()
    for cat, color in [("checks_passed", GREEN), ("checks_failed", RED)]:
        fig.add_bar(name=cat.replace("checks_", "").upper(),
                    x=[STATE_LABELS[s] for s in FILES],
                    y=[ALL[s]["quality"][cat] for s in FILES],
                    marker_color=color)
    fig.update_layout(barmode="stack", height=320, margin=dict(t=20, b=20),
                      plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# ── freshness ─────────────────────────────────────────────────────
with t_fresh:
    st.markdown(f'<div class="sec">Freshness — {STATE_LABELS[state]}</div>', unsafe_allow_html=True)
    fc = st.columns(4)
    fc[0].metric("Latest published", fr.get("latest_published", "N/A"))
    fc[1].metric("Oldest published", fr.get("oldest_published", "N/A"))
    fc[2].metric("Stale rows", f"{fr.get('stale_rows', 'N/A')} / {fr.get('total_rows', 'N/A')}")
    fc[3].metric("Is fresh", "✅ Yes" if fr.get("is_fresh") else "❌ No")

    df = B["clean"]
    if df is not None and "age_days" in df.columns:
        st.markdown('<div class="sec">Phân bố tuổi dữ liệu (age_days)</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Histogram(x=df["age_days"], nbinsx=20, marker_color=STATE_COLORS[state]))
        fig.add_vline(x=fr.get("freshness_threshold_days", 180), line_dash="dash", line_color=RED,
                      annotation_text="threshold", annotation_position="top right")
        fig.update_layout(height=320, margin=dict(t=20, b=20), plot_bgcolor="white",
                          paper_bgcolor="rgba(0,0,0,0)", xaxis_title="age_days", yaxis_title="papers")
        st.plotly_chart(fig, use_container_width=True)

# ── metrics ───────────────────────────────────────────────────────
with t_metrics:
    st.markdown('<div class="sec">So sánh metrics: Baseline / Corrupted / Repaired</div>', unsafe_allow_html=True)
    spec = [("retrieval_hit_rate", "Retrieval hit rate", True), ("mean_token_f1", "Mean token F1", False),
            ("judge_accuracy", "Judge accuracy", True), ("mean_judge_score", "Mean judge score", False)]
    fig = go.Figure()
    for s in FILES:
        fig.add_bar(name=STATE_LABELS[s], x=[t for _, t, _ in spec],
                    y=[ALL[s]["metrics"][k] / (5 if k == "mean_judge_score" else 1) for k, _, _ in spec],
                    marker_color=STATE_COLORS[s])
    fig.update_layout(barmode="group", height=380, margin=dict(t=20, b=20),
                      plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                      yaxis_title="score (judge /5 normalized)")
    st.plotly_chart(fig, use_container_width=True)

    rows = []
    for k, t, is_pct in spec:
        f = pct if is_pct else num
        b_, c_, r_ = (ALL[s]["metrics"][k] for s in FILES)
        rows.append({"Metric": t, "Baseline": f(b_), "Corrupted": f(c_), "Repaired": f(r_),
                     "Δ Corrupt": f(c_ - b_) if is_pct else f"{c_ - b_:+.3f}",
                     "Δ Repaired": f(r_ - b_) if is_pct else f"{r_ - b_:+.3f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    log = jload("results/corruption_log.json")
    if log:
        with st.expander("🧨 Corruption log"):
            st.json(log)

# ── answers drill-down ────────────────────────────────────────────
with t_answers:
    answers = B["answers"] or []
    st.markdown(f'<div class="sec">Answers drill-down — {STATE_LABELS[state]} ({len(answers)} câu)</div>', unsafe_allow_html=True)
    if answers:
        adf = pd.DataFrame([{
            "id": a["id"], "type": a["question_type"], "question": a["question"],
            "hit": "✅" if a["retrieval_hit"] else "❌", "token_f1": round(a["token_f1"], 3),
            "judge": f"{a['judge']['score']}/5", "correct": "✅" if a["judge"]["correct"] else "❌",
        } for a in answers])
        fcols = st.columns([1, 1, 2])
        qtype = fcols[0].multiselect("Loại câu hỏi", sorted(adf["type"].unique()))
        only_fail = fcols[1].checkbox("Chỉ hiện lỗi (miss / incorrect)")
        view = adf
        if qtype:
            view = view[view["type"].isin(qtype)]
        if only_fail:
            view = view[(view["hit"] == "❌") | (view["correct"] == "❌")]
        st.dataframe(view, use_container_width=True, hide_index=True, height=320)

        sel = st.selectbox("Xem chi tiết câu", view["id"].tolist() if len(view) else [])
        if sel is not None and len(view):
            a = next(x for x in answers if x["id"] == sel)
            st.markdown(f"**Q:** {a['question']}")
            c1, c2 = st.columns(2)
            c1.info(f"**Answer:**\n\n{a['answer']}")
            c2.success(f"**Ground truth:**\n\n{a['ground_truth']}")
            st.caption(f"Judge ({a['judge']['score']}/5): {a['judge']['reasoning']}")

# ── export report ─────────────────────────────────────────────────
with t_export:
    st.markdown('<div class="sec">Xuất báo cáo</div>', unsafe_allow_html=True)

    def build_markdown() -> str:
        lines = [f"# Monitoring Report — {datetime.now():%d/%m/%Y %H:%M}", ""]
        lines += [f"**Trạng thái đang xem:** {STATE_LABELS[state]} — "
                  f"{'HEALTHY ✅' if healthy else 'DEGRADED ❌'}", ""]
        lines += ["## Alerts", ""]
        for lv, msg in build_alerts(state):
            lines.append(f"- [{lv.upper()}] {msg}")
        lines += ["", "## Metrics comparison", "",
                  "| Metric | Baseline | Corrupted | Repaired |", "|---|---|---|---|"]
        for k, t, is_pct in spec:
            f = pct if is_pct else num
            lines.append("| " + " | ".join([t] + [f(ALL[s]["metrics"][k]) for s in FILES]) + " |")
        lines += ["", "## Quality checks", ""]
        for s in FILES:
            qq = ALL[s]["quality"]
            lines.append(f"### {STATE_LABELS[s]} — {qq['checks_passed']}/{qq['checks_passed'] + qq['checks_failed']} PASS")
            lines.append("")
            lines.append("| Check | Status | Detail |")
            lines.append("|---|---|---|")
            for c in qq["checks"]:
                lines.append(f"| {c['check']} | {c['status']} | {c.get('detail', '')} |")
            lines.append("")
        lines += ["## Freshness", "", "| Field | " + " | ".join(STATE_LABELS[s] for s in FILES) + " |",
                  "|---|" + "---|" * 3]
        for field in ["latest_published", "oldest_published", "stale_rows", "total_rows", "is_fresh"]:
            lines.append("| " + " | ".join([field] + [str((ALL[s]["fresh"] or {}).get(field, "N/A")) for s in FILES]) + " |")
        return "\n".join(lines)

    md = build_markdown()
    csv_buf = io.StringIO()
    pd.DataFrame(rows).to_csv(csv_buf, index=False)

    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Tải report (Markdown)", md,
                       file_name=f"monitoring_report_{datetime.now():%Y%m%d_%H%M}.md", mime="text/markdown",
                       use_container_width=True)
    c2.download_button("⬇️ Tải metrics comparison (CSV)", csv_buf.getvalue(),
                       file_name="metrics_comparison.csv", mime="text/csv", use_container_width=True)

    with st.expander("👀 Preview report"):
        st.markdown(md)

    st.markdown('<div class="sec">Báo cáo có sẵn từ pipeline</div>', unsafe_allow_html=True)
    for rel in ["reports/phase1_report.md", "reports/corruption_report.md"]:
        p = DATA / rel
        if p.exists():
            with st.expander(f"📄 {rel}"):
                st.markdown(p.read_text(encoding="utf-8"))
