"""計算 莊明燦 #19 — 2026年3月
特休0.5天（03/26半天），伙食22×15=330
"""

from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary
from meal_tracker import EmployeeMealRecord

config = SalaryConfig(
    employee_id="19",
    name="莊明燦",
    base_salary=14_100,
    duty_allowance=2_850,
    other_allowance=0,
    position_allowance=13_120,
    holiday_overtime_daily=1_665,
    full_attendance_bonus=1_600,
    labor_insurance_base=30_300,
    health_insurance_base=30_300,
    health_dependents=1,
    pension_base=30_300,
    pension_self_contribute=False,
    daily_work_allowance=50,
)

meal = EmployeeMealRecord(name="莊明燦", normal_count=22)

# 情境A：特休有薪，actual_work_days = 22（特休算出勤）
print("【情境A】特休算出勤 → actual_work_days=22")
att_a = AttendanceRecord(
    year=2026, month=3, calendar_days=31, work_days=22,
    actual_work_days=22.0,
    holiday_overtime_days=0.0,
    overtime_hours_1=0.0, overtime_hours_2=0.0,
    leave_instances=0,        # 特休不扣全勤
    annual_leave_days=0.5,
)
result_a = calculate_salary(config, att_a, meal)
result_a.print_detail()

# 情境B：actual_work_days = 21.5（特休半天不算出勤）
print("【情境B】特休不算出勤 → actual_work_days=21.5")
att_b = AttendanceRecord(
    year=2026, month=3, calendar_days=31, work_days=22,
    actual_work_days=21.5,
    holiday_overtime_days=0.0,
    overtime_hours_1=0.0, overtime_hours_2=0.0,
    leave_instances=0,
    annual_leave_days=0.5,
)
result_b = calculate_salary(config, att_b, meal)
result_b.print_detail()
