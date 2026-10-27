"""
產生每週「資料包」（交給 Gemini Notebook 製作簡報）
  1. 週報內容_YYYYMMDD.pdf / .md   → 上傳到 Gemini Notebook 當作來源
  2. 簡報指示_YYYYMMDD.txt         → 貼到 Gemini Notebook 的自訂指示（含 Podcast、資訊圖表指示）
  3. 原文連結_YYYYMMDD.txt         → 選用：貼到 Gemini Notebook 當作額外來源
內容先組成「區塊清單」，再分別輸出成 PDF、Markdown、HTML（雲端硬碟用）。
"""
import html, math, os
from pathlib import Path
from xml.sax.saxutils import escape
import config
from sources import TIER_LABEL

TAG = {"taiwan": "【台灣】", "overseas": "【旅外】", "global": ""}

# ---------- 組內容 ----------
def _src_lines(srcs):
    return [("src", f"來源（{TIER_LABEL.get(s.get('tier'), '')}）：{s.get('name','')}　{s.get('url','')}")
            for s in sorted(srcs or [], key=lambda s: s.get("tier", 9))[:3]]

def _event(e):
    tags = TAG.get(e.get("region"), "") + ("【台灣相關】" if e.get("taiwan_link") and e.get("region") == "global" else "") \
        + ("【特殊事件】" if e.get("is_special") else "") + ("【進行中】" if e.get("status") == "ongoing" else "")
    b = [("h3", f"{tags}{e['title']}"),
         ("meta", f"{e.get('sport','')}｜{e.get('date','')}｜重要度 {e.get('importance','-')}/5"
                  + (f"｜查證：{e['verdict']}" if e.get("verdict") else "")),
         ("p", e.get("summary") or "")]
    if e.get("line"):
        b.append(("p", f"成績：{e.get('player','')}（{e.get('team','')}）{e['line']}"))
    if e.get("region") == "global" and not e.get("taiwan_link") and e.get("why_matters"):
        b.append(("p", "為何重要：" + e["why_matters"]))
    if e.get("key_numbers"):
        b.append(("p", "關鍵數字：" + "；".join(e["key_numbers"][:3])))
    if e.get("note"):
        b.append(("meta", "查證說明：" + e["note"]))
    return b + _src_lines(e.get("sources"))

