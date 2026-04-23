# MAXBALL — 薪資計算系統

Google Sheets 為輸入/輸出介面，Python 純函數引擎為核心，
規則不變式 (`rules.py`) 維持語義契約，回歸案例 (`verified_cases.py`) 守金額正確性。

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

# 跑回歸測試（17 案例 + 11 條規則不變式）
python verified_cases.py

# 實際結算某月（讀 Sheets → 算薪資 → 寫回）
python main_sync.py --year 2026 --month 3

# 只試算不寫回
python main_sync.py --year 2026 --month 3 --dry-run
```

---

## 專案結構

```
MAXBALL/
├── constants.py           # 公司鐵律常數（費率、倍率、上限）
├── salary_calculator.py   # 純函數計算引擎 f(Config, Attendance) → Result
├── rules.py               # 可執行規則不變式（sediment layer）
├── employee_configs.py    # 員工 SalaryConfig（hard-coded）
├── verified_cases.py      # 回歸案例 + 跑 rules 不變式
├── main_sync.py           # Google Sheets ↔ 引擎同步（含 header 驗證）
├── sheets_schema.py       # 建立 Sheet 分頁結構
├── sheets_client.py       # gspread 薄封裝
├── _archive/              # 舊 seed/debug 腳本（不再於 CI 呼叫）
└── .github/workflows/     # sync_sheets / read_sheets（workflow_dispatch）
```

## 規則沉澱架構

- **公式常數**：只在 `constants.py` 出現一次。
- **引擎**：`salary_calculator.calculate_salary` 純函數，`_r()` 使用 `ROUND_HALF_UP`。
- **健保費 swap 點**：`salary_calculator.health_insurance_fee(config)`；未來接健保局查表，只改這一個函數。
- **規則不變式**：`rules.RULES` 每條 = predicate + 首次驗證它的 case 名單；跑 `verified_cases.py` 會一併檢查。
- **CI**：`.github/workflows/sync_sheets.yml` 接受 `year` / `month` / `dry_run` inputs，跑回歸後才寫回。

## 安全提醒

- `service_account.json` 已被加入 `.gitignore`，**絕對不要**將金鑰檔案上傳到 GitHub
- 如果不小心上傳了，請立即到 Google Cloud Console 撤銷該金鑰
