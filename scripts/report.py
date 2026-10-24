# -*- coding: utf-8 -*-
"""科技周榜报告生成器: videos_raw.json + scores.json → HTML
用法: python report.py --dir <扫描输出目录> [--title "标题"] [--out xxx.html]
"""
import argparse
import json
import os
from datetime import datetime

AUD_LABEL = {
    "S": ("🎓 学生/入门", "18-25 大学生/自学转码，编程+科普+考证"),
    "D": ("📱 数码控", "20-35 硬件更新/评测/开箱/性价比"),
    "G": ("⚙️ 极客/开发者", "22-35 底层技术/工具链/安全/开源"),
    "K": ("🔬 知识向", "25-40 深度科普/纪录片/技术经济学"),
    "C": ("💼 职场向", "25-40 AI工具/效率/行业趋势/职业发展"),
}

TYPE_COLORS = {
    "消费电子评测": "#0066cc",
    "AI·机器学习": "#7b2ff7",
    "编程开发": "#00897b",
    "科普·科学": "#e65100",
    "科技新闻": "#c62828",
    "极客·网络安全": "#2e7d32",
}

SCORE_KEYS = ("density", "visual", "cn_base", "narrative", "explosion")
SCORE_WEIGHTS = (0.20, 0.20, 0.15, 0.15, 0.30)
SCORE_LABELS = ("密度", "视觉", "中文基", "叙事", "爆点")


def fmt_views(n):
    if not n:
        return "-"
    if n >= 10_000_000:
        return f"{n / 10_000_000:.1f}kw"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    return f"{n / 1000:.0f}K"


def fmt_dur(d):
    if not d:
        return "-"
    m, s = divmod(int(d), 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def video_card(v, s, rank):
    aud = " / ".join(AUD_LABEL[a][0] for a in s.get("audiences", []) if a in AUD_LABEL)
    tcolor = TYPE_COLORS.get(v.get("cn_type", ""), "#888")
    hint = (
        f'<div class="hint">🎬 二创标题方向：{s["bili_title_hint"]}</div>'
        if s.get("bili_title_hint") else ""
    )
    dims = " ".join(
        f"{label}{s.get(key, '-')}"
        for key, label in zip(SCORE_KEYS, SCORE_LABELS)
    )
    return f"""
<div class="card">
  <a class="thumb" href="{v.get('url', '')}" target="_blank">
    <img loading="lazy" src="{v.get('thumbnail') or ''}" onerror="this.parentNode.style.display='none'">
    <span class="rank">{rank}</span>
  </a>
  <div class="info">
    <div class="t"><a href="{v.get('url', '')}" target="_blank">{v.get('title', '')}</a></div>
    <div class="meta">
      <span class="tag" style="background:{tcolor}">{v.get('cn_type', '')}</span>
      <span class="ch">{v.get('channel', '')}</span>
      <span>▶ {fmt_views(v.get('view_count'))}</span>
      <span>⏱ {fmt_dur(v.get('duration_s'))}</span>
      <span>{v.get('upload_date', '')}</span>
    </div>
    <div class="scorebar">
      <span class="total">{s.get('total', 0):.2f}</span>
      <span class="dims">{dims}</span>
    </div>
    <div class="aud">{aud}</div>
    <div class="reason">💡 {s.get('reason', '')}</div>
    {hint}
  </div>
</div>"""


def compute_total(s, dur):
    total = sum(w * s.get(k, 5) for k, w in zip(SCORE_KEYS, SCORE_WEIGHTS))
    if 480 <= dur <= 1500:
        total += 0.2
    elif dur > 2400:
        total -= 0.1
    return round(total, 2)


def build_html(videos, scores, title, days=30, min_views=500_000):
    smap = {s["video_id"]: s for s in scores}
    rows = []
    for v in videos:
        s = smap.get(v["video_id"])
        if not s:
            continue
        s["total"] = compute_total(s, v.get("duration_s") or 0)
        rows.append((v, s))
    rows.sort(key=lambda x: -x[1]["total"])

    by_type = {}
    by_aud = {k: [] for k in AUD_LABEL}
    for v, s in rows:
        by_type.setdefault(v.get("cn_type", "?"), []).append((v, s))
        for a in s.get("audiences", []):
            if a in by_aud:
                by_aud[a].append((v, s))

    cards_top = "".join(video_card(v, s, i + 1) for i, (v, s) in enumerate(rows[:20]))

    type_secs = ""
    for t, lst in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        if not lst:
            continue
        inner = "".join(video_card(v, s, i + 1) for i, (v, s) in enumerate(lst[:6]))
        type_secs += f'<h2 class="sec">{t} <small>{len(lst)} 条</small></h2><div class="grid">{inner}</div>'

    aud_secs = ""
    for k, lst in by_aud.items():
        if not lst:
            continue
        name, desc = AUD_LABEL[k]
        inner = "".join(video_card(v, s, i + 1) for i, (v, s) in enumerate(lst[:5]))
        aud_secs += f'<h2 class="sec">{name} <small>{desc}</small></h2><div class="grid">{inner}</div>'

    def _views_str():
        return f"{min_views / 10000:.0f}万" if min_views >= 10000 else str(min_views)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    formula = "总分 = 0.20密度+0.20视觉+0.15中文基础+0.15叙事+0.30爆点（10分制）"
    sub = (
        f"生成时间 {now} · 候选 {len(rows)} 条"
        f"（近{days}天 · 播放量≥{_views_str()}） · {formula}"
    )

    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1f2328;margin:0;padding:24px;max-width:1200px;margin:0 auto}}