def build_blocks(week, analyses, mats, tracking, stats):
    ev = week["events"]
    by = lambda r: [e for e in ev if e.get("region") == r]
    s = mats["slogans"]
    B = [("h1", f"全球體育週報資料包　{week['start']:%Y/%m/%d} – {week['end']:%Y/%m/%d}"),
         ("meta", f"台灣 {stats['taiwan']} 則｜旅外棒球 {stats['overseas']} 則｜國際 {stats['global']} 則｜"
                  f"專題分析 {stats['analysis']} 則｜第一、二層來源 {stats['tier12_pct']}%"),
         ("p", "本資料包的每則新聞皆來自實際報導，經 AI 改寫與跨來源比對；製作簡報時請只使用本文件內容，並保留來源。"),
         ("p", "封面副標：" + s["cover"])]
    for w in stats.get("warnings", []):
        B.append(("meta", "資料提醒：" + w))

    B += [("h2", "一、本週關鍵數字")]
    B += [("li", f"{n['number']}：{n['label']}（出自：{n['source_title']}）") for n in mats["key_numbers"]] or [("p", "本週無")]

    B += [("h2", "二、本週最該關注的 3 件事")]
    for k, t in enumerate(mats["top3"]):
        B += [("h3", f"{k + 1}. {TAG.get(t['event'].get('region'), '')}{t['event']['title']}"),
              ("p", "為什麼重要：" + t["why"])]

    B += [("h2", "三、台灣關聯專題分析　" + s["analysis"])]
    done = [e for e in analyses if e.get("analysis")]
    if not done:
        B.append(("p", "本週沒有符合條件的事件（需與台灣高度相關、重要度高且有官方或通訊社來源）。"))
    for e in done:
        a = e["analysis"]
        B += [("h3", "■ " + e["title"]), ("h4", "賽事概況"), ("p", a.get("overview", "")),
              ("h4", "中華台北／選手表現"), ("p", a.get("performance", "")), ("h4", "值得注意的狀況")]
        B += [("li", x) for x in a.get("notable", [])] or [("p", "—")]
        B += [("h4", "對台灣的意義與後續"), ("p", a.get("significance", ""))] + _src_lines(e.get("sources"))

    B += [("h2", "四、台灣體育新聞　" + s["taiwan"])]
    for e in by("taiwan"):
        B += _event(e)

    ov = by("overseas")
    B += [("h2", "五、旅外棒球動態　" + s["overseas"])]
    rows = [[e.get("player") or e["title"], e.get("team", ""), e["line"]] for e in ov if e.get("line")]
    if rows:
        B.append(("table", [["選手", "聯盟／球隊", "成績"]] + rows))
    for e in ov:
        B += _event(e)

    B += [("h2", "六、國際體育大事　" + s["global"])]
    for e in by("global"):
        B += _event(e)

    B += [("h2", "七、事件延續追蹤　" + s["tracking"])]
    if not tracking:
        B.append(("p", "目前沒有追蹤中的事件。"))
    for t in tracking:
        if t.get("new"):
            B.append(("li", f"{t['title']}（本週開始追蹤，後續幾週會持續關注）"))
            continue
        B.append(("li", f"{t['title']}（追蹤第 {t['weeks']} 週）：{t['update'] if t['has_update'] else '本週無新進展'}"
                        + ("【已告一段落】" if t.get("closed") else "")))
        B += _src_lines(t.get("sources"))

    B += [("h2", "八、下週賽程看點")]
    B += [("li", f"{u.get('date','')}　{TAG.get(u.get('region'), '')}{u.get('sport','')}｜{u.get('title','')}")
          for u in week.get("upcoming", [])] or [("p", "（本週新聞中沒有明確的下週賽程）")]

    B += [("h2", "九、本週體育小測驗")]
    for k, q in enumerate(mats["quiz"]):
        B += [("h3", f"第 {k + 1} 題：{q['q']}"), ("p", "選項：" + "／".join(q.get("options", []))),
              ("p", f"答案：{q['answer']}。{q.get('explain', '')}")]

    t = mats.get("talking") or {}
    B += [("h2", "十、講稿重點")]
    if t.get("opening"):
        B.append(("p", "開場：" + t["opening"]))
    names = {"analysis": "專題", "taiwan": "台灣新聞", "overseas": "旅外棒球", "global": "國際"}
    B += [("li", f"轉場到{names[k]}：{v}") for k, v in (t.get("transitions") or {}).items() if v and k in names]
    if t.get("closing"):
        B.append(("p", "結語：" + t["closing"]))
    B.append(("p", "結尾標語：" + s["closing"]))

    if week.get("excluded"):
        B += [("h2", "附錄、未納入的新聞（無法查證）"),
              ("meta", "以下事件因來源不足或說法不一而未採用，請勿放入簡報。")]
        B += [("li", f"{e['title']}（{e.get('exclude_reason','')}）") for e in week["excluded"][:15]]
    return B

# ---------- 輸出：Markdown / HTML / PDF ----------
def to_md(B):
    out = []
    for kind, v in B:
        if kind == "table":
            out += ["| " + " | ".join(v[0]) + " |", "|" + "---|" * len(v[0])] + ["| " + " | ".join(r) + " |" for r in v[1:]]
        else:
            if kind in ("h1", "h2", "h3", "h4", "p", "meta") and out and out[-1] != "":
                out.append("")
            out.append({"h1": "# ", "h2": "## ", "h3": "### ", "h4": "**", "li": "- ", "meta": "> ", "src": "  - "}.get(kind, "")
                       + v + ("**" if kind == "h4" else ""))
            if kind not in ("li", "src"):
                out.append("")
    return "\n".join(out) + "\n"

def to_html(B):
    out = ["<html><meta charset='utf-8'><body>"]
    for kind, v in B:
        if kind == "table":
            out.append("<table border='1'>" + "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>"
                                                       for r in v) + "</table>")
        elif kind in ("h1", "h2", "h3", "h4"):
            out.append(f"<{kind}>{html.escape(v)}</{kind}>")
        elif kind == "li":
            out.append(f"<ul><li>{html.escape(v)}</li></ul>")
        else:
            out.append(f"<p>{html.escape(v)}</p>")
    return "".join(out) + "</body></html>"

