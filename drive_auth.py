"""
【方式 B 專用】取得 Google 雲端硬碟授權（只需在自己電腦執行一次）
用法：
  1. 依 README「方式 B」在 Google Cloud 建立「電腦版應用程式」OAuth 用戶端，取得 Client ID 與 Client Secret
  2. 在自己電腦執行：python tools/drive_auth.py
  3. 依提示貼上 Client ID、Client Secret，瀏覽器會開啟 Google 授權頁，同意後回到此視窗
  4. 畫面會顯示 GDRIVE_REFRESH_TOKEN，連同 Client ID／Secret 一起存進 GitHub Secrets
權限範圍只有 drive.file：程式只能看到「自己建立的檔案」，碰不到你雲端硬碟裡的其他檔案。
"""
import http.server, json, threading, urllib.parse, urllib.request, webbrowser

SCOPE = "https://www.googleapis.com/auth/drive.file"
PORT = 8765

def main():
    cid = input("貼上 Client ID：").strip()
    secret = input("貼上 Client Secret：").strip()
    redirect = f"http://127.0.0.1:{PORT}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent"})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got["code"] = q.get("code", [""])[0]
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write("授權完成，可以關閉此頁，回到終端機。".encode("utf-8"))
        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print("正在開啟瀏覽器；若沒有自動開啟，請手動打開：\n" + url)
    webbrowser.open(url)
    while "code" not in got:
        pass
    data = urllib.parse.urlencode({"code": got["code"], "client_id": cid, "client_secret": secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    tok = json.loads(urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data).read())
    print("\n請把下列三項存進 GitHub Secrets：")
    print("GDRIVE_CLIENT_ID     =", cid)
    print("GDRIVE_CLIENT_SECRET =", secret)
    print("GDRIVE_REFRESH_TOKEN =", tok.get("refresh_token", "（沒有取得，請重新執行並確認選了同意）"))

if __name__ == "__main__":
    main()
