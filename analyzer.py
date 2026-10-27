"""合併一週資料 → 統一用語 → 去重 → 國際與旅外篩選 → 台灣關聯專題分析 → 本週統計"""
import csv, json, re
from datetime import datetime, timedelta
import config
from llm import ask_json

ANALYSIS_PROMPT = """你是體育分析師，專長是從台灣的角度解讀賽事。請只根據下列已查證的資料做分析，
不可加入資料以外的事實或數字。

事件：{title}（{date}，{sport}）
摘要：{summary}
來源資料：
{context}

只輸出 JSON：
{{
  "overview": "賽事概況：名稱、日期、目前進行到哪個階段（100 字內）",
  "performance": "中華台北或台灣選手的表現：成績、關鍵選手（150 字內）",
  "notable": ["值得注意的狀況，例如爭議判決、傷病、賽制、主要對手（每點 40 字內，2～4 點；資料沒有就少寫）"],
  "significance": "對台灣的意義與後續（120 字內；判斷性內容用「可能」「預期」）"
}}
{style}"""

def _key(title):
    return re.sub(r"[\W_]+", "", (title or "").lower())[:18]

def apply_terms(obj):
    if isinstance(obj, str):
        for a, b in config.REPLACE_TERMS.items():
            obj = obj.replace(a, b)
        return obj
    if isinstance(obj, list):
        return [apply_terms(x) for x in obj]
    if isinstance(obj, dict):
        return {k: (v if k in ("url", "link") else apply_terms(v)) for k, v in obj.items()}
    return obj

def dedupe(events):
    best = {}
    for e in events:
        k = _key(e.get("player") or e.get("title"))
        cur = best.get(k)
        if cur is None or (e.get("best_tier", 9), -e.get("importance", 0)) < (cur.get("best_tier", 9), -cur.get("importance", 0)):
            best[k] = e
    return sorted(best.values(), key=lambda e: (-e.get("importance", 0), e.get("best_tier", 9)))

def select(events):
    """國際：與台灣無關最多 3、含台灣相關最多 5；旅外最多 5"""
    tw = [e for e in events if e.get("region") == "taiwan"]
    ov = [e for e in events if e.get("region") == "overseas"][:config.OVERSEAS_MAX]
    gl = [e for e in events if e.get("region") == "global"]
    major = [e for e in gl if not e.get("taiwan_link") and e.get("importance", 0) >= 4][:config.GLOBAL_BASE]
    linked = [e for e in gl if e.get("taiwan_link")][:config.GLOBAL_MAX - len(major)]
    out = tw + ov + major + linked
    out.sort(key=lambda e: (-e.get("importance", 0), e.get("best_tier", 9)))
    return out

def load_week(report_date: datetime) -> dict:
    events, excluded, items, files, ups, degraded = [], [], [], [], [], False
    start = (report_date - timedelta(days=6)).date()
    for f in sorted(config.DATA_DIR.glob("20*.json")):
        try:
            d = datetime.strptime(f.stem[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if start <= d <= report_date.date():
            data = json.loads(f.read_text(encoding="utf-8"))
            events += data.get("events", [])
            excluded += data.get("excluded", [])
            items += data.get("items", [])
            ups += data.get("upcoming", [])
            degraded = degraded or data.get("degraded", False)
            files.append(f.name)
    ev = select(dedupe(apply_terms(events)))
    kept = {_key(e.get("player") or e["title"]) for e in ev}
    exc = [e for e in dedupe(apply_terms(excluded)) if _key(e.get("player") or e["title"]) not in kept]
    ups = sorted({(u.get("date", ""), u.get("title", "")): u for u in apply_terms(ups)
                  if u.get("date", "") >= report_date.strftime("%Y-%m-%d")}.values(), key=lambda u: u.get("date", ""))
    return {"events": ev, "excluded": exc, "items": items, "upcoming": ups[:12], "files": files,
            "degraded": degraded, "start": start, "end": report_date.date()}

def is_taiwan_related(e):
    return e.get("region") in ("taiwan", "overseas") or bool(e.get("taiwan_link"))

def pick_analysis(events):
    cand = [e for e in events if is_taiwan_related(e) and e.get("best_tier", 9) <= 2
            and (e.get("is_special") or e.get("importance", 0) >= config.SPECIAL_THRESHOLD)]
    return cand[:config.MAX_ANALYSIS]

def analyze(e):
    try:
        a = ask_json(ANALYSIS_PROMPT.format(title=e["title"], date=e.get("date", ""), sport=e.get("sport", ""),
                                            summary=e.get("summary", ""), context=e.get("context", "")[:3000],
                                            style=config.STYLE_RULES), label="analysis", max_tokens=3000)
    except Exception as ex:
        print("專題分析失敗：", str(ex)[:120])
        a = None
    if isinstance(a, dict):
        e["analysis"] = apply_terms(a)
    return e

def week_stats(week, analyses):
    ev = week["events"]
    count = lambda r: sum(1 for e in ev if e.get("region") == r)
    calls = 0
    if config.STATS_FILE.exists():
        start = week["start"].isoformat()
        calls = sum(1 for r in csv.DictReader(open(config.STATS_FILE, encoding="utf-8")) if r["time"][:10] >= start)
    warn = []
    if count("taiwan") < config.TARGET["taiwan"]:
        warn.append(f"台灣新聞 {count('taiwan')} 則，低於目標 {config.TARGET['taiwan']} 則")
    if count("overseas") < config.TARGET["overseas"] and week["end"].month not in config.OFFSEASON_MONTHS:
        warn.append(f"旅外棒球 {count('overseas')} 則，低於目標 {config.TARGET['overseas']} 則")
    if week.get("degraded"):
        warn.append("本週有部分資料因 Gemini 免費額度不足，以降級模式（只列標題）產出")
    tier = lambda t: sum(1 for e in ev if e.get("best_tier") == t)
    return {"taiwan": count("taiwan"), "overseas": count("overseas"), "global": count("global"),
            "analysis": sum(1 for e in analyses if e.get("analysis")), "calls": calls, "warnings": warn,
            "excluded": len(week.get("excluded", [])), "tiers": {t: tier(t) for t in (1, 2, 3, 4)},
            "tier12_pct": round(100 * (tier(1) + tier(2)) / len(ev)) if ev else 0}
