"""範例資料（虛構，僅供測試資料包格式，非真實新聞）"""
def _s(region):
    return {"taiwan": [{"name": "中央社", "url": "https://www.cna.com.tw/news/aspt/example.aspx", "tier": 2},
                       {"name": "中華職棒", "url": "https://www.cpbl.com.tw/example", "tier": 1}],
            "overseas": [{"name": "MLB", "url": "https://www.mlb.com/player/000000", "tier": 1}],
            "global": [{"name": "BBC Sport", "url": "https://www.bbc.com/sport/example", "tier": 2}]}[region]

def _e(i, region, sport, imp, **kw):
    e = {"title": f"【範例】{ {'taiwan': '台灣', 'overseas': '旅外', 'global': '國際'}[region]}{sport}新聞 {i}",
         "date": f"2026-10-{15 + i % 7}", "sport": sport, "region": region, "importance": imp,
         "summary": "這是範例摘要。實際執行時，Gemini 會根據各媒體的原文，用自己的話寫成 80 到 150 字的重點與數據。",
         "sources": _s(region), "best_tier": 1 if region != "global" else 2, "verdict": "多來源一致",
         "key_numbers": [f"{i}｜範例數字說明"]}
    e.update(kw)
    return e

A = {"overview": "範例：賽事名稱、日期與目前進行階段。", "performance": "範例：中華台北本週取得佳績，關鍵選手表現穩定。",
     "notable": ["範例：一場比賽出現爭議判決", "範例：主力選手賽前傷勢"], "significance": "範例：可能影響後續積分，預期下週進入決賽。"}
EVENTS = [
    _e(1, "taiwan", "羽球", 5, is_special=True, title="【範例】中華台北羽球選手奪下國際賽冠軍", analysis=A),
    _e(2, "taiwan", "棒球", 4, track=True), _e(3, "taiwan", "籃球", 3), _e(4, "taiwan", "桌球", 4), _e(5, "taiwan", "排球", 3),
    _e(6, "overseas", "棒球", 4, player="範例投手（Example A）", team="MLB／範例隊", line="6局 1自責 8K 勝投"),
    _e(7, "overseas", "棒球", 3, player="範例打者（Example B）", team="3A／範例隊", line="4打數 2安打 1轟"),
    _e(8, "global", "綜合", 5, taiwan_link=True, title="【範例】亞洲綜合賽事整體動態", analysis=A),
    _e(9, "global", "足球", 5, why_matters="範例：決定本季冠軍歸屬"),
    _e(10, "global", "網球", 4, why_matters="範例：打破公開賽紀錄", status="ongoing"),
]
WEEK = {"events": EVENTS, "excluded": [{"title": "【範例】無法查證的傳聞", "exclude_reason": "只有標題、資訊不足"}],
        "items": [], "files": ["sample"], "degraded": False,
        "upcoming": [{"date": "2026-10-27", "sport": "棒球", "title": "範例賽程 A", "region": "taiwan"},
                     {"date": "2026-10-29", "sport": "足球", "title": "範例賽程 B", "region": "global"}]}
ANALYSES = [EVENTS[0], EVENTS[7]]
MATS = {"top3": [{"event": EVENTS[0], "why": "範例：中華台北選手的歷史性成績"},
                 {"event": EVENTS[5], "why": "範例：旅外投手本季最佳表現"},
                 {"event": EVENTS[8], "why": "範例：全球關注的冠軍歸屬"}],
        "key_numbers": [{"number": "8K", "label": "範例投手單場三振", "id": 5, "source_title": EVENTS[5]["title"]},
                        {"number": "3 金", "label": "中華台北本週金牌數", "id": 0, "source_title": EVENTS[0]["title"]}],
        "slogans": {"cover": "羽球奪冠，旅外開轟", "analysis": "從台灣看本週", "taiwan": "台灣體育焦點",
                    "overseas": "旅外好手發威", "global": "世界在關注什麼", "tracking": "事件後續", "closing": "下週見！"},
        "quiz": [{"q": "範例：本週哪位旅外投手單場 8K？", "options": ["範例投手", "B", "C", "D"], "answer": "範例投手",
                  "explain": "範例：6 局 1 自責分拿下勝投"}],
        "talking": {"opening": "範例開場白。", "transitions": {"taiwan": "接下來看台灣。"}, "closing": "範例結語。"}}
TRACKING = [{"title": "【範例】某選手傷勢", "since": "2026-10-12", "weeks": 2, "has_update": True,
             "update": "範例：已完成復健，預計回到一軍。", "closed": False,
             "sources": [{"name": "中央社", "url": "https://www.cna.com.tw/x", "tier": 2}]}]
