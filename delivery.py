"""
寄送資料包
  方式 A（預設）：Email 附件（預覽版 06:45、正式版 07:30，都寄給 MAIL_TO）
  方式 B（選用）：正式版同時存進 Google 雲端硬碟（週報內容轉成 Google 文件），
                  在 Gemini Notebook 可直接從雲端硬碟選取。設定好 GDRIVE_* 四個密鑰才會啟用。
"""
import json, smtplib
from email.message import EmailMessage
from pathlib import Path
import requests
import config

def mail(subject, body, attachments=()):
    if not (config.SMTP_HOST and config.MAIL_TO):
        print("未設定 Email，略過寄送：", subject); return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_USER, config.MAIL_TO, subject
    msg.set_content(body)
    for f in attachments:
        f = Path(f)
        sub = {"pdf": ("application", "pdf"), "txt": ("text", "plain"), "md": ("text", "markdown")}.get(
            f.suffix[1:], ("application", "octet-stream"))
        msg.add_attachment(f.read_bytes(), maintype=sub[0], subtype=sub[1], filename=f.name)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls(); s.login(config.SMTP_USER, config.SMTP_PASS); s.send_message(msg)
    print("已寄出：", subject)

# ---------- 方式 B：Google 雲端硬碟 ----------
def _drive_token():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": config.GDRIVE_CLIENT_ID, "client_secret": config.GDRIVE_CLIENT_SECRET,
        "refresh_token": config.GDRIVE_REFRESH_TOKEN, "grant_type": "refresh_token"})
    r.raise_for_status()
    return r.json()["access_token"]

def _drive_upload(token, path, name, mime_src, as_google_doc=False):
    meta = {"name": name}
    if config.GDRIVE_FOLDER_ID:
        meta["parents"] = [config.GDRIVE_FOLDER_ID]
    if as_google_doc:
        meta["mimeType"] = "application/vnd.google-apps.document"    # HTML 轉成 Google 文件
    files = {"metadata": ("metadata", json.dumps(meta), "application/json; charset=UTF-8"),
             "file": (name, Path(path).read_bytes(), mime_src)}
    r = requests.post("https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,webViewLink",
                      headers={"Authorization": f"Bearer {token}"}, files=files, timeout=60)
    r.raise_for_status()
    return r.json().get("webViewLink", "")

def to_drive(files, date_str):
    """回傳雲端硬碟連結清單；未啟用或失敗時回傳空清單（不影響 Email）"""
    if not config.DRIVE_ENABLED:
        return []
    try:
        tok = _drive_token()
        out = [("週報內容（Google 文件）", _drive_upload(tok, files["html"], f"週報內容_{date_str}", "text/html", True)),
               ("簡報指示", _drive_upload(tok, files["prompt"], f"簡報指示_{date_str}.txt", "text/plain")),
               ("原文連結", _drive_upload(tok, files["links"], f"原文連結_{date_str}.txt", "text/plain"))]
        print("已存進 Google 雲端硬碟")
        return out
    except Exception as ex:
        print("⚠️ 存入雲端硬碟失敗（Email 照常寄送）：", str(ex)[:200])
        return []
