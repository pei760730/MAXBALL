"""
薪資計算模組（公司鐵律版）

【收入公式】
  本薪        = 本薪月額 ÷ 30 × 月曆天數
  職務津貼    = 職務津貼月額 ÷ 30 × 月曆天數
  其他加給    = 固定加給 + 實際出班天數 × 260（含週六）
  全勤獎金    = 1,600（每次請假扣 300，最多扣至 0）
  假日加班費  = 2,450 × 週六加班天數（或依時薪基準計算）
  前段加班費  = 時薪基準 × 1.33（取整數）× 加班小時
  後段加班費  = 時薪基準 × 1.66（取整數）× 加班小時
  職務加給    = 固定月額（請假依小時或天數比例扣除）

【扣除公式】
  勞保費      = 勞保投保薪資 × 2.5%（員工自付）
  健保費      = 健保投保薪資 × 1.551%（員工自付 = 5.17% × 30%）
  退休金自提  = 退休金投保薪資 × 6%（若選擇自提）
  福利金      = min(應領合計 × 1%, 350)
  便當費      = 訂購份數 × 15 元（僅中午）
"""

from dataclasses import dataclass, field
from meal_tracker import EmployeeMealRecord, MEAL_PRICE_NORMAL, MEAL_PRICE_VEG


# ──────────────────────────────────────────────
# 公司固定費率（鐵律）
# ──────────────────────────────────────────────
OVERTIME_RATE_1 = 1.33          # 前段加班倍率
OVERTIME_RATE_2 = 1.66          # 後段加班倍率

LABOR_INSURANCE_RATE   = 0.0250  # 勞保 員工自付 2.5%（總費率12.5% × 員工負擔20%）
HEALTH_INSURANCE_RATE  = 0.01551 # 健保 員工自付 1.551%（費率5.17% × 員工負擔30%）
PENSION_EMPLOYEE_RATE  = 0.06    # 退休金自提 6%
WELFARE_FUND_RATE      = 0.01    # 福利金 1%
WELFARE_FUND_MAX       = 350     # 福利金最多扣 350 元
DAILY_WORK_ALLOWANCE   = 260     # 出勤加給（每實際出班日，含週六）


# ──────────────────────────────────────────────
# 資料結構
# ──────────────────────────────────────────────
@dataclass
class SalaryConfig:
    """
    員工薪資核定設定（從「員工設定」工作表讀取）
    """
    employee_id: str
    name: str
    base_salary: float              # 本薪月額
    duty_allowance: float           # 職務津貼月額
    other_allowance: float          # 其他加給（固定部分）
    position_allowance: float       # 職務加給（固定月額，請假比例扣除）
    overtime_hourly_base: float     # 時薪基準（= 前段率/1.33 = 後段率/1.66）
    full_attendance_bonus: float    # 全勤獎金月額（通常 1,600）
    labor_insurance_base: float     # 勞保投保薪資
    health_insurance_base: float    # 健保投保薪資
    pension_base: float             # 退休金投保薪資
    pension_self_contribute: bool = False   # 是否自提 6%
    meal_exempt: bool = False               # 不訂便當（不扣便當費）
    health_dependents: int = 0             # 健保眷屬人數（計算健保費用）
    holiday_overtime_daily: float = 0.0    # 假日加班固定日費（0 = 由時薪基準自動計算）
    daily_work_allowance: float = 0.0      # 出勤加給/天（員工個別設定）


@dataclass
class AttendanceRecord:
    """
    員工出勤記錄（從「月出勤」工作表讀取）
    """
    year: int
    month: int
    calendar_days: int              # 當月曆天數（1月31、2月28/29…）
    work_days: int                  # 法定工作日數（平日 Mon-Fri）
    actual_work_days: float         # 實際出班天數（含週六加班日）
    holiday_overtime_days: float = 0.0  # 週六/休息日 加班天數
    sunday_overtime_days: float = 0.0   # 例假日（週日/國定） 加班天數
    overtime_hours_1: float = 0.0   # 平日延時前段加班時數（1.33 倍）
    overtime_hours_2: float = 0.0   # 平日延時後段加班時數（1.66 倍）
    leave_instances: int = 0        # 請假次數（用於扣全勤獎金，每次 -300）
    unpaid_leave_days: float = 0.0  # 無薪假日數
    sick_leave_days: float = 0.0    # 病假日數（半薪）
    personal_leave_days: float = 0.0    # 事假日數（無薪）
    annual_leave_days: float = 0.0  # 特休日數（有薪）
    has_festival_bonus: bool = False    # 當月是否有節金


