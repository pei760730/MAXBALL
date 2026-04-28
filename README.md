# MAXBALL — 薪資計算系統

19 位員工的月薪資計算與 Google Sheets 整合。
**員工設定由 Python 維護**（版本控管、單一權威源），**出勤 / 便當 / 結算** 走 Google Sheets。
核心是純函數引擎 + 17 條可執行規則不變式 + coverage matrix，所有改動由 17 個真實薪資截圖回歸測試守門（且已由 CI 強制）。

---

## 架構總覽

```
employee_configs.py  ──►  salary_calculator ──► SalaryResult
 (Python, 19 人)           f(config, attendance)         │
                                  ▲                     │
 月出勤  ─── load_attendance ─────┤                     │
 便當訂購 ── load_meal_counts ────┘                     │
                                                        │
                                 薪資結算 ◄─────────────┘
                                 (Google Sheets)
```

- **引擎** (`salary_calculator.calculate_salary`)：純函數，`_r()` 以 `ROUND_HALF_UP` 替代 Python 銀行家捨入
- **規則不變式** (`rules.py`)：17 條，分 SEMANTIC（語義獨立斷言）+ STRUCTURAL（組成契約），每條 = applies + check + 驗證案例名單
- **回歸案例** (`verified_cases.py`)：17 個真實薪資截圖 + coverage matrix（規則觸發次數 / 零觸發提示 / 無公式守護的欄位）
- **邊界層** (`boundary.py`)：header 漂移 → `raise ValueError`；姓名 typo / 值域異常 → 訊息列；獨立可測，不依賴 Google Sheets

---

## 快速開始

### 第一步：建立 Google Cloud 專案 & 取得金鑰

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. **「選取專案」** → **「新增專案」**
3. **「API 和服務」** → **「資料庫」**，啟用 **Google Sheets API** 與 **Google Drive API**
4. **「API 和服務」** → **「憑證」** → **「建立憑證」** → **「服務帳戶」**
5. 進入服務帳戶 → **「金鑰」** → **「新增金鑰」** → **「JSON」**
6. 下載的 JSON 重新命名為 `service_account.json` 放專案根目錄

### 第二步：分享 Google Sheet 給服務帳戶

1. `service_account.json` 裡的 `client_email` 欄位（`xxxx@xxxx.iam.gserviceaccount.com`）
2. Google Sheet →「共用」→ 貼上該 email，權限 **編輯者**

### 第三步：安裝套件 & 執行

```bash
pip install -r requirements.txt

# 回歸測試（17 案例 + 17 條規則不變式）—— 先跑這個
python verified_cases.py

# 實際結算某月（讀 Sheets → 算薪資 → 寫回 Sheets）
python main_sync.py --year 2026 --month 3

# 只試算不寫回
python main_sync.py --year 2026 --month 3 --dry-run
```

CI 會在 push 到 `main` 與所有 PR 自動執行 `.github/workflows/regression.yml`：

```bash
python verified_cases.py
```

exit code 即守門判準；這使 README 內「回歸測試守門」成為可驗證事實。  
`.github/workflows/sync_sheets.yml` 仍保留 workflow_dispatch 供月結算手動執行。

---

## 專案結構

```
MAXBALL/
├── constants.py           # 費率 / 倍率 / 上限（唯一定義處，封版）
├── salary_calculator.py   # 純函數引擎 + _r() + health_insurance_fee（健保查表）
├── rules.py               # 17 條規則（SEMANTIC × 7 + STRUCTURAL × 10），每條含 applies/check
├── employee_configs.py    # 員工 SalaryConfig（Python 單一權威源）
├── verified_cases.py      # 17 個回歸案例（Case 結構 + tolerance_reason）+ coverage matrix
├── boundary.py            # 邊界驗證（header / 姓名 / 值域），自帶 self-test
├── main_sync.py           # 月出勤/便當 讀取 → 計算 → 寫回薪資結算
├── sheets_schema.py       # Sheet 分頁 bootstrap（一次性，不含員工設定）
├── sheets_client.py       # gspread 薄封裝
├── ISSUES.md              # narrative：未驗證個案 + 候選規則（結構化訊號改由 coverage matrix 印）
└── .github/workflows/
    ├── regression.yml     # 回歸守門（push main + 所有 PR，跑 verified_cases.py）
    ├── sync_sheets.yml    # 月結算（workflow_dispatch + year/month/dry_run）
    └── read_sheets.yml    # 拉 Sheets snapshot（workflow_dispatch）
```

---

## 設計原則（Opus 4.7 redesign 沉澱）

| 原則 | 實作點 |
|---|---|
| 單一權威源 | Employee configs 只在 `employee_configs.py`；Sheet 不再有「員工設定」tab |
| 鐵律常數只寫一次 | 所有費率在 `constants.py`，其他模組 import |
| 規則沉澱可執行，且區分種類 | `rules.py` 分 SEMANTIC（獨立斷言）/ STRUCTURAL（組成契約）；每條 = applies + check + verified_by |
| 規則層自我健身 | `coverage matrix` 每次回歸印觸發次數；零觸發即死規則或漏 case |
| Tolerance 必須歸因 | 任何 `tolerance > 0` 必對得回 `TOLERANCE_REASONS` 的 swap 點；接表後自動失敗提醒收掉 |
| 捨入策略明確 | `_r()` 使用 `ROUND_HALF_UP`（台灣會計慣例），非 Python 內建銀行家 |
| 健保查表單點 | `salary_calculator.health_insurance_fee(config)` 以健保局分擔表查表 |
| Boundary 獨立可測 | `boundary.py` 自帶 self-test，不依賴 Google Sheets |
| 邊界 fail loud | Sheet header 漂移 / 便當未知標記 → raise；姓名 typo / 值域異常 → 中止 |
| CI 回歸守門 | `regression.yml` 強制 `python verified_cases.py`，exit code 為唯一判準 |

---

## 驗證狀態

**17/17 通過（全部 exact）**（2026 年 3 月）
- 17 筆 exact（diff=0）

**17 條規則 0 破損**
- SEMANTIC（7）：`annual_leave_no_deduct` / `pension_off` / `pension_annual_leave_full` / `pension_partial_ratio` / `position_proration` / `meal_exempt` / `welfare_cap_and_exempt`
- STRUCTURAL（10）：`base_duty_formula` / `overtime_base_240` / `holiday_ot_rounding` / `daily_work_allowance` / `health_insurance_formula` / `labor_insurance_formula` / `night_shift_compose` / `meal_allowance_compose` / `festival_compose` / `sums_consistent`

**Coverage matrix 提示**（`python verified_cases.py` 自動印）：
零觸發規則：`pension_partial_ratio` / `position_proration` / `festival_compose` — 對應引擎分支但無 case 證明；前兩條等簡宜君 #17 截圖補齊即可觸發，festival 等有節金月份。

未驗證個案：陳麥斯 #8、簡宜君 #17（見 `ISSUES.md`）

---

## 安全提醒

- `service_account.json` 已在 `.gitignore`，**絕對不要** commit 上 GitHub
- 若不慎上傳，立即到 Google Cloud Console 撤銷該金鑰並重新產生
