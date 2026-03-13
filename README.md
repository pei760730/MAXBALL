# MAXBALL - Google Sheets 整合工具

使用 Python 讀寫 Google Sheets 的工具專案。

---

## 快速開始

### 第一步：建立 Google Cloud 專案 & 取得金鑰

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點擊上方 **「選取專案」** → **「新增專案」**，輸入專案名稱後建立
3. 在左側選單找到 **「API 和服務」** → **「資料庫」**
4. 搜尋並啟用以下兩個 API：
   - **Google Sheets API**
   - **Google Drive API**
5. 到 **「API 和服務」** → **「憑證」**
6. 點 **「建立憑證」** → **「服務帳戶」**
7. 填入服務帳戶名稱，完成建立
8. 點進剛建立的服務帳戶 → **「金鑰」** 分頁 → **「新增金鑰」** → **「JSON」**
9. 下載的 JSON 檔案重新命名為 `service_account.json`，放到本專案根目錄

### 第二步：分享 Google Sheet 給服務帳戶

1. 開啟 `service_account.json`，找到 `client_email` 欄位（例如：`xxxx@xxxx.iam.gserviceaccount.com`）
2. 開啟你的 Google Sheet
3. 點右上角 **「共用」**
4. 將 `client_email` 的地址貼上，權限設為 **「編輯者」**
5. 點 **「傳送」**

### 第三步：安裝套件 & 執行

```bash
# 安裝 Python 套件
pip install -r requirements.txt

# 修改 example.py 中的 Sheet 名稱或 URL
# 然後執行
python example.py
```

---

## 專案結構

```
MAXBALL/
├── sheets_client.py    # Google Sheets 連線與讀寫模組
├── example.py          # 使用範例
├── requirements.txt    # Python 套件清單
├── .gitignore          # Git 忽略清單（會排除金鑰檔案）
└── README.md           # 本文件
```

## 主要功能

| 函式 | 說明 |
|------|------|
| `connect()` | 使用 Service Account 連線 |
| `open_sheet()` | 用名稱開啟 Google Sheet |
| `open_sheet_by_url()` | 用 URL 開啟 Google Sheet |
| `read_all()` | 讀取所有資料（二維 list） |
| `read_as_dicts()` | 讀取資料為 dict list |
| `write_row()` | 寫入一列 |
| `write_rows()` | 批次寫入多列 |
| `update_cell()` | 更新單一儲存格 |
| `clear_worksheet()` | 清空工作表 |

## 安全提醒

- `service_account.json` 已被加入 `.gitignore`，**絕對不要**將金鑰檔案上傳到 GitHub
- 如果不小心上傳了，請立即到 Google Cloud Console 撤銷該金鑰
