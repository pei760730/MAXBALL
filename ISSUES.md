# 薪資計算系統 — 待處理事項（narrative）

> 結構化訊號（規則觸發次數、tolerance 歸因、無公式守護的欄位）由
> `python verified_cases.py` 的 coverage matrix 自動印出，**不再寫進這份文件**。
> 這裡只放需要人類 narrative 的個案與決策紀錄。

## 驗證狀態
17/17 通過（2026 年 3 月）；17 條規則 0 破損。
- 16 筆 exact 對齊
- 1 筆 tolerance=1：**陳佩欣 #16**，已歸因到 `health_insurance_table_lookup`
  - swap 點：`salary_calculator.health_insurance_fee`
  - 接表後在 `verified_cases.TOLERANCE_REASONS` 移除該鍵 → 自動 fail，提醒收掉 tolerance

## 未驗證個案（缺資料，無法做成 case）
- **陳麥斯 #8**：缺完整薪資截圖；保險投保基數待確認。
- **簡宜君 #17**：複雜（含事假、月薪 28 天、借支 10,000）；事假扣薪規則未沉澱。

## 候選規則（等實際 case 觸發後再升級）
- 事假/病假扣薪：每次扣多少？從哪個項目扣？病假是否半薪？
  - 觸發時機：簡宜君 #17 截圖補齊。
- 截圖中的「特殊扣除」目前不在引擎內：
  - 許連灯：勞退健保自付 1,841（截圖實領 30,205 vs 標準 32,046）
  - 吳慧娟：勞退健保自付 588（截圖實領 31,975 vs 標準 32,563）
  - 莊志成：代扣互展 10,000（截圖實領 53,377 vs 標準 63,377）
  - 簡宜君：借支 10,000
  - 待決定：要進引擎成為新欄位，還是視為「會計帳上事項，不在薪資計算內」。

## 規則層零觸發（由 coverage matrix 提示）
規則已寫好對應引擎分支，但目前 17 個 case 都不觸發。**不刪**，等對應 case 出現自動接管：
- `festival_compose`：留給有節金月份。
- `pension_partial_ratio`：簡宜君 #17 補資料後（有事假且 pension 自提者）會觸發。
- `position_proration`：簡宜君 #17 補資料後（有事/病/無薪假者）會觸發。
