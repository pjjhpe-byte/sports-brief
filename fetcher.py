"""
抓取新聞與數據（不需 AI、不花錢）
  - 媒體 RSS（BBC Sport、ESPN 等）
  - Google 新聞 RSS 關鍵字搜尋（含中央社等台灣媒體）
  - 原文全文（供查證，抓不到就用標題與摘要）
  - MLB 官方數據：自動找出出生地為台灣的球員，抓本期間的每場成績
"""
import html, re, time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
import requests
import config
from sources import classify

UA = {"User-Agent": "Mozilla/5.0 (compatible; SportsBriefBot/2.0; weekly sports digest)"}
TAG = re.compile(r"<[^>]+>")

def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", s or ""))).strip()

def _get(url, timeout=20):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r

def _date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

def parse_feed(xml_text):
    """同時支援 RSS 2.0 與 Atom，回傳 [{title, link, summary, published, source_name, source_url}]"""
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    items = []
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        kids = {}
        for c in it:                                    # 同名標籤只取第一個
            kids.setdefault(c.tag.split("}")[-1], c)
        text = lambda *names: next(((kids[n].text or "").strip() for n in names if n in kids and kids[n].text), "")
        link = text("link")
        if not link and "link" in kids:
            link = kids["link"].get("href", "")
        src = kids.get("source")
        items.append({
            "title": _clean(text("title")),
            "link": link,
            "summary": _clean(text("description", "summary"))[:400],
            "published": _date(text("pubDate", "published", "updated")),
            "source_name": (src.text or "").strip() if src is not None else "",
            "source_url": src.get("url", "") if src is not None else "",
        })
    return items

def _within(item, since, until):
    p = item.get("published")
    return p is None or (since <= p <= until + timedelta(hours=1))

def _finalize(raw, region, origin, since, until):
    out = []
    for it in raw:
        if not it["title"] or not _within(it, since, until):
            continue
        is_gnews = "news.google.com" in it["link"]
        title = it["title"]
        if is_gnews and it["source_name"] and title.endswith(" - " + it["source_name"]):
            title = title[: -len(it["source_name"]) - 3]
        name, tier = classify(it["source_url"] if is_gnews else it["link"], it["source_name"] or origin)
        if tier is None:
            continue                                    # 評論平台、傳聞網站不採用
        out.append({"title": title, "link": it["link"], "summary": it["summary"],
                    "published": it["published"].isoformat() if it["published"] else "",
                    "source": name, "tier": tier, "region_hint": region, "via": "gnews" if is_gnews else "rss"})
    return out

def fetch_rss(since, until, health):
    items = []
    for f in config.RSS_FEEDS:
        try:
            got = _finalize(parse_feed(_get(f["url"]).text), f["region"], f["name"], since, until)
            health.append((f["url"], len(got), ""))
            items += got
        except Exception as ex:
            health.append((f["url"], 0, str(ex)[:80]))
    return items

def fetch_html_lists(since, until, health):
    """讀取媒體新聞列表頁（例如中央社體育），用網址中的日期篩選"""
    items = []
    for src in config.HTML_LISTS:
        try:
            page = _get(src["url"]).text
            got, seen = [], set()
            pat = re.compile(r'<a[^>]+href="(?P<u>' + src["link_pattern"].replace("(\\d{12})", "(?P<id>\\d{12})")
                             + r')"[^>]*>(?P<t>.*?)</a>', re.S)
            for m in pat.finditer(page):
                url, title = m.group("u"), _clean(m.group("t"))
                if url in seen or len(title) < 6:
                    continue
                seen.add(url)
                try:
                    d = datetime.strptime(m.group("id")[:8], "%Y%m%d").replace(tzinfo=until.tzinfo)
                except ValueError:
                    continue
                if since.date() <= d.date() <= until.date():
                    name, tier = classify(url, src["name"])
                    got.append({"title": title, "link": url, "summary": "", "published": d.isoformat(),
                                "source": name, "tier": tier, "region_hint": src["region"], "via": "list"})
            health.append((src["url"], len(got), ""))
            items += got
        except Exception as ex:
            health.append((src["url"], 0, str(ex)[:80]))
    return items

def gnews_url(q):
    return f"https://news.google.com/rss/search?q={quote_plus(q + ' when:4d')}&{config.GNEWS_TW}"

def fetch_gnews(since, until, health):
    items = []
    for region, qs in config.GNEWS_QUERIES.items():
        for q in qs:
            try:
                got = _finalize(parse_feed(_get(gnews_url(q)).text), region, "", since, until)
                got = got[:config.MAX_ITEMS_PER_QUERY]
                health.append((f"Google新聞：{q}", len(got), ""))
                items += got
            except Exception as ex:
                health.append((f"Google新聞：{q}", 0, str(ex)[:80]))
            time.sleep(1)
    return items

