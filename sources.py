"""
新聞來源分層（可自行增減）
  第一層：官方單位　第二層：通訊社與可信媒體　第三層：一般主要媒體　第四層：其他
  不採用：評論平台、轉會傳聞網站
Google 新聞的項目會依「原始媒體網址」或「媒體名稱」判斷層級。
"""
from urllib.parse import urlparse

TIERS = {
    1: {
        "國際奧會": ["olympics.com"], "FIFA": ["fifa.com"], "UEFA": ["uefa.com"],
        "英超": ["premierleague.com"], "NBA": ["nba.com"], "MLB": ["mlb.com"], "小聯盟": ["milb.com"],
        "日本職棒": ["npb.jp"], "韓國職棒": ["koreabaseball.com"], "WBSC": ["wbsc.org"],
        "ATP": ["atptour.com"], "WTA": ["wtatennis.com"], "BWF": ["bwfbadminton.com"],
        "WTT": ["worldtabletennis.com"], "ITTF": ["ittf.com"], "F1": ["formula1.com"],
        "世界田徑": ["worldathletics.org"], "亞奧理事會": ["ocasia.org"], "NFL": ["nfl.com"],
        "體育署": ["sa.gov.tw"], "中華奧會": ["tpenoc.net"], "中華職棒": ["cpbl.com.tw"],
        "TPBL": ["tpbl.basketball"], "P. LEAGUE+": ["pleagueofficial.com"],
    },
    2: {
        "Reuters": ["reuters.com"], "AP": ["apnews.com"], "AFP": ["afp.com"],
        "中央社": ["cna.com.tw"], "公視": ["pts.org.tw"],
        "ESPN": ["espn.com", "espn.co.uk"], "BBC Sport": ["bbc.com", "bbc.co.uk"],
    },
    3: {
        "Sky Sports": ["skysports.com"], "The Guardian": ["theguardian.com"],
        "CBS Sports": ["cbssports.com"], "Yahoo Sports": ["sports.yahoo.com"],
        "聯合報": ["udn.com"], "自由時報": ["ltn.com.tw"], "中時": ["chinatimes.com"],
        "ETtoday": ["ettoday.net"], "TVBS": ["tvbs.com.tw"], "三立新聞": ["setn.com"],
        "Yahoo奇摩新聞": ["tw.news.yahoo.com"], "鏡週刊": ["mirrormedia.mg"],
    },
}
NOT_EVIDENCE = {"運動視界": ["sportsv.net"], "Transfermarkt": ["transfermarkt.com", "transfermarkt.us"]}
TIER_LABEL = {1: "第一層・官方", 2: "第二層・通訊社", 3: "第三層・媒體", 4: "第四層・其他"}
# Google 新聞只給媒體名稱時用的對照
NAME_HINTS = {"中央社": 2, "CNA": 2, "公視": 2, "Reuters": 2, "路透": 2, "AP News": 2, "ESPN": 2,
              "BBC": 2, "MLB.com": 1, "中華職棒": 1}

def _match(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)

def classify(url: str, name_hint: str = ""):
    """回傳 (媒體名稱, 層級)；不採用的來源回傳 (名稱, None)"""
    host = urlparse(url or "").netloc.lower().split(":")[0]
    for name, domains in NOT_EVIDENCE.items():
        if _match(host, domains):
            return name, None
    for tier in (1, 2, 3):
        for name, domains in TIERS[tier].items():
            if _match(host, domains):
                return name, tier
    for key, tier in NAME_HINTS.items():
        if key.lower() in (name_hint or "").lower():
            return name_hint, tier
    return (name_hint or host.removeprefix("www.") or "未知來源"), 4

def best_tier(sources) -> int:
    return min((s["tier"] for s in sources if s.get("tier")), default=9)
