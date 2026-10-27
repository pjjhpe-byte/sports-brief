"""
每週兩次蒐集（台灣時間）
  週五 06:00 → 本週一 00:00 起至今
  週一 05:30 → 上週四 12:00 起至今（與週五重疊半天）
流程：抓 RSS／Google 新聞／MLB 官方數據 → Gemini 選題 → 撰寫與查證 → 規則把關 → 存 data/日期.json
"""
import json
from datetime import datetime, timedelta
import config, fetcher, editor
from llm import QuotaExceeded

def window(now: datetime) -> datetime:
    if now.weekday() == 0:
        return (now - timedelta(days=4)).replace(hour=12, minute=0, second=0, microsecond=0)
    return (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

def collect(now: datetime) -> str:
    since = window(now)
    items, health = fetcher.collect_items(since, now)
    print(f"抓到新聞 {len(items)} 則（{since:%m/%d %H:%M} 起）")
    for src, n, err in health:
        if n == 0:
            print(f"  ⚠️ 來源無資料：{src} {err}")
    try:
        mlb = [] if now.month in config.OFFSEASON_MONTHS else fetcher.mlb_week(since, now)
    except Exception as ex:
        print("MLB 官方數據抓取失敗：", ex); mlb = []
    print(f"MLB 官方數據：台灣球員出賽 {len(mlb)} 人")

    data = {"collected_at": now.isoformat(), "window_start": since.isoformat(),
            "health": health, "items": [{k: it[k] for k in ("id", "title", "link", "source", "tier",
                                                             "region_hint", "published")} for it in items]}
    if not items and not mlb:
        print("⚠️ 本次沒有抓到任何新聞，略過 AI 處理（報告將使用其他天的資料）")
        data.update(events=[], excluded=[], upcoming=[], degraded=False)
        path = config.DATA_DIR / f"{now:%Y-%m-%d}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return str(path)
    try:
        events, upcoming = editor.triage(items, since, now) if items else ([], [])
        print(f"Gemini 選題：{len(events)} 個事件")
        events = editor.write_and_verify(events, {it["id"]: it for it in items}, mlb)
        kept, excluded = editor.apply_rules(events)
        data.update(events=kept, excluded=excluded, upcoming=upcoming, degraded=False)
        print(f"查證完成：採用 {len(kept)} 則、未納入 {len(excluded)} 則")
    except QuotaExceeded as ex:
        # 降級模式：免費額度用完時，只保留高層級來源的標題，報告仍可產出
        print("⚠️ Gemini 免費額度不足，改用降級模式：", ex)
        top = [it for it in items if it["tier"] <= 2][:20]
        data.update(events=[{"title": it["title"], "region": it["region_hint"], "sport": "", "importance": 3,
                             "date": it["published"][:10], "summary": "（降級模式：僅列標題，未經 AI 整理）",
                             "sources": [{"name": it["source"], "url": it["link"], "tier": it["tier"]}],
                             "best_tier": it["tier"], "verdict": "未查證（降級模式）"} for it in top],
                    excluded=[], upcoming=[], degraded=True)
    path = config.DATA_DIR / f"{now:%Y-%m-%d}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("已存檔", path.name)
    return str(path)
