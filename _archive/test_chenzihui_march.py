"""計算 陳姿惠 #14 — 2026年3月"""

from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary
from meal_tracker import EmployeeMealRecord

config = SalaryConfig(
    employee_id="14",
    name="陳姿惠",
    base_salary=14_100,
    duty_allowance=2_700,
    other_allowance=0,
    position_allowance=16_600,
    holiday_overtime_daily=1_840,
    full_attendance_bonus=1_600,
    labor_insurance_base=34_800,
    health_insurance_base=34_800,
    health_dependents=0,
    pension_base=34_800,
    pension_self_contribute=False,
    daily_work_allowance=0,
)

attendance = AttendanceRecord(
    year=2026,
    month=3,
    calendar_days=31,
    work_days=22,
    actual_work_days=22.0,
    holiday_overtime_days=0.0,
    overtime_hours_1=0.0,
    overtime_hours_2=0.0,
    leave_instances=0,
)

# 情境A：無便當
print("【情境A】無便當費")
result_a = calculate_salary(config, attendance, None)
result_a.print_detail()

# 情境B：22份便當
print("【情境B】22份便當 (22×15=330)")
meal = EmployeeMealRecord(name="陳姿惠", normal_count=22)
result_b = calculate_salary(config, attendance, meal)
result_b.print_detail()
