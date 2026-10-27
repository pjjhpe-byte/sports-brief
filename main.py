"""
全球體育週報 v7（免費版：Gemini API + Gemini Notebook）
  python main.py feeds     # 檢查各新聞來源是否抓得到（啟動時先跑一次）
  python main.py collect   # 週五 06:00：蒐集週一～週四並查證
  python main.py monday    # 週一 05:30：蒐集週末 → 專題分析 → 簡報素材 → 產出資料包 → 寄預覽版
  python main.py send      # 週一 07:30：寄正式版（若已暫停則不寄）
  python main.py hold      # 手動：暫停本週正式版
  python main.py sendnow   # 手動：修正後立即寄正式版（解除暫停）
  python main.py report    # 手動：用已蒐集資料重新產出資料包並寄預覽版
  python main.py annual    # 12/28：年度回顧
  python main.py demo      # 不需 API Key，用範例資料產出資料包
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import config, delivery, archive

def _files(d):
    s = d.strftime("%Y%m%d")
    o = config.OUTPUT_DIR
    return {"pdf": o / f"週報內容_{s}.pdf", "md": o / f"週報內容_{s}.md", "html": o / f"週報內容_{s}.html",
            "prompt": o / f"簡報指示_{s}.txt", "links": o / f"原文連結_{s}.txt"}

def _hold(d):
    return config.OUTPUT_DIR / f"HOLD_{d:%Y%m%d}"

def latest_report(now):
    ds = sorted(f.stem.split("_")[1] for f in config.OUTPUT_DIR.glob("stats_*.json"))
    return datetime.strptime(ds[-1], "%Y%m%d").replace(tzinfo=now.tzinfo) if ds else now - timedelta(days=now.weekday())

def _summary(d):
    md = _files(d)["md"].read_text(encoding="utf-8")
    lines, keep, quote = md.splitlines(), [], 0
    for l in lines:
        if l.startswith("## 三、"):
            break                                   # 只取到「最該關注的 3 件事」
        if l.startswith("> "):
            quote += 1
            if quote > 1 and not l.startswith("> 資料提醒"):
                continue
        if l.startswith(("# ", "> ", "### ", "為什麼重要", "## 二")):
            keep.append(l.lstrip("#> ").strip())
    return "\n".join(keep)

STEPS = """【本週簡報製作（約 5 分鐘）】
1. 開啟 Gemini Notebook（notebooklm.google.com）→ 新增筆記本
2. 上傳附件「週報內容_*.pdf」當作來源
3. Studio → 簡報 → 自訂 → 貼上「簡報指示_*.txt」中的【簡報指示】→ 產生
（想做 Podcast 或資訊圖表，指示也在同一個檔案裡）"""

def report(now):
    from analyzer import load_week, pick_analysis, analyze, week_stats
    from extras import materials
    import tracking, package
    week = load_week(now)
    if not week["events"]:
        sys.exit("本週沒有經查證的資料，無法產出")
    analyses = [analyze(e) for e in pick_analysis(week["events"])]
    trk = tracking.run(now, week["events"], week["items"])
    mats = materials(week["events"], analyses)
    stats = week_stats(week, analyses)
    files = package.build(week, analyses, mats, trk, stats, now)
    archive.save_stats(now.strftime("%Y%m%d"), stats)
    archive.rebuild_index()
    print("已產出：", *[str(f) for f in files.values()], sep="\n  ")
    for w in stats["warnings"]:
        print("⚠️", w)
    send_preview(now)

def send_preview(d):
    f = _files(d)
    link = f"{config.REPO_URL}/actions/workflows/sports-brief.yml" if config.REPO_URL else "GitHub → Actions → 全球體育週報"
    body = (f"【這是預覽版】約 07:30 會自動寄出正式版。\n"
            f"內容有問題要暫停：打開 {link} → Run workflow → task 輸入 hold。\n修正後要寄出：task 輸入 sendnow。\n\n"
            + "=" * 30 + "\n" + _summary(d) + "\n\n" + STEPS)
    delivery.mail(f"【預覽】體育週報資料包 {d:%Y/%m/%d}", body, [f["pdf"], f["prompt"], f["links"]])

def send(d, force=False):
    f, h = _files(d), _hold(d)
    if h.exists() and not force:
        print("本週正式版已暫停（HOLD）。修正後請執行 sendnow。"); return
    if h.exists():
        h.unlink()
    if not all(f[k].exists() for k in ("pdf", "prompt", "links")):
        delivery.mail(f"⚠️ 體育週報 {d:%Y/%m/%d} 產生失敗",
                      "本週資料包未成功產生。請到 GitHub → Actions 點開紅色 ✗ 的紀錄查看錯誤，"
                      "修正後執行 task=monday，確認預覽版後再執行 task=sendnow。")
        return
    drive = delivery.to_drive(f, d.strftime("%Y%m%d"))
    extra = ("\n\n【已存進 Google 雲端硬碟】在 Gemini Notebook 新增來源時選「雲端硬碟」即可：\n"
             + "\n".join(f"- {n}：{u}" for n, u in drive)) if drive else ""
    delivery.mail(f"體育週報資料包 {d:%Y/%m/%d}", STEPS + extra + "\n\n" + "=" * 30 + "\n" + _summary(d),
                  [f["pdf"], f["prompt"], f["links"]])

def feeds():
    import fetcher
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    items, health = fetcher.collect_items(now - timedelta(days=4), now)
    print(f"{'則數':>4}  來源")
    for src, n, err in health:
        print(f"{n:>4}  {src}" + (f"  ⚠️ {err}" if err else ("  ⚠️ 無資料" if n == 0 else "")))
    try:
        p = fetcher.taiwan_players(now.year)
        print(f"MLB 官方數據：找到台灣出生球員 {len(p)} 人（{', '.join(x['name'] for x in p[:6])}…）")
    except Exception as ex:
        print("⚠️ MLB 官方數據無法連線：", ex)
    print(f"合計 {len(items)} 則（去重後）")

def demo(now):
    from sample_data import WEEK, ANALYSES, MATS, TRACKING
    from analyzer import week_stats
    import package
    week = {**WEEK, "start": now.date() - timedelta(days=6), "end": now.date()}
    stats = week_stats(week, ANALYSES)
    stats["warnings"] = ["範例資料，非真實新聞"] + stats["warnings"]
    files = package.build(week, ANALYSES, MATS, TRACKING, stats, now)
    archive.save_stats(now.strftime("%Y%m%d"), stats)
    archive.rebuild_index()
    print("已產出：", *[str(f) for f in files.values()], sep="\n  ")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    if cmd in ("collect", "monday", "report", "annual") and not config.GEMINI_API_KEY:
        sys.exit("找不到 GEMINI_API_KEY，請到 GitHub Secrets 設定")
    if cmd == "collect":
        from collector import collect
        collect(now)
    elif cmd == "monday":
        from collector import collect
        collect(now)
        report(now)
    elif cmd == "report":
        report(now)
    elif cmd == "send":
        send(now)
    elif cmd == "hold":
        d = latest_report(now)
        _hold(d).write_text("paused", encoding="utf-8")
        print(f"已暫停 {d:%Y/%m/%d} 的正式版")
    elif cmd == "sendnow":
        send(latest_report(now), force=True)
    elif cmd == "annual":
        try:
            files = archive.annual(now)
        except Exception as ex:
            print("年度回顧失敗：", ex)
            delivery.mail(f"⚠️ {now.year} 年度回顧產生失敗",
                          "可能是 Gemini 免費額度暫時用完。請隔天到 GitHub → Actions 手動執行 task=annual。")
            sys.exit(1)
        if files:
            delivery.mail(f"{now.year} 全球體育年度回顧", Path(files[0]).read_text(encoding="utf-8"), files[1:])
    elif cmd == "feeds":
        feeds()
    elif cmd == "demo":
        demo(now)
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
