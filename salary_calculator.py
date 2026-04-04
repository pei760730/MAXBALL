"""
薪資計算模組

功能：
- 讀取員工薪資基本設定（本薪、職務津貼、全勤獎金等）
- 讀取出勤資料（加班時數、假日加班、事病假等）
- 自動扣除便當費用
- 計算勞保、健保、退休金自提
- 產生薪資明細並可寫回 Google Sheets

薪資組成：
  【收入項目】
    本薪（按出勤日數比例給付）
    職務津貼（按出勤日數比例給付）
    其他加給
    全勤獎金（全勤且無無薪假才給付）
    假日加班費（週六休息日）
    延時加班費（1.33 倍、1.66 倍）
    節金（春節、端午、中秋）

  【扣除項目】
    勞工保險費（員工自付部分）
    全民健康保險費（員工自付部分）
    新制退休金自提（6%，若有選擇自提）
    便當費（每月訂購份數 × 單價）
"""

from dataclasses import dataclass, field
from meal_tracker import EmployeeMealRecord, MEAL_PRICE_NORMAL, MEAL_PRICE_VEG


# ──────────────────────────────────────────────
# 勞健保費率（2025 年適用，可依年度調整）
# ──────────────────────────────────────────────
LABOR_INSURANCE_EMPLOYEE_RATE = 0.1100   # 勞保員工負擔比率 11%（含就業保險）
HEALTH_INSURANCE_EMPLOYEE_RATE = 0.05   # 健保員工負擔比率 5%（含補充保費）
PENSION_EMPLOYER_RATE = 0.06             # 退休金雇主提撥 6%（員工自提另計）

# 加班費倍率
OVERTIME_RATE_1 = 1.3333   # 前 2 小時 1⅓ 倍
OVERTIME_RATE_2 = 1.6667   # 後 2 小時 1⅔ 倍


@dataclass
class SalaryConfig:
    """
    員工薪資核定設定（從「核定」工作表讀取）
    """
    employee_id: str
    name: str
    base_salary: float         # 本薪（月）
    duty_allowance: float      # 職務津貼（月）
    other_allowance: float     # 其他加給（月）
    full_attendance_bonus: float  # 全勤獎金
    labor_insurance_base: float   # 勞保投保薪資
    health_insurance_base: float  # 健保投保薪資
    pension_base: float           # 退休金投保薪資
    pension_self_contribute: bool = False  # 是否自提 6%


@dataclass
class AttendanceRecord:
    """
    員工出勤記錄（從「出勤」工作表讀取）
    """
    year: int
    month: int
    calendar_days: int          # 當月曆日數
    work_days: int              # 法定工作日數
    actual_work_days: float     # 實際出勤日數
    holiday_overtime_days: float = 0.0   # 假日加班日數（週六/休息日）
    sunday_overtime_days: float  = 0.0   # 例假日加班日數
    overtime_hours_1: float = 0.0        # 延時加班前段時數（1.33 倍）
    overtime_hours_2: float = 0.0        # 延時加班後段時數（1.66 倍）
    unpaid_leave_days: float = 0.0       # 無薪假日數
    sick_leave_days: float = 0.0         # 病假日數（半薪）
    personal_leave_days: float = 0.0     # 事假日數（無薪）
    annual_leave_days: float = 0.0       # 特休日數（有薪）
    has_festival_bonus: bool = False     # 當月是否有節金


@dataclass
class SalaryResult:
    """
    薪資計算結果
    """
    name: str
    # 收入
    base_pay: float = 0.0
    duty_pay: float = 0.0
    other_pay: float = 0.0
    full_attendance_bonus: float = 0.0
    holiday_overtime_pay: float = 0.0
    overtime_pay_1: float = 0.0
    overtime_pay_2: float = 0.0
    festival_bonus: float = 0.0
    gross_income: float = 0.0

    # 扣除
    labor_insurance_fee: float = 0.0
    health_insurance_fee: float = 0.0
    pension_self: float = 0.0
    meal_deduction: float = 0.0
    total_deduction: float = 0.0

    # 實領
    net_salary: float = 0.0

    def print_detail(self):
        """列印薪資明細"""
        print(f"\n{'='*50}")
        print(f"  {self.name}  薪資明細")
        print(f"{'='*50}")
        print("【收入項目】")
        print(f"  本薪（按出勤比例）　　: {self.base_pay:>10,.0f} 元")
        print(f"  職務津貼（按出勤比例）: {self.duty_pay:>10,.0f} 元")
        print(f"  其他加給　　　　　　　: {self.other_pay:>10,.0f} 元")
        print(f"  全勤獎金　　　　　　　: {self.full_attendance_bonus:>10,.0f} 元")
        print(f"  假日加班費　　　　　　: {self.holiday_overtime_pay:>10,.0f} 元")
        print(f"  延時加班費（1.33倍）　: {self.overtime_pay_1:>10,.0f} 元")
        print(f"  延時加班費（1.66倍）　: {self.overtime_pay_2:>10,.0f} 元")
        print(f"  節金　　　　　　　　　: {self.festival_bonus:>10,.0f} 元")
        print(f"  {'─'*38}")
        print(f"  應領合計　　　　　　　: {self.gross_income:>10,.0f} 元")
        print("【扣除項目】")
        print(f"  勞保費（員工自付）　　: {self.labor_insurance_fee:>10,.0f} 元")
        print(f"  健保費（員工自付）　　: {self.health_insurance_fee:>10,.0f} 元")
        print(f"  退休金自提（6%）　　　: {self.pension_self:>10,.0f} 元")
        print(f"  便當費　　　　　　　　: {self.meal_deduction:>10,.0f} 元")
        print(f"  {'─'*38}")
        print(f"  扣除合計　　　　　　　: {self.total_deduction:>10,.0f} 元")
        print(f"{'='*50}")
        print(f"  實領薪資　　　　　　　: {self.net_salary:>10,.0f} 元")
        print(f"{'='*50}\n")


