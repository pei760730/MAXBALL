# MAXBALL — 薪資計算系統

19 位員工的月薪資計算與 Google Sheets 整合。
**員工設定由 Python 維護**（版本控管、單一權威源），**出勤 / 便當 / 結算** 走 Google Sheets。
核心是純函數引擎 + 17 條可執行規則不變式（**I/M/C 三分**）+ coverage matrix（含 mutation-based 欄位守衛），
所有改動由 17 個真實薪資截圖回歸測試守門，CI 上以 `regression.yml` 強制執行。

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

- **引擎** (`salary_calculator.calculate_salary`)：純函數，`_r()` 以 `ROUND_HALF_UP` 替代 Python 銀行家捨入；健保查表（單一 swap 點）
- **規則不變式** (`rules.py`)：17 條，三分為 **independent**（不重抄公式的獨立斷言）/ **mirror**（與引擎共用 helper 的鏡像，擋 helper drift 不擋演算法錯誤）/ **composition**（合計關係兜底）。每條 = applies + check
- **回歸案例** (`verified_cases.py`)：17 個真實薪資截圖 + coverage matrix。Matrix 印兩個視角：(a) 規則觸發次數 + I/M/C 標籤；(b) **mutation-based 欄位守衛** —— 每個 result 欄位 +1 跑全部規則，列出抓得到的非 composition 規則；只剩 `sums_consistent` 兜底者即真實覆蓋缺口
- **邊界層** (`boundary.py`)：header 漂移 → `raise ValueError`；姓名 typo / 值域異常 → 訊息列；便當訂購未知標記 → raise；`selftest()` 由 regression suite 在最開頭呼叫

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

# 回歸測試（單一守門進入點：boundary self-test + 17 案例 + 17 條規則 + coverage matrix）
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
├── rules.py               # 17 條規則（independent×3 + mirror×13 + composition×1），每條含 applies/check
├── employee_configs.py    # 員工 SalaryConfig（Python 單一權威源）
├── verified_cases.py      # 17 個回歸案例 + coverage matrix（含 mutation-based 欄位守衛）；單一守門進入點
├── boundary.py            # 邊界驗證（header / 姓名 / 值域 / 便當字元），selftest() 由 regression suite 呼叫
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
| 規則 kind 三分（鏡像不是不變式） | `rules.py`：independent（不重抄公式）/ mirror（與引擎共用 helper，只擋 drift）/ composition（合計兜底）。Mirror 規則自報身分，避免「規則數 0 破損」信號通脹 |
| Traceability 用 derive，不用宣告 | 移除 `verified_by` 名單與 `FIELD_FORMULA_RULES` 字典；coverage matrix runtime 同時印「規則→case」與「欄位→守衛規則」兩個視角 |
| 欄位守衛由 mutation 決定 | 每個 result 欄位 +1 跑全部規則；只剩 `sums_consistent` 兜底者即真實覆蓋缺口 |
| 單一守門進入點 | boundary self-test + tolerance 歸因 + cases + rules + coverage matrix 全走 `python verified_cases.py`，CI gate 只認這一個 exit code |
| Tolerance 必須歸因 | 任何 `tolerance > 0` 必對得回 `TOLERANCE_REASONS` 的 swap 點；接表後自動失敗提醒收掉 |
| 捨入策略明確 | `_r()` 使用 `ROUND_HALF_UP`（台灣會計慣例），非 Python 內建銀行家 |
| 健保查表單點 | `salary_calculator.health_insurance_fee(config)` 以健保局分擔表查表 |
| 邊界 fail loud | Sheet header 漂移 / 便當未知標記 → raise；姓名 typo / 值域異常 → 中止 |
| 封閉迴路 = 強制迴路 | `regression.yml` 在 push/PR 自動跑回歸；README 上的不變式承諾對得回 CI exit code |

---

## 驗證狀態

**17/17 通過（全部 exact）**（2026 年 3 月）
- 17 筆 exact（diff=0）

**17 條規則 0 破損**（依 kind）
- **independent（3）**：`annual_leave_no_deduct` / `pension_off` / `meal_exempt` — 真不變式，演算法錯誤時會獨立發聲
- **mirror（13）**：`pension_annual_leave_full` / `pension_partial_ratio` / `position_proration` / `welfare_cap_and_exempt` / `base_duty_formula` / `overtime_base_240` / `holiday_ot_rounding` / `daily_work_allowance` / `health_insurance_formula` / `labor_insurance_formula` / `night_shift_compose` / `meal_allowance_compose` / `festival_compose` — 只擋 helper drift，不擋演算法錯誤；金額守門靠 case target
- **composition（1）**：`sums_consistent` — 合計兜底；mutation testing 顯示 `festival_bonus` / `gross_income` / `total_deduction` / `net_salary` 僅由它守衛

**結構化訊號全由 `python verified_cases.py` 自動印**（不再寫進 README/ISSUES）：
- 零觸發規則 + 樣本 case 名單
- 欄位守衛清單（mutation +1 → 哪些 non-composition 規則攔得住）
- 「僅 composition 兜底」的真實覆蓋缺口

未驗證個案：陳麥斯 #8、簡宜君 #17（見 `ISSUES.md`）

---

## 安全提醒

- `service_account.json` 已在 `.gitignore`，**絕對不要** commit 上 GitHub
- 若不慎上傳，立即到 Google Cloud Console 撤銷該金鑰並重新產生
