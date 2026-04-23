"""
薪資計算引擎（純函數）
=====================
f(SalaryConfig, AttendanceRecord) → SalaryResult

所有常數從 constants.py import，本模組不定義任何費率。
不依賴 Google Sheets、不依賴便當模組、不含 demo。
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from constants import (
    OVERTIME_RATE_FRONT, OVERTIME_RATE_BACK, OVERTIME_DIVISOR,
    LABOR_INSURANCE_RATE, HEALTH_INSURANCE_RATE, HEALTH_EMPLOYEE_SHARE,
    PENSION_SELF_RATE, WELFARE_RATE, WELFARE_CAP,
    FULL_ATTENDANCE_DEDUCT, MEAL_PRICE,
)


def _r(x: float) -> int:
    # 台灣會計四捨五入 (ROUND_HALF_UP)，避免 Python 內建 round() 的銀行家捨入。
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def health_insurance_fee(config: "SalaryConfig") -> int:
    """
    員工自付健保費（公式法）= 投保薪資 × 5.17% × (1+眷屬) × 30%。

    未來若要接健保局「保險費分擔表」查表，只需替換本函數實作；
    rules.py::health_insurance_formula 會跟著走，不會漂移。
    """
    return _r(
        config.health_insurance_base * HEALTH_INSURANCE_RATE
        * (1 + config.health_dependents) * HEALTH_EMPLOYEE_SHARE
    )


# ──────────────────────────────────────────────
# 資料結構
# ──────────────────────────────────────────────
@dataclass
class SalaryConfig:
    """員工薪資核定設定（從核定表讀取，每人固定）"""
    employee_id: str
    name: str
    base_salary: float              # 本薪月額
    duty_allowance: float           # 職務津貼月額
    other_allowance: float          # 其他加給（固定部分，如主管加給）
    position_allowance: float       # 職務加給（固定月額）
    full_attendance_bonus: float    # 全勤獎金月額（通常 1,600）
    labor_insurance_base: float     # 勞保投保薪資
    health_insurance_base: float    # 健保投保薪資
    pension_base: float             # 退休金投保薪資
    pension_self_contribute: bool = False   # 是否自提 6%
    meal_exempt: bool = False               # 不訂便當（不扣便當費）
    welfare_exempt: bool = False            # 不扣福利金
    health_dependents: int = 0             # 健保眷屬人數
    daily_work_allowance: float = 0.0      # 出勤加給/天（基本工資差額補貼）
    night_shift_daily: float = 0.0         # 夜班津貼/天（依實際上班天含六日）
    meal_allowance_daily: float = 0.0      # 伙食津貼/天（依實際上班天含六日）


@dataclass
class AttendanceRecord:
    """員工當月出勤記錄（每月變動）"""
    year: int
    month: int
    calendar_days: int              # 當月曆天數
    work_days: int                  # 法定工作日數（Mon-Fri）
    actual_work_days: float         # 實際出班天數（平日）
    holiday_overtime_days: float = 0.0  # 週六/休息日加班天數
    sunday_overtime_days: float = 0.0   # 例假日（週日/國定）加班天數
    overtime_hours_1: float = 0.0   # 平日延時前段加班時數（1.33 倍）
    overtime_hours_2: float = 0.0   # 平日延時後段加班時數（1.66 倍）
    leave_instances: int = 0        # 請假次數（事假/病假，用於扣全勤）
    unpaid_leave_days: float = 0.0  # 無薪假日數
    sick_leave_days: float = 0.0    # 病假日數
    personal_leave_days: float = 0.0    # 事假日數
    annual_leave_days: float = 0.0  # 特休日數（有薪假）
    has_festival_bonus: bool = False    # 當月是否有節金
    meal_count: int = 0             # 便當份數（普通+素食合計）


@dataclass
class SalaryResult:
    """薪資計算結果"""
    name: str
    # 收入
    base_pay: float = 0.0
    duty_pay: float = 0.0
    other_pay: float = 0.0
    position_pay: float = 0.0
    full_attendance_bonus: float = 0.0
    holiday_overtime_pay: float = 0.0
    overtime_pay_1: float = 0.0
    overtime_pay_2: float = 0.0
    night_shift_pay: float = 0.0
    meal_allowance_pay: float = 0.0
    festival_bonus: float = 0.0
    gross_income: float = 0.0
    # 扣除
    labor_insurance_fee: float = 0.0
    health_insurance_fee: float = 0.0
    pension_self: float = 0.0
    welfare_deduction: float = 0.0
    meal_deduction: float = 0.0
    total_deduction: float = 0.0
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
        if self.night_shift_pay:
            print(f"  夜班津貼　　　　　　　: {self.night_shift_pay:>10,.0f} 元")
        if self.meal_allowance_pay:
            print(f"  伙食津貼　　　　　　　: {self.meal_allowance_pay:>10,.0f} 元")
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
# 核心計算函數（純函數，無副作用）
# ──────────────────────────────────────────────
def calculate_salary(config: SalaryConfig, attendance: AttendanceRecord) -> SalaryResult:
    """
    計算員工當月薪資。

    規則摘要：
      收入: base÷30×曆日, duty÷30×曆日, other+dwa×出勤天,
            position(事假/病假比例扣), 全勤(每次請假-300),
            假日加班日費, 延時加班(前段1.33/後段1.66), 節金
      扣除: 勞保2.5%, 健保5.17%×(1+眷屬)×30%, 退休金6%,
            福利min(1%,350), 便當份數×15
    """
    r = SalaryResult(name=config.name)

    # ── 1. 本薪 & 職務津貼 ÷ 30 × 月曆天數 ──
    r.base_pay = _r(config.base_salary / 30 * attendance.calendar_days)
    r.duty_pay = _r(config.duty_allowance / 30 * attendance.calendar_days)

    # ── 2. 其他加給 = 固定 + 出勤天 × 每日加給 ──
    total_work_days = attendance.actual_work_days + attendance.holiday_overtime_days
    r.other_pay = _r(config.other_allowance + total_work_days * config.daily_work_allowance)

    # ── 3. 職務加給（按事假/病假/無薪假天數比例扣除，特休不扣）──
    non_annual_leave = (
        attendance.personal_leave_days
        + attendance.sick_leave_days
        + attendance.unpaid_leave_days
    )
    if non_annual_leave > 0 and attendance.work_days > 0:
        deduct = _r(config.position_allowance / attendance.work_days * non_annual_leave)
        r.position_pay = _r(config.position_allowance - deduct)
    else:
        r.position_pay = _r(config.position_allowance)

    # ── 4. 全勤獎金（每次事假/病假扣 300，特休不扣，最多扣至 0）──
    r.full_attendance_bonus = max(0, config.full_attendance_bonus - attendance.leave_instances * FULL_ATTENDANCE_DEDUCT)

    # ── 5. 加班費共用基數 ──
    overtime_base = (
        config.base_salary + config.duty_allowance + config.other_allowance
        + config.full_attendance_bonus + config.position_allowance
    )
    hourly_base = overtime_base / OVERTIME_DIVISOR

    # ── 5a. 假日加班費（週六/休息日，8小時: 前2hr×1.33 + 後6hr×1.66）──
    holiday_daily = hourly_base * (OVERTIME_RATE_FRONT * 2 + OVERTIME_RATE_BACK * 6)
    r.holiday_overtime_pay = _r(holiday_daily * attendance.holiday_overtime_days)

    # ── 5b. 延時加班費（平日）──
    front_rate = _r(hourly_base * OVERTIME_RATE_FRONT)
    back_rate  = _r(hourly_base * OVERTIME_RATE_BACK)
    r.overtime_pay_1 = _r(front_rate * attendance.overtime_hours_1)
    r.overtime_pay_2 = _r(back_rate  * attendance.overtime_hours_2)

    # ── 7. 夜班津貼 & 伙食津貼（依實際上班天含六日）──
    total_work_days_all = attendance.actual_work_days + attendance.holiday_overtime_days + attendance.sunday_overtime_days
    r.night_shift_pay = _r(config.night_shift_daily * total_work_days_all)
    r.meal_allowance_pay = _r(config.meal_allowance_daily * total_work_days_all)

    # ── 8. 節金 ──
    r.festival_bonus = config.duty_allowance if attendance.has_festival_bonus else 0.0

    # ── 應領合計 ──
    r.gross_income = (
        r.base_pay + r.duty_pay + r.other_pay + r.position_pay
        + r.full_attendance_bonus + r.holiday_overtime_pay
        + r.overtime_pay_1 + r.overtime_pay_2
        + r.night_shift_pay + r.meal_allowance_pay + r.festival_bonus
    )

    # ── 8. 勞保費 ──
    r.labor_insurance_fee = _r(config.labor_insurance_base * LABOR_INSURANCE_RATE)

    # ── 9. 健保費 ──
    r.health_insurance_fee = health_insurance_fee(config)

    # ── 10. 退休金自提 ──
    #   特休視為出勤：effective = actual + annual_leave
    #   全勤 → ratio=1.0，有缺勤 → ratio=effective/30
    effective_work = attendance.actual_work_days + attendance.annual_leave_days
    pension_ratio = 1.0 if effective_work >= attendance.work_days else effective_work / 30
    r.pension_self = (
        _r(config.pension_base * PENSION_SELF_RATE * pension_ratio)
        if config.pension_self_contribute else 0.0
    )

    # ── 11. 福利金 ──
    r.welfare_deduction = 0 if config.welfare_exempt else min(WELFARE_CAP, _r(r.gross_income * WELFARE_RATE))

    # ── 12. 便當費 ──
    if not config.meal_exempt and attendance.meal_count > 0:
        r.meal_deduction = attendance.meal_count * MEAL_PRICE

    # ── 扣除合計 & 實領 ──
    r.total_deduction = (
        r.labor_insurance_fee + r.health_insurance_fee + r.pension_self
        + r.welfare_deduction + r.meal_deduction
    )
    r.net_salary = r.gross_income - r.total_deduction

    return r
