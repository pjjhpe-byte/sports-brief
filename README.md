# 全球體育週報 v7（免費版）

**分工**：程式（GitHub ＋ Gemini API 免費層）每週自動蒐集、查證、整理成「資料包」→ 你把資料包放進 **Gemini Notebook**，一鍵生成簡報。
**費用**：每月 0 元（GitHub 免費額度＋Gemini API 免費層＋Gemini Notebook 免費帳號）。

---

## 一、每週流程（台灣時間）

| 時間 | 自動執行 | 你要做的事 |
|---|---|---|
| 週五 06:00 | 抓週一～週四新聞 → Gemini 選題、改寫、查證 | — |
| 週一 05:30 | 抓週末新聞與查證 → 專題分析、延續追蹤、簡報素材 → 產出資料包 | — |
| 週一約 06:45 | 寄【預覽】資料包給你 | 看一下內容；有問題就執行 `hold` |
| 週一約 07:30 | 寄正式版資料包 | 上傳到 Gemini Notebook 生成簡報（約 5 分鐘） |
| 12/28 06:00 | 年度回顧 | — |

## 二、每週收到的資料包（3 個附件）

| 檔案 | 用途 |
|---|---|
| `週報內容_日期.pdf` | **上傳到 Gemini Notebook 當作來源**。含關鍵數字、最該關注 3 件事、台灣關聯專題、台灣新聞、旅外棒球（含成績表）、國際、延續追蹤、下週看點、小測驗、講稿重點，每則附來源網址與查證狀態 |
| `簡報指示_日期.txt` | 依當週內容自動寫好的**簡報指示**（20 頁以內的頁面架構＋風格要求），另附 Podcast、資訊圖表指示 |
| `原文連結_日期.txt` | 選用：本週重要報導的原文網址，可加進 Gemini Notebook 當額外來源 |

## 三、新聞來源與查證

**來源**（不需付費、不需 AI 搜尋）：
- 中央社體育列表頁（直接取得原文）
- BBC Sport、ESPN 的官方 RSS
- Google 新聞 RSS 關鍵字搜尋（中職、TPBL、中華台北、旅美／旅日／旅韓等）
- MLB 官方數據：自動找出台灣出生的球員（大聯盟～1A），抓取本週每場成績

**查證**：
1. 程式只採用實際存在的報導（網址都來自 RSS 或列表頁，不會有 AI 編造的網址）
2. Gemini 讀取原文，用自己的話改寫，並比對各來源的日期、比分、人名、數據
3. 規則把關：

| 情況 | 處理 |
|---|---|
| 多個來源一致 | 採用（標示「多來源一致」） |
| 單一官方或通訊社來源 | 採用（標示「單一可信來源」；只有標題時另標「細節請見原文」） |
| 只有一家第三層以下媒體 | 不採用，列入附錄 |
| 來源說法不一 | 不採用，列入附錄 |
| 旅外球員數據 | 以 MLB 官方數據為準 |
| 評論平台、轉會傳聞網站 | 一律不當作來源 |

**用語**：一律「中華台北」；旅外球員中文名依中央社寫法，首次出現附英文名。

## 四、Gemini 免費額度

- 每週約 10～15 次呼叫，在免費層範圍內
- 程式自動控制呼叫速度（約每 13 秒一次），額度不足時會自動改用較小的備援模型
- 仍然不足時進入**降級模式**：只列可信媒體的標題（不經 AI 整理），報告照常寄出並標註
- 免費層的內容可能被 Google 用來改進產品；體育新聞屬公開資訊，影響不大

---

## 五、啟動步驟

### 事前準備
- 解壓 `sports_brief_v7.zip`
- 一個 Google 帳號（申請 Gemini API Key、使用 Gemini Notebook）
- 一個 Gmail 帳號（寄出資料包，可與上面相同）
- 預計時間：設定約 30 分鐘、測試約 30 分鐘

### 步驟 1：申請 Gemini API Key（免費）
1. 到 **aistudio.google.com**，用 Google 帳號登入（需年滿 18 歲）
2. 左側 **Get API key** → **Create API key**
3. 複製金鑰（`AIza` 開頭）保存好
4. **不要**綁定付款方式，維持在免費層

### 步驟 2：申請 Gmail 應用程式密碼
1. **myaccount.google.com** → **安全性** → 開啟**兩步驟驗證**
2. 到 **myaccount.google.com/apppasswords** → 名稱填 `sports-brief` → 建立
3. 複製 16 碼密碼，**去掉空格**

