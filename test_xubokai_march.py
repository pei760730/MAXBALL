"""驗算 許柏凱 #13 — 2026年3月 — 目標實領 34,262"""

from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary
from meal_tracker import EmployeeMealRecord

config = SalaryConfig(
    employee_id="13",
    name="許柏凱",
    base_salary=14_100,
    duty_allowance=2_700,
    other_allowance=4_800,
    position_allowance=9_500,
    holiday_overtime_daily=1_719,
    full_attendance_bonus=1_600,
    labor_insurance_base=30_300,
    health_insurance_base=30_300,
    health_dependents=2,
    pension_base=30_300,
    pension_self_contribute=False,
    daily_work_allowance=175,
)

attendance = AttendanceRecord(
    year=2026,
    month=3,
    calendar_days=31,
    work_days=22,
    actual_work_days=22.0,      # 22天全勤
    holiday_overtime_days=0.0,  # 無週六加班
    overtime_hours_1=0.0,       # 無加班
    overtime_hours_2=0.0,
    leave_instances=0,
)

meal = EmployeeMealRecord(name="許柏凱", normal_count=22)  # 22份×15=330

result = calculate_salary(config, attendance, meal)
result.print_detail()

TARGET = 34_262
print(f"目標實領：{TARGET:,}")
print(f"計算實領：{result.net_salary:,.0f}")
diff = result.net_salary - TARGET
if diff == 0:
    print("✓ 完全吻合！")
else:
    print(f"差異：{diff:+,.0f}")
