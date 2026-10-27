"""
呼叫 Gemini API（免費層）
  - 優先使用官方 google-genai 套件；沒安裝時改用 REST
  - 每次呼叫間隔 MIN_INTERVAL_SEC 秒，避免超過免費層每分鐘次數
  - 遇到額度用盡（429）會等待重試，仍失敗就改用備援模型
  - 每次呼叫記錄在 data/stats.csv（免費層不收費，只記次數與 token）
"""
import csv, json, re, time
from datetime import datetime
from zoneinfo import ZoneInfo
import config

_last_call = [0.0]
_calls = [0]

class QuotaExceeded(RuntimeError):
    """免費額度用完（主力與備援模型都失敗）"""

class AccessDenied(RuntimeError):
    """API Key 無權限（例如免費層不適用此專案），重試無用"""

def _sdk_call(model, prompt, max_tokens):
    from google import genai
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    r = client.models.generate_content(
        model=model, contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0.3, "max_output_tokens": max_tokens})
    u = getattr(r, "usage_metadata", None)
    return r.text, getattr(u, "prompt_token_count", 0) or 0, getattr(u, "candidates_token_count", 0) or 0

def _rest_call(model, prompt, max_tokens):
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3, "maxOutputTokens": max_tokens}}
    r = requests.post(url, json=body, headers={"x-goog-api-key": config.GEMINI_API_KEY}, timeout=180)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    d = r.json()
    text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    u = d.get("usageMetadata", {})
    return text, u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0)

def _call(model, prompt, max_tokens):
    try:
        import google.genai  # noqa: F401
        return _sdk_call(model, prompt, max_tokens)
    except ImportError:
        return _rest_call(model, prompt, max_tokens)

def _is_denied(ex):
    s = str(ex)
    return "403" in s or "PERMISSION_DENIED" in s or "API_KEY_INVALID" in s or "API key not valid" in s

def _is_busy(ex):
    s = str(ex)
    return "503" in s or "UNAVAILABLE" in s or "overloaded" in s.lower() or "disconnected" in s.lower()

def _is_quota(ex):
    s = str(ex)
    return "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower()

def ask_json(prompt: str, label: str, max_tokens: int = 8000):
    if _calls[0] >= config.MAX_CALLS_PER_RUN:
        raise QuotaExceeded(f"本次執行已達呼叫上限 {config.MAX_CALLS_PER_RUN} 次")
    last = None
    for model in (config.MODEL, config.FALLBACK_MODEL):
        for attempt in range(3):
            wait = config.MIN_INTERVAL_SEC - (time.time() - _last_call[0])
            if wait > 0:
                time.sleep(wait)
            _last_call[0] = time.time()
            try:
                _calls[0] += 1
                text, tin, tout = _call(model, prompt, max_tokens)
                _log(label, model, tin, tout)
                return _extract_json(text)
            except Exception as ex:
                last = ex
                print(f"[{label}] {model} 第 {attempt + 1} 次失敗：{str(ex)[:160]}")
                if _is_denied(ex):
                    raise AccessDenied(
                        "Gemini API 拒絕存取（403）。請確認 GitHub Secrets 的 GEMINI_API_KEY 正確，"
                        "且金鑰是用個人 Gmail 在 aistudio.google.com 建立。原始訊息：" + str(ex)[:200])
                if _is_busy(ex):                      # Google 端暫時忙碌：稍等後盡快改用備援模型
                    time.sleep(20)
                    if attempt >= 1:
                        break
                elif _is_quota(ex):
                    time.sleep(30 * (attempt + 1))
                    if attempt >= 1:
                        break                           # 換備援模型
                elif attempt < 2:
                    time.sleep(10)
    if last is not None and _is_quota(last):
        raise QuotaExceeded(str(last)[:200])
    raise RuntimeError(f"[{label}] 重試後仍失敗：{last}")

def _extract_json(text: str):
    text = re.sub(r"```(?:json)?", "", text or "")
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("回應中找不到 JSON：" + text[:200])
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[min(starts):end + 1])

def _log(label, model, tin, tout):
    new = not config.STATS_FILE.exists()
    with open(config.STATS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "label", "model", "input_tokens", "output_tokens"])
        w.writerow([datetime.now(ZoneInfo(config.TIMEZONE)).isoformat(timespec="minutes"), label, model, tin, tout])
    print(f"[{label}] {model}：輸入 {tin:,}／輸出 {tout:,} tokens")
