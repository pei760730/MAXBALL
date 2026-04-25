"""
公司鐵律常數（唯一定義處）
============================
所有模組的費率、倍率、固定值都從這裡 import。
不在其他地方重複定義。
"""

# ── 加班倍率 ──
OVERTIME_RATE_FRONT = 1.33      # 前段加班（平日前2小時 / 假日前2小時）
OVERTIME_RATE_BACK  = 1.66      # 後段加班（平日第3小時起 / 假日3-8小時）

# ── 保險費率（員工自付部分）──
LABOR_INSURANCE_RATE  = 0.0250   # 勞保 2.5%（總12.5% × 員工20%）
HEALTH_INSURANCE_RATE = 0.0517   # 健保費率 5.17%
HEALTH_EMPLOYEE_SHARE = 0.30     # 健保員工負擔 30%
PENSION_SELF_RATE     = 0.06     # 退休金自提 6%

# ── 福利金 ──
WELFARE_RATE = 0.01              # 應領 × 1%
WELFARE_CAP  = 350               # 最多扣 350 元

# ── 全勤獎金 ──
FULL_ATTENDANCE_DEDUCT  = 300    # 每次請假扣 300

# ── 便當 ──
MEAL_PRICE = 15                  # 員工自付（普通/素食皆同）

# ── 工時 ──
HOURS_PER_DAY    = 8                              # 正常工時
DAYS_PER_MONTH   = 30                             # 月薪制除數
OVERTIME_DIVISOR = DAYS_PER_MONTH * HOURS_PER_DAY # = 240

# ── 假日加班 8 小時拆段（前 2hr × 1.33 + 後 6hr × 1.66）──
HOLIDAY_OT_FRONT_HOURS = 2
HOLIDAY_OT_BACK_HOURS  = 6