def calculate_salary(
    config: SalaryConfig,
    attendance: AttendanceRecord,
    meal_record: EmployeeMealRecord | None = None,
) -> SalaryResult:
    """
    計算員工當月薪資。

    Args:
        config: 薪資核定設定。
        attendance: 出勤記錄。
        meal_record: 便當訂購記錄（若 None 則不扣便當費）。

    Returns:
        SalaryResult 薪資計算結果。
    """
    result = SalaryResult(name=config.name)
    cal_days = attendance.calendar_days

    # ── 1. 本薪 & 職務津貼（按給薪日數比例）──
    daily_base  = config.base_salary / 30
    daily_duty  = config.duty_allowance / 30
    pay_days    = attendance.actual_work_days + attendance.annual_leave_days

    result.base_pay = round(daily_base * pay_days)
    result.duty_pay = round(daily_duty * pay_days)
    result.other_pay = round(config.other_allowance)

    # ── 2. 全勤獎金（無事/病/無薪假才給）──
    has_absence = (
        attendance.unpaid_leave_days > 0
        or attendance.sick_leave_days > 0
        or attendance.personal_leave_days > 0
    )
    result.full_attendance_bonus = (
        0.0 if has_absence else config.full_attendance_bonus
    )

    # ── 3. 假日加班費（週六休息日，1 倍工資 + 1 倍加給）──
    daily_wage = (config.base_salary + config.duty_allowance) / 30
    result.holiday_overtime_pay = round(
        daily_wage * attendance.holiday_overtime_days * 2
    )

    # ── 4. 延時加班費（時薪 × 倍率）──
    hourly_wage = daily_wage / 8
    result.overtime_pay_1 = round(hourly_wage * OVERTIME_RATE_1 * attendance.overtime_hours_1)
    result.overtime_pay_2 = round(hourly_wage * OVERTIME_RATE_2 * attendance.overtime_hours_2)

    # ── 5. 節金（春節/端午/中秋，按核定節金月份計算）──
    result.festival_bonus = (
        config.duty_allowance if attendance.has_festival_bonus else 0.0
    )

    # ── 應領合計 ──
    result.gross_income = (
        result.base_pay
        + result.duty_pay
        + result.other_pay
        + result.full_attendance_bonus
        + result.holiday_overtime_pay
        + result.overtime_pay_1
        + result.overtime_pay_2
        + result.festival_bonus
    )

    # ── 6. 勞保費 ──
    result.labor_insurance_fee = round(
        config.labor_insurance_base * LABOR_INSURANCE_EMPLOYEE_RATE
    )

    # ── 7. 健保費 ──
    result.health_insurance_fee = round(
        config.health_insurance_base * HEALTH_INSURANCE_EMPLOYEE_RATE
    )

    # ── 8. 退休金自提 ──
    result.pension_self = (
        round(config.pension_base * 0.06) if config.pension_self_contribute else 0.0
    )

    # ── 9. 便當費 ──
    if meal_record:
        result.meal_deduction = meal_record.total_cost

    # ── 扣除合計 ──
    result.total_deduction = (
        result.labor_insurance_fee
        + result.health_insurance_fee
        + result.pension_self
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
    """
    批次計算所有員工薪資。

    Args:
        configs: 員工薪資設定清單。
        attendances: 以員工姓名為 key 的出勤記錄 dict。
        meal_summary: meal_tracker.summarize() 回傳的摘要（可選）。

    Returns:
        list[SalaryResult]
    """
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
# 單機示範（不需要 Google Sheets）
# ──────────────────────────────────────────────
def demo():
    """示範計算一位員工的薪資（2026年2月）。"""
    from meal_tracker import EmployeeMealRecord

    config = SalaryConfig(
        employee_id="11",
        name="鄧志展",
        base_salary=27_000,
        duty_allowance=13_500,
        other_allowance=7_108,
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=60_800,
        pension_base=60_800,
        pension_self_contribute=True,
    )

    attendance = AttendanceRecord(
        year=2026,
        month=2,
        calendar_days=28,
        work_days=14,
        actual_work_days=16.375,
        holiday_overtime_days=2.375,
        overtime_hours_1=30,
        overtime_hours_2=38,
        has_festival_bonus=False,
    )

    # 2026年3月便當：訂了 20 份普通便當
    meal = EmployeeMealRecord(name="鄧志展", normal_count=20)

    result = calculate_salary(config, attendance, meal)
    result.print_detail()
    return result


if __name__ == "__main__":
    demo()
