"""全域設定：可直接在 GitHub 網頁編輯此檔"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"          # 蒐集資料、追蹤清單、用量紀錄
OUTPUT_DIR = BASE_DIR / "output"      # 每週資料包（存檔）
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
STATS_FILE = DATA_DIR / "stats.csv"
TRACKING_FILE = DATA_DIR / "tracking.json"
TIMEZONE = "Asia/Taipei"

# ---------- Gemini API（免費層）----------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")               # 主力
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK", "gemini-3.5-flash-lite")  # 額度用完時改用
MIN_INTERVAL_SEC = 13         # 兩次呼叫最少間隔（約每分鐘 4～5 次，避免超過免費層限制）
MAX_CALLS_PER_RUN = 80        # 單次執行最多呼叫次數（保護免費額度）

# ---------- 新聞來源：媒體直接提供的 RSS ----------
# 執行 python main.py feeds 可檢查每個來源是否抓得到
RSS_FEEDS = [
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/rss.xml", "region": "global"},
    {"name": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml", "region": "global"},
    # ESPN 的 RSS 對 GitHub 伺服器回傳空白，改由下方英文 Google 新聞取得
]

# ---------- 新聞來源：直接讀取媒體的新聞列表頁 ----------
# 中央社體育列表：網址中的 12 位數字前 8 碼為日期（YYYYMMDD），可直接取得原文全文
HTML_LISTS = [
    {"name": "中央社", "url": "https://www.cna.com.tw/list/aspt.aspx", "region": "taiwan",
     "link_pattern": r"(?:https?://www\.cna\.com\.tw)?/news/aspt/(\d{12})\.aspx"},
]

# ---------- 新聞來源：Google 新聞 RSS 關鍵字搜尋 ----------
# 每個查詢會自動加上「when:4d」（最近 4 天）
# 一般字串用繁體中文介面搜尋；寫成 ["查詢", "en"] 則用英文介面（搜尋英文媒體時要用這個）
GNEWS_LOCALES = {"zh": "hl=zh-TW&gl=TW&ceid=TW:zh-Hant", "en": "hl=en-US&gl=US&ceid=US:en"}
GNEWS_QUERIES = {
    "taiwan": ["site:cna.com.tw 體育", "中華職棒", "TPBL OR 台灣職籃", "中華台北 國際賽",
               "台灣 羽球 OR 桌球 奪冠", "台灣 選手 決賽", "體育署"],
    "overseas": ["旅美 投手 OR 打者", "旅日 台灣 球員", "旅韓 台灣 球員", "台灣 大聯盟 OR 小聯盟"],
    "global": ["site:cna.com.tw 國際 體育", ["site:espn.com", "en"], ["site:reuters.com sports", "en"],
               ["site:apnews.com sports", "en"]],
}
MAX_ITEMS_PER_QUERY = 15
FETCH_ARTICLE_TEXT = True     # 是否下載原文全文供查證（抓不到時改用標題與摘要）
ARTICLE_CHARS = 2500          # 每篇原文最多取多少字給 AI

# ---------- MLB 官方數據（旅美球員）----------
MLB_API = "https://statsapi.mlb.com/api/v1"
MLB_LEVELS = {1: "MLB", 11: "3A", 12: "2A", 13: "高階1A", 14: "1A"}
OFFSEASON_MONTHS = [11, 12, 1, 2]     # 休賽季：改收簽約、轉隊、冬季聯盟、春訓

# ---------- 每週數量 ----------
TARGET = {"taiwan": 5, "overseas": 2}
GLOBAL_BASE = 3               # 與台灣無關的國際重大事件最多 3 則
GLOBAL_MAX = 5                # 含台灣相關賽事最多 5 則
OVERSEAS_MAX = 5
SPECIAL_THRESHOLD = 4
MAX_ANALYSIS = 3              # 台灣關聯專題分析每週上限
TRACK_MAX_WEEKS = 3
TRACK_MAX_ITEMS = 6

# ---------- 用語規範 ----------
STYLE_RULES = """【用語與撰寫規範】
- 我國代表隊一律寫「中華台北」，不寫「中華隊」「台灣隊」。
- 台灣旅外球員中文姓名以中央社寫法為準；第一次出現時附英文名，例如：林昱珉（Yu-Min Lin）。
- 摘要必須用自己的話改寫，不可照抄原文，直接引用不超過一句。
- 只能使用提供的資料中出現的事實與數字，不可自行補充或推測。
- 傷病只寫官方公布的內容。
- 使用繁體中文。"""
REPLACE_TERMS = {"中華隊": "中華台北", "台灣隊": "中華台北"}

# ---------- 簡報（交給 Gemini Notebook 製作）----------
DECK_AUDIENCE = os.getenv("DECK_AUDIENCE", "關心體育的一般聽眾（例如學校師生、同事）")
DECK_MAX_SLIDES = 20          # Gemini Notebook 每次最多 20 頁

# ---------- 寄送方式 ----------
# A（預設）：Email 附件；B：同時存進 Google 雲端硬碟（設定好 GDRIVE_* 密鑰才會啟用）
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
REPO_URL = os.getenv("REPO_URL", "")
GDRIVE_CLIENT_ID = os.getenv("GDRIVE_CLIENT_ID", "")
GDRIVE_CLIENT_SECRET = os.getenv("GDRIVE_CLIENT_SECRET", "")
GDRIVE_REFRESH_TOKEN = os.getenv("GDRIVE_REFRESH_TOKEN", "")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")
DRIVE_ENABLED = all([GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN])
