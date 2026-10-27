"""
Gemini 編輯台（三步驟）
  1. 選題：把數百則標題歸併成「事件」，判斷區塊、重要度、是否特殊、與台灣相關性
  2. 撰寫與查證：讀每個事件的原文／摘要，用自己的話寫摘要，並比對各來源是否一致
  3. 規則把關：依來源層級與查證結果決定採用或排除
"""
import json
from concurrent.futures import ThreadPoolExecutor
import config, fetcher
from llm import ask_json
from sources import best_tier

TRIAGE_PROMPT = """你是資深體育新聞編輯。以下是 {since} 至 {until}（台灣時間）各媒體的新聞標題清單
（id、區塊提示、媒體、來源層級 1=官方 2=通訊社 3=媒體 4=其他、標題、摘要）。

請把「報導同一件事」的標題歸併成一個事件，並挑選本週值得報導的事件：
・taiwan（台灣新聞）：{focus_tw}。旅外棒球選手的新聞不要放這裡。至少 {n_tw} 件。
・overseas（旅外棒球）：旅美、旅日、旅韓台灣棒球選手。{overseas_rule}
・global（國際）：(a) 全球等級重大事件（世界紀錄、重大決賽、重大醜聞或決策），taiwan_link=false，最多 {g_base} 件；
  (b) 賽事層級與台灣相關的國際新聞（有中華台北參加的綜合性運動會整體賽況、賽制、主辦權），taiwan_link=true。
  台灣選手的個人成績放 taiwan。與台灣相關性低又不是全球頂級的事件請省略。
另外從清單中找出未來 7 天值得關注的賽事（只能根據標題內容，不可自行補充）。

{style}

清單：
{items}

只輸出 JSON：
{{
  "events": [{{
    "item_ids": [屬於此事件的 id],
    "title": "事件標題（繁體中文，自行撰寫）",
    "sport": "運動項目",
    "region": "taiwan、overseas 或 global",
    "date": "YYYY-MM-DD",
    "importance": 1-5,
    "is_special": true/false（重大爆冷、破紀錄、禁藥或違規、明星重傷或退休、重大轉會、主辦權、台灣選手歷史性成績、安全事故）,
    "special_reason": "原因或空字串",
    "taiwan_link": true/false,
    "why_matters": "國際且與台灣無關時，一句話說明為何重要；其他留空",
    "track": true/false（後續幾週可能有進展：傷病、禁賽、調查、轉隊、進行中的系列賽）,
    "status": "final 或 ongoing"
  }}],
  "upcoming": [{{"date": "YYYY-MM-DD", "sport": "", "title": "", "region": "taiwan、overseas 或 global"}}]
}}"""

WRITE_PROMPT = """你是體育新聞查證編輯。以下每個事件附有各來源的原文片段或標題摘要。
請逐一完成：
1. 只根據提供的資料，用自己的話寫 80～150 字摘要（含比分、數據）；資料沒有的細節不要寫。
2. 比對各來源的日期、比分、人名、數據是否一致，並判斷支持程度：
   - multi：兩個以上來源內容一致
   - single：只有一個來源，但有具體內容（原文或摘要）
   - headline：只有標題，缺乏細節
   - conflict：來源之間有矛盾且無法判斷何者正確
3. 若來源之間有小差異，以層級較高（數字較小）的來源為準，並在 note 說明。
4. 旅外棒球事件若附有 MLB 官方數據，數據以官方為準；球員中文名依清單中中央社等媒體寫法，查不到就只寫英文名。
   請判斷 notable：是否值得報導（勝投、優質先發、關鍵安打或全壘打、救援成功、升降級、傷兵、交易簽約）；表現平淡為 false。

{style}

事件：
{events}

只輸出 JSON 陣列：
[{{"key": "事件代號", "title": "標題（可修正）", "summary": "摘要", "support": "multi|single|headline|conflict",
   "note": "查證說明（30 字內）", "key_numbers": ["值得放大呈現的數字與一句說明，例如：7K｜生涯單場新高"],
   "player": "旅外棒球填：中文名（英文名）", "team": "旅外棒球填：聯盟／球隊", "line": "旅外棒球填：本週代表性成績",
   "notable": true/false, "importance": 1-5}}]"""

def _overseas_rule(until):
    if until.month in config.OFFSEASON_MONTHS:
        return "目前為休賽季：收錄簽約、轉隊、入札、冬季聯盟、春訓等重要消息。"
    return "只收錄明顯表現或重要變動（先發勝投、關鍵安打或全壘打、升降一軍或大聯盟、傷兵、交易、簽約）。"

def triage(items, since, until):
    rows = [{"id": it["id"], "hint": it["region_hint"], "src": it["source"], "tier": it["tier"],
             "title": it["title"], "sum": it["summary"][:90], "date": it["published"][:10]} for it in items]
    res = ask_json(TRIAGE_PROMPT.format(
        since=since.strftime("%Y-%m-%d %H:%M"), until=until.strftime("%Y-%m-%d %H:%M"),
        focus_tw="中職、國內職籃與聯賽、體育政策、台灣選手國際賽重大成績（奪冠、打進決賽、破紀錄）",
        n_tw=4, overseas_rule=_overseas_rule(until), g_base=config.GLOBAL_BASE,
        style=config.STYLE_RULES, items=json.dumps(rows, ensure_ascii=False)),
        label="triage", max_tokens=24000)
    valid = {it["id"] for it in items}
    events = []
    for e in res.get("events", []) if isinstance(res, dict) else []:
        ids = [i for i in e.get("item_ids", []) if i in valid]
        if ids and e.get("region") in ("taiwan", "overseas", "global"):
            e["item_ids"] = ids
            events.append(e)
    return events, (res.get("upcoming", []) if isinstance(res, dict) else [])

