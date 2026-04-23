# MAXBALL — 薪資計算系統

19 位員工的月薪資計算與 Google Sheets 整合。
**員工設定由 Python 維護**（版本控管、單一權威源），**出勤 / 便當 / 結算** 走 Google Sheets。
核心是純函數引擎 + 11 條可執行規則不變式，所有改動由 17 個真實薪資截圖回歸測試守門。

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
- **規則不變式** (`rules.py`)：11 條，每條 = predicate + 首次驗證案例名單；engine 若偏離語義，CI 擋
- **回歸案例** (`verified_cases.py`)：17 個真實薪資截圖驗證；同時跑不變式雙層守門
- **boundary 驗證**：Sheet header 漂移 → `raise ValueError`；出勤姓名打錯 / 值域異常 → 中止計算

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

# 回歸測試（17 案例 + 11 條規則不變式）—— 先跑這個
python verified_cases.py

# 實際結算某月（讀 Sheets → 算薪資 → 寫回 Sheets）
python main_sync.py --year 2026 --month 3

# 只試算不寫回
python main_sync.py --year 2026 --month 3 --dry-run
```

CI 上用 `.github/workflows/sync_sheets.yml` 的 workflow_dispatch 觸發，手動輸入 `year` / `month` / `dry_run`；先跑回歸再寫回。

---

## 專案結構

```
MAXBALL/
├── constants.py           # 費率 / 倍率 / 上限（唯一定義處，封版）
├── salary_calculator.py   # 純函數引擎 + _r() + health_insurance_fee helper
├── rules.py               # 11 條可執行規則不變式
├── employee_configs.py    # 員工 SalaryConfig（Python 單一權威源）
├── verified_cases.py      # 17 個回歸案例 + 執行 rules 不變式
├── main_sync.py           # 月出勤/便當 讀取 → 計算 → 寫回薪資結算
│                          #   含 header 驗證 + validate_attendance
├── sheets_schema.py       # Sheet 分頁 bootstrap（一次性）
├── sheets_client.py       # gspread 薄封裝
├── ISSUES.md              # 未驗證個案 + 候選規則（待觸發才升級）
├── _archive/              # 舊 seed/debug 腳本（不在 CI）
└── .github/workflows/
    ├── sync_sheets.yml    # 月結算（workflow_dispatch + year/month/dry_run）
    └── read_sheets.yml    # 拉 Sheets snapshot（workflow_dispatch）
```

---

## 設計原則（Opus 4.7 redesign 沉澱）

| 原則 | 實作點 |
|---|---|
| 單一權威源 | Employee configs 只在 `employee_configs.py`；Sheet 不再有「員工設定」tab |
| 鐵律常數只寫一次 | 所有費率在 `constants.py`，其他模組 import |
| 規則沉澱可執行 | `rules.py` 11 條 predicate，engine 變更會被雙層檢查（案例金額 + 語義契約） |
| 捨入策略明確 | `_r()` 使用 `ROUND_HALF_UP`（台灣會計慣例），非 Python 內建銀行家 |
| 健保查表 swap 點 | `salary_calculator.health_insurance_fee(config)`；未來接健保局表只改此函數 |
| Boundary 驗證 | Sheet header 漂移 → raise；姓名 typo / 值域異常 → 中止，不 silently 賠錢 |
| CI 契約收斂 | `workflow_dispatch` + year/month/dry_run，不再 poke-file 觸發 |

---

## 驗證狀態

**17/17 通過**（2026 年 3 月）
- 16 筆 exact
- 1 筆 tolerance=1：陳佩欣 #31（健保公式 vs 健保局查表真實差異，非捨入；swap 點已備好待查表接入）

**11 條規則不變式 0 破損**：
`base_duty_formula` / `annual_leave_no_deduct` / `pension_annual_leave_full` / `pension_off` /
`overtime_base_240` / `meal_exempt` / `daily_work_allowance` / `holiday_ot_rounding` /
`health_insurance_formula` / `welfare_cap_and_exempt` / `sums_consistent`

未驗證個案：陳麥斯 #8、簡宜君 #17（見 `ISSUES.md`，需實際薪資截圖）

---

## 安全提醒

- `service_account.json` 已在 `.gitignore`，**絕對不要** commit 上 GitHub
- 若不慎上傳，立即到 Google Cloud Console 撤銷該金鑰並重新產生
