"""資料包存檔目錄（output/INDEX.md）與年度回顧"""
import json
from datetime import datetime
import config
from llm import ask_json

def save_stats(date_str, stats):
    (config.OUTPUT_DIR / f"stats_{date_str}.json").write_text(
        json.dumps({k: v for k, v in stats.items() if k != "tiers"}, ensure_ascii=False), encoding="utf-8")

def rebuild_index():
    rows = []
    for f in sorted(config.OUTPUT_DIR.glob("stats_*.json"), reverse=True):
        s, d = json.loads(f.read_text(encoding="utf-8")), f.stem.split("_")[1]
        rows.append(f"| {d[:4]}/{d[4:6]}/{d[6:]} | {s.get('taiwan',0)} | {s.get('overseas',0)} | {s.get('global',0)} | "
                    f"{s.get('analysis',0)} | {s.get('tier12_pct',0)}% | {s.get('calls',0)} | "
                    f"[內容](週報內容_{d}.pdf)・[指示](簡報指示_{d}.txt)・[連結](原文連結_{d}.txt) |")
    years = sorted(config.OUTPUT_DIR.glob("年度回顧_*.pdf"), reverse=True)
    text = ["# 全球體育週報　資料包目錄", "", "| 日期 | 台灣 | 旅外棒球 | 國際 | 專題 | 第一二層來源 | Gemini 呼叫次數 | 檔案 |",
            "|---|---|---|---|---|---|---|---|"] + rows
    if years:
        text += ["", "## 年度回顧"] + [f"- [{y.stem}]({y.name})" for y in years]
    (config.OUTPUT_DIR / "INDEX.md").write_text("\n".join(text) + "\n", encoding="utf-8")

ANNUAL_PROMPT = """你是體育年鑑主編。以下是 {year} 年每週資料包中已查證的新聞（id、日期、區塊、標題、摘要）。
請只根據這份清單撰寫年度回顧，不可新增清單以外的事實。
{style}

清單：
{items}

只輸出 JSON：
{{"headline": "年度一句話總結（50 字內）",
  "taiwan": [{{"id": 編號, "point": "年度意義（40 字內）"}}]（最多 8）,
  "overseas": [{{"id": 編號, "point": ""}}]（最多 6）,
  "global": [{{"id": 編號, "point": ""}}]（最多 5）,
  "outlook": "明年值得期待（120 字內，用「可望」「預期」）"}}"""

def annual(now: datetime):
    from analyzer import dedupe, apply_terms
    from package import to_pdf, to_md
    events = []
    for f in sorted(config.DATA_DIR.glob(f"{now.year}-*.json")):
        events += json.loads(f.read_text(encoding="utf-8")).get("events", [])
    events = sorted([e for e in dedupe(apply_terms(events)) if e.get("importance", 0) >= 3],
                    key=lambda e: e.get("date", ""))[:400]
    if not events:
        print("今年沒有資料，略過年度回顧"); return []
    items = [{"id": i, "date": e.get("date"), "region": e.get("region"), "title": e["title"],
              "summary": (e.get("summary") or "")[:60]} for i, e in enumerate(events)]
    r = apply_terms(ask_json(ANNUAL_PROMPT.format(year=now.year, style=config.STYLE_RULES,
                                                  items=json.dumps(items, ensure_ascii=False)),
                             label="annual", max_tokens=5000))
    pick = lambda k: [(events[x["id"]], x.get("point", "")) for x in r.get(k, [])
                      if isinstance(x, dict) and isinstance(x.get("id"), int) and 0 <= x["id"] < len(events)]
    B = [("h1", f"{now.year} 全球體育年度回顧"), ("p", r.get("headline", ""))]
    for name, key in (("台灣年度大事", "taiwan"), ("旅外棒球年度亮點", "overseas"), ("國際年度大事", "global")):
        B.append(("h2", name))
        for e, p in pick(key):
            B += [("h3", f"{e.get('date','')}｜{e['title']}"), ("p", p)]
            B += [("src", f"來源：{s['name']}　{s['url']}") for s in e.get("sources", [])[:1]]
    B += [("h2", "明年展望"), ("p", r.get("outlook", "")),
          ("meta", f"資料範圍：{now.year} 年每週資料包中經查證的 {len(events)} 則新聞。")]
    pdf, md = config.OUTPUT_DIR / f"年度回顧_{now.year}.pdf", config.OUTPUT_DIR / f"年度回顧_{now.year}.md"
    to_pdf(B, pdf); md.write_text(to_md(B), encoding="utf-8")
    rebuild_index()
    return [str(md), str(pdf)]