def collect_items(since, until):
    """抓取所有新聞並去除重複，回傳 (items, health)"""
    health = []
    items = fetch_html_lists(since, until, health) + fetch_rss(since, until, health) + fetch_gnews(since, until, health)
    seen, out = set(), []
    for it in items:
        k = re.sub(r"[\W_]+", "", it["title"].lower())[:30]
        if k in seen:
            continue
        seen.add(k)
        it["id"] = len(out)
        out.append(it)
    return out, health

# ---------- 原文 ----------
def resolve_link(url):
    """Google 新聞連結盡量轉成原始報導網址（轉不了就保留原連結）"""
    if "news.google.com" not in url:
        return url
    try:
        r = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        if "news.google.com" not in urlparse(r.url).netloc:
            return r.url
        m = re.search(r'data-n-au="([^"]+)"', r.text) or re.search(r'<a[^>]+href="(https?://(?!news\.google)[^"]+)"', r.text)
        if m:
            return html.unescape(m.group(1))
    except Exception:
        pass
    return url

def article_text(url):
    """抓原文段落文字；失敗回傳空字串"""
    if not config.FETCH_ARTICLE_TEXT or "news.google.com" in url:
        return ""
    try:
        page = _get(url, timeout=15).text
    except Exception:
        return ""
    page = re.sub(r"(?is)<(script|style|nav|footer|header|aside)[^>]*>.*?</\1>", " ", page)
    paras = [_clean(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", page)]
    text = " ".join(p for p in paras if len(p) > 25)
    return text[:config.ARTICLE_CHARS]

# ---------- MLB 官方數據 ----------
def _mlb(path, **params):
    return _get(f"{config.MLB_API}{path}", timeout=25).json() if not params else \
        requests.get(f"{config.MLB_API}{path}", params=params, headers=UA, timeout=25).json()

def taiwan_players(season):
    players = {}
    for sport_id, level in config.MLB_LEVELS.items():
        try:
            data = _mlb(f"/sports/{sport_id}/players", season=season)
        except Exception:
            continue
        for p in data.get("people", []):
            if (p.get("birthCountry") or "").lower() == "taiwan" and p["id"] not in players:
                players[p["id"]] = {"id": p["id"], "name": p.get("fullName", ""), "level": level, "sport_id": sport_id,
                                    "pos": (p.get("primaryPosition") or {}).get("abbreviation", ""),
                                    "team_id": (p.get("currentTeam") or {}).get("id")}
    return list(players.values())

def _line(group, s):
    if group == "pitching":
        res = "勝投" if s.get("wins") else "敗投" if s.get("losses") else "救援成功" if s.get("saves") else \
            "中繼成功" if s.get("holds") else ""
        return f"{s.get('inningsPitched','0')}局 {s.get('earnedRuns',0)}自責 {s.get('strikeOuts',0)}K {res}".strip()
    hr = f" {s['homeRuns']}轟" if s.get("homeRuns") else ""
    rbi = f" {s['rbi']}打點" if s.get("rbi") else ""
    return f"{s.get('atBats',0)}打數 {s.get('hits',0)}安打{hr}{rbi}"

def mlb_week(since, until):
    """回傳台灣球員在期間內的出賽紀錄（官方數據）"""
    out = []
    season = until.year
    for p in taiwan_players(season):
        games = []
        for group in ("pitching", "hitting"):
            try:
                data = requests.get(f"{config.MLB_API}/people/{p['id']}/stats", headers=UA, timeout=25,
                                    params={"stats": "gameLog", "season": season, "group": group,
                                            "sportId": p["sport_id"]}).json()
            except Exception:
                continue
            for sp in (data.get("stats") or [{}])[0].get("splits", []):
                d = sp.get("date", "")
                try:
                    dd = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
                except Exception:
                    continue
                if since - timedelta(days=1) <= dd <= until:
                    st = sp.get("stat", {})
                    if group == "hitting" and not st.get("plateAppearances"):
                        continue
                    if group == "pitching" and st.get("inningsPitched") in (None, "0.0"):
                        continue
                    games.append({"date": d, "group": group, "line": _line(group, st),
                                  "opp": (sp.get("opponent") or {}).get("name", "")})
            time.sleep(0.3)
        if games:
            out.append({**p, "games": sorted(games, key=lambda g: g["date"]),
                        "url": f"https://www.mlb.com/player/{p['id']}"})
    return out
