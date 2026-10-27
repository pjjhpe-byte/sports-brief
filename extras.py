"""簡報素材（一次呼叫）：本週最該關注 3 件事、關鍵數字、章節標語、小測驗、講稿重點"""
import json
import config
from llm import ask_json
from analyzer import apply_terms

PROMPT = """你是體育週報主編兼簡報企劃。以下是本週已查證的新聞（id、區塊、標題、摘要、可放大的數字）。
請只根據這些內容準備簡報素材，不可新增清單以外的事實或數字。

{style}

本週新聞：
{items}
專題分析主題：{analyses}

只輸出 JSON：
{{
  "top3": [{{"id": 編號, "why": "為什麼重要（40 字內，優先考慮與台灣的關聯）"}}]（3 個）,
  "key_numbers": [{{"number": "數字（含單位，例如 7K、3金、0.98）", "label": "一句說明（20 字內）", "id": 來源新聞編號}}]（3～4 個，只能用清單中的數字）,
  "slogans": {{"cover": "封面副標（20 字內）", "analysis": "專題章節標語", "taiwan": "台灣新聞章節標語",
               "overseas": "旅外棒球章節標語", "global": "國際章節標語", "tracking": "延續追蹤標語", "closing": "結尾一句話"}}
             （每句 18 字內，口語、有活力，例如「羽球再奪冠，中華台北本週 3 金」）,
  "quiz": [{{"q": "題目", "options": ["A", "B", "C", "D"], "answer": "正確選項文字", "explain": "解說（30 字內）"}}]（3 題，答案必須能在本週新聞中找到）,
  "talking": {{"opening": "開場白（60 字內）", "transitions": {{"analysis": "", "taiwan": "", "overseas": "", "global": ""}},
               "closing": "結語（50 字內）"}}
}}"""

def materials(events, analyses):
    items = [{"id": i, "region": e.get("region"), "title": e["title"], "summary": (e.get("summary") or "")[:120],
              "numbers": e.get("key_numbers", [])[:3]} for i, e in enumerate(events[:25])]
    try:
        r = ask_json(PROMPT.format(style=config.STYLE_RULES, items=json.dumps(items, ensure_ascii=False),
                                   analyses="、".join(e["title"] for e in analyses) or "（無）"),
                     label="materials", max_tokens=5000)
    except Exception as ex:
        print("簡報素材產生失敗，改用預設：", str(ex)[:120])
        r = {}
    r = apply_terms(r) if isinstance(r, dict) else {}
    ok = lambda x: isinstance(x, dict) and isinstance(x.get("id"), int) and 0 <= x["id"] < len(items)
    top = [{"event": events[x["id"]], "why": x.get("why", "")} for x in r.get("top3", []) if ok(x)][:3]
    for e in events:                                # 後備：依重要度補足
        if len(top) >= 3:
            break
        if all(t["event"] is not e for t in top):
            top.append({"event": e, "why": e.get("why_matters") or e.get("special_reason") or ""})
    nums = [x for x in r.get("key_numbers", []) if ok(x)][:4]
    if not nums:
        nums = [{"number": n.split("｜")[0], "label": n.split("｜")[-1], "id": i}
                for i, e in enumerate(events[:10]) for n in e.get("key_numbers", [])[:1]][:4]
    for n in nums:
        n["source_title"] = events[n["id"]]["title"]
    defaults = {"cover": "本週體育大事一次看", "analysis": "從台灣的角度看本週", "taiwan": "台灣體育焦點",
                "overseas": "旅外棒球動態", "global": "國際體育大事", "tracking": "事件後續追蹤", "closing": "下週見！"}
    slogans = {**defaults, **{k: v for k, v in (r.get("slogans") or {}).items() if isinstance(v, str) and v.strip()}}
    quiz = [q for q in r.get("quiz", []) if isinstance(q, dict) and q.get("q") and q.get("answer")][:3]
    talking = r.get("talking") if isinstance(r.get("talking"), dict) else {}
    return {"top3": top, "key_numbers": nums, "slogans": slogans, "quiz": quiz, "talking": talking}