@dataclass
class SalaryResult:
    """
    薪資計算結果
    """
    name: str
    # 收入
    base_pay: float = 0.0           # 本薪（月曆天比例）
    duty_pay: float = 0.0           # 職務津貼（月曆天比例）
    other_pay: float = 0.0          # 其他加給（固定＋出班天 × 260）
    position_pay: float = 0.0       # 職務加給（固定月額）
    full_attendance_bonus: float = 0.0  # 全勤獎金
    holiday_overtime_pay: float = 0.0   # 假日加班費（週六）
    overtime_pay_1: float = 0.0     # 延時加班費（1.33 倍）
    overtime_pay_2: float = 0.0     # 延時加班費（1.66 倍）
    festival_bonus: float = 0.0     # 節金
    gross_income: float = 0.0       # 應領合計

    # 扣除
    labor_insurance_fee: float = 0.0    # 勞保費
    health_insurance_fee: float = 0.0   # 健保費
    pension_self: float = 0.0           # 退休金自提
    welfare_deduction: float = 0.0      # 福利金
    meal_deduction: float = 0.0         # 便當費
    total_deduction: float = 0.0        # 扣除合計

    # 實領
    net_salary: float = 0.0

    def print_detail(self):
        print(f"\n{'='*50}")
        print(f"  {self.name}  薪資明細")
        print(f"{'='*50}")
        print("【收入項目】")
        print(f"  本薪（月曆天比例）　　: {self.base_pay:>10,.0f} 元")
        print(f"  職務津貼（月曆天比例）: {self.duty_pay:>10,.0f} 元")
        print(f"  其他加給　　　　　　　: {self.other_pay:>10,.0f} 元")
        print(f"  職務加給　　　　　　　: {self.position_pay:>10,.0f} 元")
        print(f"  全勤獎金　　　　　　　: {self.full_attendance_bonus:>10,.0f} 元")
        print(f"  假日加班費（週六）　　: {self.holiday_overtime_pay:>10,.0f} 元")
        print(f"  延時加班費（1.33倍）　: {self.overtime_pay_1:>10,.0f} 元")
        print(f"  延時加班費（1.66倍）　: {self.overtime_pay_2:>10,.0f} 元")
        print(f"  節金　　　　　　　　　: {self.festival_bonus:>10,.0f} 元")
        print(f"  {'─'*38}")
        print(f"  應領合計　　　　　　　: {self.gross_income:>10,.0f} 元")
        print("【扣除項目】")
        print(f"  勞保費（員工自付2.5%）: {self.labor_insurance_fee:>10,.0f} 元")
        print(f"  健保費（員工自付）　　: {self.health_insurance_fee:>10,.0f} 元")
        print(f"  退休金自提（6%）　　　: {self.pension_self:>10,.0f} 元")
        print(f"  福利金（1%,最多350）　: {self.welfare_deduction:>10,.0f} 元")
        print(f"  便當費　　　　　　　　: {self.meal_deduction:>10,.0f} 元")
        print(f"  {'─'*38}")
        print(f"  扣除合計　　　　　　　: {self.total_deduction:>10,.0f} 元")
        print(f"{'='*50}")
        print(f"  實領薪資　　　　　　　: {self.net_salary:>10,.0f} 元")
        print(f"{'='*50}\n")


