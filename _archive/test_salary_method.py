"""測試兩種 daily_work_allowance 計算方式，對照鄧志展3月實領 90,106"""

from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary, SalaryResult
from copy import deepcopy

config = SalaryConfig(
    employee_id="11",
    name="鄧志展",
    base_salary=16_350,
    duty_allowance=7_950,
    other_allowance=2_850,
    position_allowance=17_850,
    holiday_overtime_daily=2_450,
    daily_work_allowance=260,
    meal_exempt=True,
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
    work_days=22,
    actual_work_days=22.0,
    holiday_overtime_days=4.0,
    overtime_hours_1=50.0,
    overtime_hours_2=60.0,
    leave_instances=0,
)

TARGET = 90_106

print("=" * 60)
print(f"目標實領金額：{TARGET:,}")
print("=" * 60)

# ──────────────────────────────────────────────
# 方法 A：出勤加給 × (平日 + 週六) — 現有邏輯
# ──────────────────────────────────────────────
print("\n【方法 A】出勤加給 × (平日出勤 + 週六加班天數)")
result_a = calculate_salary(config, attendance)
result_a.print_detail()
print(f"  差異 = {result_a.net_salary - TARGET:+,.0f}")

# ──────────────────────────────────────────────
# 方法 B：出勤加給 × 平日出勤天數 only
# ──────────────────────────────────────────────
print("\n【方法 B】出勤加給 × 平日出勤天數 only (不含週六)")

# 暫時修改計算：手動覆蓋 other_pay
result_b = SalaryResult(name=config.name)

result_b.base_pay = round(config.base_salary / 30 * attendance.calendar_days)
result_b.duty_pay = round(config.duty_allowance / 30 * attendance.calendar_days)

# 只用平日出勤天數
result_b.other_pay = round(
    config.other_allowance + attendance.actual_work_days * config.daily_work_allowance
)

result_b.position_pay = round(config.position_allowance)
result_b.full_attendance_bonus = max(0, config.full_attendance_bonus - attendance.leave_instances * 300)
result_b.holiday_overtime_pay = round(config.holiday_overtime_daily * attendance.holiday_overtime_days)

overtime_base = (
    config.base_salary + config.duty_allowance + config.other_allowance
    + config.full_attendance_bonus + config.position_allowance
)
front_rate = round(overtime_base / 240 * 1.33)
back_rate = round(overtime_base / 240 * 1.66)
result_b.overtime_pay_1 = round(front_rate * attendance.overtime_hours_1)
result_b.overtime_pay_2 = round(back_rate * attendance.overtime_hours_2)

result_b.gross_income = (
    result_b.base_pay + result_b.duty_pay + result_b.other_pay
    + result_b.position_pay + result_b.full_attendance_bonus
    + result_b.holiday_overtime_pay + result_b.overtime_pay_1 + result_b.overtime_pay_2
)

result_b.labor_insurance_fee = round(config.labor_insurance_base * 0.025)
result_b.health_insurance_fee = round(config.health_insurance_base * 0.0517 * 1 * 0.30)
result_b.pension_self = round(config.pension_base * 0.06)
result_b.welfare_deduction = min(350, round(result_b.gross_income * 0.01))
result_b.meal_deduction = 0

result_b.total_deduction = (
    result_b.labor_insurance_fee + result_b.health_insurance_fee
    + result_b.pension_self + result_b.welfare_deduction
)
result_b.net_salary = result_b.gross_income - result_b.total_deduction

result_b.print_detail()
print(f"  差異 = {result_b.net_salary - TARGET:+,.0f}")

# ──────────────────────────────────────────────
# 反推：如果實領 = 90,106，出勤天數應該是多少？
# ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("【反推分析】")
print("=" * 60)

# 固定扣除 (不受 gross 影響太多)
fixed_deduct = 1_145 + 943 + 3_648  # 勞保+健保+退休金
# 福利金 = min(350, gross * 1%) → 當 gross > 35,000 時固定 350
# 所以總扣除 ≈ 1,145 + 943 + 3,648 + 350 = 6,086

for welfare in [350]:
    needed_gross = TARGET + fixed_deduct + welfare
    # 驗算福利金
    actual_welfare = min(350, round(needed_gross * 0.01))
    if actual_welfare == welfare:
        print(f"  需要應領合計 = {needed_gross:,}")

        # 方法A反推: gross = base+duty+other+position+attendance+holiday+ot1+ot2
        fixed_part = (
            round(16_350/30*31) + round(7_950/30*31)  # base + duty
            + 17_850 + 1_600  # position + attendance
            + 2_450 * 4  # holiday ot
            + front_rate * 50  # ot1
            + back_rate * 60  # ot2
        )
        needed_other = needed_gross - fixed_part
        print(f"  固定收入部分 = {fixed_part:,}")
        print(f"  需要其他加給 = {needed_other:,}")

        # 方法A: other = 2850 + days*260
        days_a = (needed_other - 2_850) / 260
        print(f"  方法A (含週六): 需要 {days_a:.2f} 天 × 260 (實際 {22+4}=26 天)")

        # 方法B: other = 2850 + workdays*260
        days_b = (needed_other - 2_850) / 260
        print(f"  方法B (僅平日): 需要 {days_b:.2f} 天 × 260 (實際平日 22 天)")
