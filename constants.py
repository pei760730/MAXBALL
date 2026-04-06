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
FULL_ATTENDANCE_DEFAULT = 1_600  # 標準全勤獎金
FULL_ATTENDANCE_DEDUCT  = 300    # 每次請假扣 300

# ── 便當 ──
MEAL_PRICE = 15                  # 員工自付（普通/素食皆同）

# ── 工時 ──
HOURS_PER_DAY   = 8              # 正常工時
DAYS_PER_MONTH  = 30             # 月薪制除數
OVERTIME_DIVISOR = DAYS_PER_MONTH * HOURS_PER_DAY  # = 240

# ── 上班時間（分鐘）──
WORK_START_MINUTES    = 8 * 60       # 08:00
EVENING_OT_START_MIN  = 17 * 60 + 30 # 17:30（晚班加班起算）

# ── 假日加班分段 ──
HOLIDAY_OT_SEGMENTS = [
    (2.0,  OVERTIME_RATE_FRONT),  # 1-2小時：1.33倍
    (6.0,  OVERTIME_RATE_BACK),   # 3-8小時：1.66倍
    (2.0,  OVERTIME_RATE_FRONT),  # 9-10小時：1.33倍
    (9999, OVERTIME_RATE_BACK),   # 11小時起：1.66倍
]