def _font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    for p in [os.getenv("PDF_FONT_PATH", ""), "C:/Windows/Fonts/msjh.ttc",
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]:
        if p and os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("ZH", p, subfontIndex=0))
                return "ZH"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("MSung-Light"))
    return "MSung-Light"

def to_pdf(B, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    F = _font()
    navy, red = colors.HexColor("#0A1F5C"), colors.HexColor("#D7141A")
    st = {"h1": ParagraphStyle("h1", fontName=F, fontSize=18, leading=26, textColor=navy, spaceAfter=8),
          "h2": ParagraphStyle("h2", fontName=F, fontSize=14, leading=21, textColor=navy, spaceBefore=12, spaceAfter=4),
          "h3": ParagraphStyle("h3", fontName=F, fontSize=11.5, leading=17, spaceBefore=6),
          "h4": ParagraphStyle("h4", fontName=F, fontSize=10.5, leading=15, textColor=red, spaceBefore=3),
          "p": ParagraphStyle("p", fontName=F, fontSize=10, leading=16, wordWrap="CJK"),
          "li": ParagraphStyle("li", fontName=F, fontSize=10, leading=16, wordWrap="CJK", leftIndent=10),
          "meta": ParagraphStyle("m", fontName=F, fontSize=8.5, leading=12, textColor=colors.grey, wordWrap="CJK"),
          "src": ParagraphStyle("s", fontName=F, fontSize=8, leading=11, textColor=colors.grey, wordWrap="CJK")}
    flow = []
    for kind, v in B:
        if kind == "table":
            t = Table([[Paragraph(escape(c), st["p"]) for c in r] for r in v], colWidths=[5 * cm, 4.5 * cm, 7.5 * cm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE5F7")),
                                   ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey)]))
            flow += [t, Spacer(1, 4)]
        else:
            flow.append(Paragraph(escape(("・" if kind == "li" else "") + v), st[kind]))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                      bottomMargin=1.8 * cm, title="全球體育週報資料包").build(flow)

# ---------- 簡報指示 ----------
def slide_plan(week, analyses, mats, tracking):
    ev = week["events"]
    n = lambda r: sum(1 for e in ev if e.get("region") == r)
    plan = [("封面", f"標題「全球體育週報」、期間、副標「{mats['slogans']['cover']}」"),
            ("本週關鍵數字", "用大字呈現「一、本週關鍵數字」的 3～4 個數字與說明"),
            ("本週最該關注的 3 件事", "三件事並列，各附一句為什麼重要")]
    plan += [("專題：" + e["title"][:24], "四格：賽事概況、中華台北／選手表現、值得注意的狀況、對台灣的意義")
             for e in analyses if e.get("analysis")]
    plan += [("台灣體育新聞" + (f"（{i + 1}）" if n("taiwan") > 3 else ""), "每頁 2～3 則，標題＋重點＋來源")
             for i in range(min(3, max(1, math.ceil(n("taiwan") / 3))))]
    if n("overseas"):
        plan += [("旅外棒球動態", "左側本週亮點選手大字成績，右側成績表")]
    plan += [("國際體育大事", "每則一句重點與「為何重要」")] * min(2, max(1, math.ceil(n("global") / 3)))
    if any(not t.get("new") for t in tracking):
        plan += [("事件延續追蹤", "時間軸或狀態列表")]
    if week.get("upcoming"):
        plan += [("下週賽程看點", "日期色塊＋賽事")]
    if mats["quiz"]:
        plan += [("本週體育小測驗", "3 題選擇題，答案放下一頁或頁尾"), ("小測驗解答", "答案與解說")]
    plan += [("結尾", f"結尾標語「{mats['slogans']['closing']}」")]
    while len(plan) > config.DECK_MAX_SLIDES:      # 超過 20 頁時先刪減台灣、國際分頁
        for i in range(len(plan) - 1, -1, -1):
            if plan[i][0].startswith(("台灣體育新聞（", "國際體育大事", "小測驗解答")):
                plan.pop(i)
                break
        else:
            plan.pop(-2)
    return plan