def _materials(e, items_by_id):
    """整理事件的來源：解析原始網址、抓原文（最多 3 個來源，優先高層級）"""
    its = sorted((items_by_id[i] for i in e["item_ids"]), key=lambda x: x["tier"])[:3]
    def one(it):
        url = fetcher.resolve_link(it["link"])
        return {"name": it["source"], "tier": it["tier"], "url": url, "title": it["title"],
                "text": fetcher.article_text(url) or it["summary"]}
    with ThreadPoolExecutor(3) as ex:
        return list(ex.map(one, its))

def write_and_verify(events, items_by_id, mlb_records):
    """撰寫摘要並查證；mlb_records 為旅外球員官方數據"""
    for k, e in enumerate(events):
        e["key"] = f"E{k}"
        e["materials"] = _materials(e, items_by_id)
    for k, p in enumerate(mlb_records):
        events.append({"key": f"M{k}", "region": "overseas", "sport": "棒球", "title": f"{p['name']} 本週出賽",
                       "date": p["games"][-1]["date"], "importance": 3, "item_ids": [], "mlb": True,
                       "materials": [{"name": "MLB", "tier": 1, "url": p["url"], "title": p["name"],
                                      "text": f"{p['level']}｜{p['pos']}｜" + "；".join(
                                          f"{g['date']} 對 {g['opp']}：{g['line']}" for g in p["games"])}]})
    names = [it["title"] for it in items_by_id.values() if it["region_hint"] == "overseas"][:40]
    for i in range(0, len(events), 6):
        chunk = events[i:i + 6]
        payload = [{"key": e["key"], "region": e["region"], "title": e["title"],
                    "sources": [{"媒體": m["name"], "層級": m["tier"], "標題": m["title"], "內容": m["text"][:1800]}
                                for m in e["materials"]]} for e in chunk]
        extra = f"\n（旅外球員中文名參考標題：{json.dumps(names, ensure_ascii=False)}）" if any(e.get("mlb") for e in chunk) else ""
        try:
            res = ask_json(WRITE_PROMPT.format(style=config.STYLE_RULES,
                                               events=json.dumps(payload, ensure_ascii=False) + extra),
                           label="write", max_tokens=16000)
        except Exception as ex:
            print("撰寫失敗，本批改用標題：", str(ex)[:120])
            res = []
        by = {r.get("key"): r for r in res if isinstance(r, dict)}
        for e in chunk:
            r = by.get(e["key"], {"support": "headline", "summary": "", "note": "撰寫未回傳"})
            for f in ("title", "summary", "note", "key_numbers", "player", "team", "line", "importance"):
                if r.get(f):
                    e[f] = r[f]
            e["support"] = r.get("support", "headline")
            e["notable"] = r.get("notable", True)
    return merge_mlb(events, mlb_records)

def merge_mlb(events, mlb_records):
    """同一位球員同時出現在新聞與 MLB 官方數據時，把官方成績併入新聞，避免重複"""
    news = [e for e in events if e.get("region") == "overseas" and not e.get("mlb")]
    out = []
    for e in events:
        if not e.get("mlb"):
            out.append(e)
            continue
        rec = mlb_records[int(e["key"][1:])]
        names = [rec["name"], rec["name"].split()[-1]] + ([e["player"].split("（")[0]] if e.get("player") else [])
        hit = next((n for n in news if any(x and x in f"{n['title']}{n.get('summary','')}{n.get('player','')}"
                                           for x in names[:1] + names[2:])), None)
        if hit:
            hit["line"] = hit.get("line") or e.get("line", "")
            hit["team"] = hit.get("team") or e.get("team", "")
            hit["player"] = hit.get("player") or e.get("player", "")
            hit["materials"] = hit.get("materials", []) + e["materials"]
            hit["note"] = (hit.get("note", "") + "；成績以 MLB 官方數據為準").strip("；")
        else:
            out.append(e)
    return out

def apply_rules(events):
    """依查證結果與來源層級決定採用或排除"""
    kept, excluded = [], []
    for e in events:
        srcs = [{"name": m["name"], "url": m["url"], "tier": m["tier"]} for m in e.get("materials", [])]
        e["sources"] = srcs
        e["best_tier"] = best_tier(srcs)
        domains = {m["name"] for m in srcs}
        sup = e.get("support")
        reason = ""
        if not srcs:
            reason = "無可用來源"
        elif sup == "conflict":
            reason = "來源說法不一"
        elif sup == "headline" and e["best_tier"] > 2 and len(domains) < 2:
            reason = "只有標題、資訊不足"
        elif sup == "single" and e["best_tier"] > 2:
            reason = "僅單一非主要媒體報導"
        elif e.get("mlb") and not e.get("notable", True):
            reason = "表現平淡（不收錄）"
        e["context"] = "\n".join(f"【{m['name']}】{m['text']}" for m in e.get("materials", []))[:3000]
        e.pop("materials", None)
        e["verdict"] = {"multi": "多來源一致", "single": "單一可信來源",
                        "headline": "多來源標題一致" if len(domains) >= 2 else "僅依可信媒體標題（細節請見原文）"}.get(sup, "")
        if reason:
            e["exclude_reason"] = reason
            if not e.get("mlb"):
                excluded.append(e)
            continue
        if e.get("is_special") and e["best_tier"] > 2:
            e["is_special"] = False
            e["note"] = (e.get("note", "") + "；缺第一、二層來源，取消特殊事件").strip("；")
        kept.append(e)
    return kept, excluded