# ──────────────────────────────────────────────
# 核心計算函數
# ──────────────────────────────────────────────
def calculate_salary(
    config: SalaryConfig,
    attendance: AttendanceRecord,
    meal_record: EmployeeMealRecord | None = None,
) -> SalaryResult:
    """
    計算員工當月薪資（依公司鐵律）。
    """
    result = SalaryResult(name=config.name)

    # ── 1. 本薪 & 職務津貼 ÷ 30 × 月曆天數 ──
    result.base_pay = round(config.base_salary / 30 * attendance.calendar_days)
    result.duty_pay = round(config.duty_allowance / 30 * attendance.calendar_days)

    # ── 2. 其他加給 = 固定 + (平日出班 + 週六加班) × 260 ──
    total_work_days = attendance.actual_work_days + attendance.holiday_overtime_days
    result.other_pay = round(
        config.other_allowance + total_work_days * config.daily_work_allowance
    )

    # ── 3. 職務加給（固定月額，請假比例扣除由人事手動處理）──
    result.position_pay = round(config.position_allowance)

    # ── 4. 全勤獎金（每次請假扣 300，最多扣至 0）──
    deduct = attendance.leave_instances * 300
    result.full_attendance_bonus = max(0, config.full_attendance_bonus - deduct)

    # ── 5. 假日加班費（週六/休息日）──
    #   若有設定固定日費直接用，否則由時薪基準計算
    #   標準8小時: 2hr×1.33 + 6hr×1.66 = 12.62 倍
    if config.holiday_overtime_daily > 0:
        holiday_daily = config.holiday_overtime_daily
    else:
        holiday_daily = round(config.overtime_hourly_base * 12.62 / 50) * 50  # 取整至50元
    result.holiday_overtime_pay = round(holiday_daily * attendance.holiday_overtime_days)

    # ── 6. 延時加班費（取整數時薪後計算）──
    front_rate = round(config.overtime_hourly_base * OVERTIME_RATE_1)  # 例: 194×1.33=258
    back_rate  = round(config.overtime_hourly_base * OVERTIME_RATE_2)  # 例: 194×1.66=322
    result.overtime_pay_1 = round(front_rate * attendance.overtime_hours_1)
    result.overtime_pay_2 = round(back_rate  * attendance.overtime_hours_2)

    # ── 7. 節金（春節/端午/中秋，以職務津貼為標準）──
    result.festival_bonus = (
        config.duty_allowance if attendance.has_festival_bonus else 0.0
    )

    # ── 應領合計 ──
    result.gross_income = (
        result.base_pay
        + result.duty_pay
        + result.other_pay
        + result.position_pay
        + result.full_attendance_bonus
        + result.holiday_overtime_pay
        + result.overtime_pay_1
        + result.overtime_pay_2
        + result.festival_bonus
    )

    # ── 8. 勞保費（員工自付 2.5%）──
    result.labor_insurance_fee = round(
        config.labor_insurance_base * LABOR_INSURANCE_RATE
    )

    # ── 9. 健保費（員工自付 = 投保薪資 × 5.17% × (1+眷屬) × 30%）──
    result.health_insurance_fee = round(
        config.health_insurance_base * 0.0517 * (1 + config.health_dependents) * 0.30
    )

    # ── 10. 退休金自提 6%（公式：IF(出勤天 = 應出勤天, 1, 出勤天/30) × 投保薪 × 6%）──
    #   actual_work_days = 平日出勤天（Mon-Fri），work_days = 當月法定工作日
    #   全勤 → 比例 = 1；有缺勤 → 比例 = actual_work_days / 30
    pension_ratio = (
        1.0 if attendance.actual_work_days >= attendance.work_days
        else attendance.actual_work_days / 30
    )
    result.pension_self = (
        round(config.pension_base * PENSION_EMPLOYEE_RATE * pension_ratio)
        if config.pension_self_contribute else 0.0
    )

    # ── 11. 福利金（應領合計 × 1%，最多 350 元）──
    result.welfare_deduction = min(
        WELFARE_FUND_MAX,
        round(result.gross_income * WELFARE_FUND_RATE)
    )

    # ── 12. 便當費（meal_exempt=True 者永遠不扣）──
    if meal_record and not config.meal_exempt:
        result.meal_deduction = meal_record.total_cost

    # ── 扣除合計 ──
    result.total_deduction = (
        result.labor_insurance_fee
        + result.health_insurance_fee
        + result.pension_self
        + result.welfare_deduction
        + result.meal_deduction
    )

    # ── 實領薪資 ──
    result.net_salary = result.gross_income - result.total_deduction

    return result