### 步驟 3：建立 GitHub 儲存庫
1. **github.com** → 右上角 **+** → **New repository** → 名稱 `sports-brief` → **Private** → **Create repository**
2. 點 **uploading an existing file** → 把 `sports_brief_v7` 資料夾內**所有檔案與資料夾**拖入 → **Commit changes**
3. ⚠️ 確認有 `.github/workflows/sports-brief.yml`（隱藏資料夾常被略過）。沒有的話：
   **Add file** → **Create new file** → 檔名輸入 `.github/workflows/sports-brief.yml` → 用記事本開原檔全部複製貼上 → **Commit changes**

> **舊版（v6）repo 改用 v7**：建議另開新的 repo。若沿用舊 repo，請先刪除所有舊檔案（含 `data`、`output`），再上傳 v7，並刪除 Secret `ANTHROPIC_API_KEY`。

### 步驟 4：設定密鑰
repo 的 **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Name | Secret |
|---|---|
| `GEMINI_API_KEY` | 步驟 1 的金鑰 |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_USER` | 你的 Gmail 地址 |
| `SMTP_PASS` | 步驟 2 的 16 碼密碼 |
| `MAIL_TO` | 你的信箱（預覽版與正式版都寄這裡） |

### 步驟 5：開啟寫入權限
**Settings** → **Actions** → **General** → 最下方 **Workflow permissions** → **Read and write permissions** → **Save**

### 步驟 6：手動測試（依序）
**Actions** →（有提示先啟用）→ 左側 **全球體育週報** → **Run workflow** → task 輸入指令 → 綠色 **Run workflow**，等綠色 ✓ 再做下一項：

| 順序 | task | 確認重點 | 時間 |
|---|---|---|---|
| 1 | `feeds` | 點進執行紀錄看「執行」步驟：各來源的則數。**中央社列表、Google 新聞、MLB 至少要有資料**；若多個顯示 0 或 ⚠️，把畫面截圖給我 | 約 2 分鐘 |
| 2 | `demo` | 最下方 **Artifacts** 下載，確認 PDF 中文正常、指示檔內容合理 | 約 2 分鐘 |
| 3 | `collect` | repo 的 `data/` 出現新檔案 | 約 5～10 分鐘 |
| 4 | `report` | 收到【預覽】信，附 3 個檔案 | 約 5～10 分鐘 |
| 5 | `hold` | 執行成功即可（測試暫停） | 約 1 分鐘 |
| 6 | `sendnow` | 收到正式版信 | 約 1 分鐘 |

全部成功即完成，之後依排程自動執行。

### 步驟 7：第一次用 Gemini Notebook 做簡報
1. 開啟 **notebooklm.google.com**（Gemini Notebook）→ **新增筆記本**
2. **新增來源** → 上傳信中的 `週報內容_日期.pdf`
3. 右側 **Studio** → **簡報**（Slide deck）→ **自訂**（鉛筆圖示）
4. 打開 `簡報指示_日期.txt`，複製【簡報指示】整段貼上 → **產生**
5. 生成後可下載或分享；想要語音版或一頁圖，同一個檔案裡有 Podcast、資訊圖表指示

> 免費帳號每個筆記本能生成的簡報、影片、資訊圖表次數有限，建議**每週開一個新筆記本**。Gemini Notebook 每份簡報最多 20 頁，指示檔已自動控制在 20 頁內。

---

## 六、寄送方式

### 方式 A：Email 附件（目前使用）
完成步驟 4 即可，不需其他設定。

### 方式 B：自動存進 Google 雲端硬碟（選用，日後想改再設定）
設定後，正式版會**同時**存進你的雲端硬碟（週報內容自動轉成 Google 文件），在 Gemini Notebook「新增來源」選**雲端硬碟**即可，不用下載再上傳。Email 照常寄送。

**B-1 建立 Google Cloud 專案與 OAuth 用戶端（約 15 分鐘，只做一次）**
1. 到 **console.cloud.google.com** → 上方專案選單 → **新增專案**（名稱 `sports-brief`）
2. 左側 **API 和服務** → **程式庫** → 搜尋 **Google Drive API** → **啟用**
3. **API 和服務** → **OAuth 同意畫面**：使用者類型選**外部** → 填應用程式名稱與你的信箱 → 儲存
   - 在「目標對象／測試使用者」加入你自己的 Google 帳號
   - 在「發布狀態」按**發布應用程式**（改為「正式版」）。⚠️ 若維持「測試中」，授權約 7 天就會失效
4. **API 和服務** → **憑證** → **建立憑證** → **OAuth 用戶端 ID** → 應用程式類型選**電腦版應用程式** → 建立
5. 記下 **用戶端 ID** 與 **用戶端密鑰**

**B-2 取得授權（在自己的電腦執行一次）**
1. 電腦需安裝 Python 3（python.org 下載）
2. 在解壓後的資料夾開啟終端機（Windows：在資料夾網址列輸入 `cmd` 按 Enter）
3. 執行 `python tools/drive_auth.py`
4. 依提示貼上用戶端 ID、用戶端密鑰 → 瀏覽器開啟 Google 授權頁 → 選你的帳號 → 同意
   （若出現「Google 尚未驗證這個應用程式」，點**進階** → **前往 sports-brief**，因為這是你自己建立的應用程式）
5. 終端機會顯示三個值

**B-3 存進 GitHub Secrets**

| Name | Secret |
|---|---|
| `GDRIVE_CLIENT_ID` | 用戶端 ID |
| `GDRIVE_CLIENT_SECRET` | 用戶端密鑰 |
| `GDRIVE_REFRESH_TOKEN` | B-2 顯示的 refresh token |
| `GDRIVE_FOLDER_ID` | 選用：指定存放資料夾。打開雲端硬碟資料夾，網址最後一段即為 ID；不填則存在根目錄 |

**B-4 測試**：Actions 執行 `sendnow`，信中出現「已存進 Google 雲端硬碟」與連結即成功。

> 權限範圍只有 `drive.file`：程式只能存取**自己建立的檔案**，看不到你雲端硬碟裡的其他檔案。
> 若雲端硬碟存檔失敗，Email 仍會照常寄出，信中不會出現雲端硬碟連結。
> 要改回只用 Email：刪除 `GDRIVE_REFRESH_TOKEN` 這個 Secret 即可。

---

## 七、每週一怎麼用
1. **約 06:45** 收到【預覽】信 → 看一下「最該關注的 3 件事」與 PDF
2. 沒問題 → 不用做事，**07:30 左右**自動寄正式版
3. 有問題 → 點信中的連結 → **Run workflow** → task 輸入 `hold`
4. 修正後 → 同一頁 task 輸入 `sendnow`（要重新產出內容就先執行 `report`，確認新的預覽再 `sendnow`）
5. 收到正式版 → 依步驟 7 放進 Gemini Notebook 生成簡報

## 八、維護與調整
- **報告目錄**：`output/INDEX.md` 列出每週資料包、新聞則數、Gemini 呼叫次數
- **新聞來源常是 0**：執行 `feeds` 檢查；網站改版或封鎖時，在 `config.py` 修改 `RSS_FEEDS`、`HTML_LISTS`、`GNEWS_QUERIES`
- **調整關鍵字**：`config.py` 的 `GNEWS_QUERIES`（例如增加「中華台北 棒球 12強」）
- **調整簡報對象與風格**：`config.py` 的 `DECK_AUDIENCE`，或直接在 Gemini Notebook 修改指示
- **增減媒體與層級**：`sources.py`
- **Gemini 模型名稱變更**：Google 汰換模型時，修改 `config.py` 的 `MODEL`、`FALLBACK_MODEL`（可在 AI Studio 查目前可用的免費模型）

## 九、常見問題
- **Actions 沒有「全球體育週報」**：`.github` 資料夾沒上傳，回步驟 3
- **錯誤訊息「找不到 GEMINI_API_KEY」**：Secret 名稱拼錯或有空格
- **錯誤訊息含 429 或 RESOURCE_EXHAUSTED**：免費額度暫時用完，程式會自動改用備援模型或降級模式；若常發生，把 `config.py` 的 `MIN_INTERVAL_SEC` 調大（例如 20）
- **沒收到信**：`SMTP_PASS` 要用應用程式密碼、不含空格
- **push 失敗**：步驟 5 未選 Read and write
- **台灣新聞太少**：先執行 `feeds` 看中央社列表與 Google 新聞是否有資料，再調整關鍵字

## 十、注意事項
- 查證能大幅降低錯誤，但無法保證 100%；Gemini Notebook 生成簡報後，建議抽查重要比分與數據（PDF 內有原文網址）
- Gemini Notebook 只根據上傳的資料製作簡報，資料包已包含所需的事實與數字
- GitHub 排程可能延遲 10～15 分鐘
- 附錄「未納入的新聞」是查證不通過的內容，請不要放進簡報