h1{{font-size:26px;margin:0 0 4px}}
.sub{{color:#888;font-size:13px;margin-bottom:20px}}
.sec{{font-size:19px;margin:28px 0 12px;padding-left:10px;border-left:4px solid #0066cc}}
.sec small{{color:#999;font-weight:400;font-size:13px;margin-left:8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:14px}}
.card{{display:flex;gap:12px;background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.thumb{{position:relative;width:190px;min-width:190px;aspect-ratio:16/9;border-radius:8px;overflow:hidden;background:#eee;display:block}}
.thumb img{{width:100%;height:100%;object-fit:cover;display:block}}
.rank{{position:absolute;left:0;top:0;background:rgba(0,0,0,.65);color:#fff;font-size:12px;padding:2px 8px;border-radius:0 0 6px 0}}
.info{{flex:1;min-width:0}}
.t a{{color:#222;font-size:14.5px;font-weight:600;text-decoration:none;line-height:1.4}}
.t a:hover{{color:#0066cc}}
.meta{{font-size:12px;color:#777;margin:6px 0 8px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.tag{{color:#fff;font-size:11px;padding:1px 8px;border-radius:10px}}
.ch{{font-weight:600}}
.scorebar{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
.total{{background:#0066cc;color:#fff;font-weight:700;font-size:16px;border-radius:6px;padding:1px 10px}}
.dims{{font-size:12px;color:#666}}
.aud{{font-size:12px;color:#00897b;margin-bottom:5px;font-weight:600}}
.reason{{font-size:12.5px;color:#555;line-height:1.5}}
.hint{{font-size:12px;color:#999;margin-top:4px}}
footer{{margin-top:30px;color:#aaa;font-size:12px;text-align:center}}
</style></head><body>
<h1>🔬 {title}</h1>
<div class="sub">{sub}</div>
<h2 class="sec">🔥 综合总榜 TOP20</h2><div class="grid">{cards_top}</div>
<h2 class="sec">🎯 按人群精选</h2>{aud_secs}
<h2 class="sec">📚 按类型分组</h2>{type_secs}
<footer>youtube-tech-radar · 频道源334个 + 关键词搜索18组 · 数据来自 YouTube 公开页</footer>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--title", default="YouTube 科技选题榜")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-views", type=int, default=500_000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    vids_path = os.path.join(args.dir, "videos_raw.json")
    with open(vids_path, encoding="utf-8") as f:
        videos = json.load(f)

    scores_path = os.path.join(args.dir, "scores.json")
    if os.path.exists(scores_path):
        with open(scores_path, encoding="utf-8") as f:
            scores = json.load(f)
    else:
        scores = []
        print("⚠ 无 scores.json，未打分（报告将是无分版本）")

    out = args.out or os.path.join(
        args.dir,
        f"{datetime.now().strftime('%Y-%m-%d')}_{args.title}.html",
    )
    html = build_html(videos, scores, args.title, args.days, args.min_views)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ 报告 → {out} ({os.path.getsize(out) // 1024}KB)")


if __name__ == "__main__":
    main()