def instructions(week, analyses, mats, tracking, stem):
    plan = slide_plan(week, analyses, mats, tracking)
    pages = "\n".join(f"{i + 1}. {t}：{d}" for i, (t, d) in enumerate(plan))
    s = mats["slogans"]
    deck = f"""請根據來源「{stem}」製作一份簡報，共 {len(plan)} 頁：

{pages}

【要求】
- 對象：{config.DECK_AUDIENCE}；語言：繁體中文。
- 風格：活潑、有運動感；中華台北代表隊色系（深藍、紅、白）；多用大數字、圖示、對比色塊，少用大段文字。
- 各章節標題使用資料包中的標語：專題「{s['analysis']}」、台灣「{s['taiwan']}」、旅外「{s['overseas']}」、國際「{s['global']}」。
- 我國代表隊一律稱「中華台北」。
- 只使用來源中的資訊，不要加入來源以外的事實或數字；每則新聞在頁面角落標註媒體來源。
- 「附錄、未納入的新聞」不要放進簡報。"""
    audio = f"""請以兩位主持人輕鬆對談的方式，用繁體中文（台灣用語）介紹本週體育大事，約 8～10 分鐘。
開場先講「本週最該關注的 3 件事」，接著聊台灣關聯專題與旅外棒球，最後用小測驗第 1 題和聽眾互動。
只使用來源內容；我國代表隊稱「中華台北」；不要提到附錄中未納入的新聞。"""
    info = f"""請做一張直式資訊圖表「本週體育一頁看懂」：上方放本週關鍵數字，中間放最該關注的 3 件事，
下方放旅外棒球成績表。中華台北代表隊色系（深藍、紅、白），繁體中文，只使用來源內容並標註來源媒體。"""
    steps = f"""【Gemini Notebook 製作步驟】
1. 開啟 notebooklm.google.com（Gemini Notebook）→ 新增筆記本，命名「{stem}」
2. 新增來源 → 上傳「週報內容_*.pdf」（選用：再把「原文連結_*.txt」裡的網址逐一以「網站」加入）
3. 右側 Studio → 簡報（Slide deck）→ 自訂 → 貼上下方【簡報指示】→ 產生
4. 想要語音版：Studio → 語音摘要（Audio Overview）→ 自訂 → 貼上【Podcast 指示】
5. 想要一頁圖：Studio → 資訊圖表（Infographic）→ 貼上【資訊圖表指示】
※ 免費帳號每個筆記本的生成次數有限，建議每週開新筆記本。"""
    return f"{steps}\n\n===== 簡報指示（複製以下全部）=====\n{deck}\n\n===== Podcast 指示 =====\n{audio}\n\n===== 資訊圖表指示 =====\n{info}\n"

def links(week, analyses):
    seen, out = set(), []
    pri = [e for e in analyses] + week["events"]
    for e in pri:
        for s in sorted(e.get("sources", []), key=lambda s: s.get("tier", 9)):
            u = s.get("url", "")
            if u and u not in seen and s.get("tier", 9) <= 3:
                seen.add(u)
                out.append(f"{u}　# {s.get('name','')}｜{e['title'][:30]}")
                break
    return "以下網址可在 Gemini Notebook「新增來源 → 網站」逐一貼上（選用，最多 15 則）：\n" + "\n".join(out[:15]) + "\n"

def build(week, analyses, mats, tracking, stats, now):
    stem = f"週報內容_{now:%Y%m%d}"
    B = build_blocks(week, analyses, mats, tracking, stats)
    d = config.OUTPUT_DIR
    files = {"pdf": d / f"週報內容_{now:%Y%m%d}.pdf", "md": d / f"週報內容_{now:%Y%m%d}.md",
             "html": d / f"週報內容_{now:%Y%m%d}.html", "prompt": d / f"簡報指示_{now:%Y%m%d}.txt",
             "links": d / f"原文連結_{now:%Y%m%d}.txt"}
    files["md"].write_text(to_md(B), encoding="utf-8")
    files["html"].write_text(to_html(B), encoding="utf-8")
    to_pdf(B, files["pdf"])
    files["prompt"].write_text(instructions(week, analyses, mats, tracking, stem), encoding="utf-8")
    files["links"].write_text(links(week, analyses), encoding="utf-8")
    return files