def batch_calculate(
    configs: list[SalaryConfig],
    attendances: dict[str, AttendanceRecord],
    meal_summary: dict | None = None,
) -> list[SalaryResult]:
    """批次計算所有員工薪資。"""
    results = []
    meal_records = {}
    if meal_summary:
        for r in meal_summary.get("records", []):
            meal_records[r.name] = r

    for config in configs:
        attendance = attendances.get(config.name)
        if not attendance:
            print(f"[警告] 找不到 {config.name} 的出勤記錄，跳過")
            continue
        meal_record = meal_records.get(config.name)
        result = calculate_salary(config, attendance, meal_record)
        results.append(result)

    return results


# ──────────────────────────────────────────────
# 示範：鄧志展 2026年3月
# ──────────────────────────────────────────────
def demo():
    """
    鄧志展 2026年3月薪資（對照手寫計算表）
    本薪16350/30×31=16895  職務津貼7950/30×31=8215
    其他加給2850+26×260=9610  職務加給17850
    前段50hr×258=12900  後段60hr×322=19320
    假日4天×2450=9800  全勤1600
    合計應達 96,190
    """
    from meal_tracker import EmployeeMealRecord

    config = SalaryConfig(
        employee_id="30",
        name="鄧志展",
        base_salary=16_350,
        duty_allowance=7_950,
        other_allowance=2_850,          # 其他加給固定部分
        position_allowance=17_850,      # 職務加給（月額）
        overtime_hourly_base=194,       # 時薪基準（194×1.33=258, 194×1.66=322）
        holiday_overtime_daily=2_450,   # 週六加班日費（鐵律）
        daily_work_allowance=260,       # 出勤加給260元/天
        meal_exempt=True,               # 鄧志展不訂便當，永遠不扣便當費
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=60_800,
        pension_base=60_800,
        pension_self_contribute=True,
    )

    attendance = AttendanceRecord(
        year=2026,
        month=3,
        calendar_days=31,
        work_days=22,                   # 3月 Mon-Fri 法定22天
        actual_work_days=22.0,          # 平日實際出班22天（全勤 → 退休金比例=1）
        holiday_overtime_days=4.0,      # 週六加班4天（其他加給 = 22+4=26天 × 260）
        overtime_hours_1=50.0,          # 前段 1.33倍（早班+晚班合計）
        overtime_hours_2=60.0,          # 後段 1.66倍
        leave_instances=0,              # 無請假
    )

    result = calculate_salary(config, attendance)  # 不傳 meal_record，鄧志展不訂便當
    result.print_detail()

    # 驗證對照手寫
    expected_gross = 96_190
    print(f"  對照手寫合計: {expected_gross:,} 元")
    diff = result.gross_income - expected_gross
    if diff == 0:
        print("  ✓ 應領合計完全吻合！")
    else:
        print(f"  差異: {diff:+,.0f} 元")

    return result


def demo_xu_bo_kai():
    """許柏凱 2026年3月薪資（22平日全勤，無加班，22份便當）"""
    from meal_tracker import EmployeeMealRecord

    config = SalaryConfig(
        employee_id="13",
        name="許柏凱",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=4_800,          # 其他加給固定部分
        position_allowance=9_500,       # 職務加給
        overtime_hourly_base=136,       # 136×1.33=181, 136×1.66=226
        holiday_overtime_daily=1_719,   # 假日加班日費（2hr×181+6hr×226=1,718≈1,719）
        daily_work_allowance=175,       # 出勤加給175元/天（60+30+40+45）
        full_attendance_bonus=1_600,
        labor_insurance_base=30_300,
        health_insurance_base=30_300,
        health_dependents=2,            # 2眷屬 → 健保×3人
        pension_base=30_300,
        pension_self_contribute=False,
    )

    attendance = AttendanceRecord(
        year=2026,
        month=3,
        calendar_days=31,
        work_days=22,
        actual_work_days=22.0,          # 22平日全勤
        holiday_overtime_days=0.0,      # 無週六加班
        overtime_hours_1=0.0,
        overtime_hours_2=0.0,
        leave_instances=0,
    )

    meal = EmployeeMealRecord(name="許柏凱", normal_count=22)
    result = calculate_salary(config, attendance, meal)
    result.print_detail()
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("鄧志展")
    demo()
    print("=" * 50)
    print("許柏凱")
    demo_xu_bo_kai()
