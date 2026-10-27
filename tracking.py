"""
事件延續追蹤（不需網路搜尋）
  - 本週 track=true 的事件加入追蹤清單（data/tracking.json）
  - 每週一由 Gemini 比對「追蹤中事件」與本週所有新聞標題，找出後續進展，來源取自實際新聞
  - 事件結束或追蹤滿 3 週即停止
"""
import json, re
import config
from llm import ask_json
from analyzer import apply_terms

PROMPT = """以下是追蹤中的體育事件，以及本週各媒體的新聞標題（id、媒體、標題）。
請判斷每個追蹤事件本週是否有後續進展（例如傷癒復出、處分結果、調查結論、轉隊完成、系列賽結果）。
只能根據標題判斷，引用的新聞 id 必須確實與該事件相關；沒有就回報無進展。
{style}

追蹤中事件：
{tracked}

本週新聞標題：
{items}

只輸出 JSON 陣列：[{{"id": 追蹤事件編號, "has_update": true/false, "update": "進展（50 字內）",
                    "item_ids": [相關新聞 id], "closed": true/false（事件已告一段落）}}]"""

def _key(t):
    return re.sub(r"[\W_]+", "", (t or "").lower())[:18]

def load():
    if config.TRACKING_FILE.exists():
        return json.loads(config.TRACKING_FILE.read_text(encoding="utf-8"))
    return {"items": []}

def run(now, events, news_items):
    state = load()
    tracked = state["items"]
    results = []
    if tracked and news_items:
        by_id = {it["id"]: it for it in news_items}
        q = [{"id": i, "title": t["title"], "since": t["since"]} for i, t in enumerate(tracked)]
        rows = [{"id": it["id"], "src": it["source"], "title": it["title"]} for it in news_items][:300]
        try:
            res = ask_json(PROMPT.format(style=config.STYLE_RULES, tracked=json.dumps(q, ensure_ascii=False),
                                         items=json.dumps(rows, ensure_ascii=False)), label="tracking", max_tokens=3000)
        except Exception as ex:
            print("延續追蹤失敗：", str(ex)[:120]); res = []
        by = {r.get("id"): r for r in res if isinstance(r, dict)}
        for i, t in enumerate(tracked):
            r = by.get(i, {})
            srcs = [{"name": by_id[j]["source"], "url": by_id[j]["link"], "tier": by_id[j]["tier"]}
                    for j in r.get("item_ids", []) if j in by_id][:2]
            has = bool(r.get("has_update")) and bool(srcs) and bool(r.get("update"))
            t["weeks"] = t.get("weeks", 0) + 1
            t["closed"] = bool(r.get("closed")) and has
            results.append(apply_terms({"title": t["title"], "since": t["since"], "weeks": t["weeks"],
                                        "has_update": has, "update": r.get("update", "") if has else "",
                                        "sources": srcs, "closed": t["closed"]}))
    state["items"] = [t for t in tracked if not t.get("closed") and t.get("weeks", 0) < config.TRACK_MAX_WEEKS]
    known = {_key(t["title"]) for t in state["items"]}
    new = sorted([e for e in events if e.get("track") and _key(e["title"]) not in known],
                 key=lambda e: -e.get("importance", 0))
    for e in new[:max(config.TRACK_MAX_ITEMS - len(state["items"]), 0)]:
        state["items"].append({"title": e["title"], "since": now.strftime("%Y-%m-%d"), "weeks": 0})
        results.append(apply_terms({"title": e["title"], "since": now.strftime("%Y-%m-%d"), "weeks": 0,
                                    "has_update": False, "update": "", "sources": [], "closed": False, "new": True}))
    config.TRACKING_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"延續追蹤：本週查詢 {len(results)} 件，目前追蹤中 {len(state['items'])} 件")
    return results
