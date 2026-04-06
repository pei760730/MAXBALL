"""反推 莊明燦 #19 — 2026年3月 — 實領 30,359"""

from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary
from meal_tracker import EmployeeMealRecord

TARGET = 30_359

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

# 反推需要的 gross
print("=" * 60)
print(f"目標實領：{TARGET:,}")
print("=" * 60)

# 固定扣除
labor = round(30_300 * 0.025)   # 758
health_1dep = round(30_300 * 0.0517 * 2 * 0.30)  # 940 (1眷屬)
health_2dep = round(30_300 * 0.0517 * 3 * 0.30)  # 1410 (2眷屬)
meal_cost = 330

print(f"勞保費: {labor}")
print(f"健保費(1眷屬): {health_1dep}")
print(f"健保費(2眷屬): {health_2dep}")

for dep_label, health_fee in [("1眷屬", health_1dep), ("2眷屬", health_2dep)]:
    # gross = net + labor + health + welfare + meal
    # welfare = min(350, round(gross * 0.01))
    # 嘗試不同 gross 值
    for gross in range(30_000, 36_000):
        welfare = min(350, round(gross * 0.01))
        total_ded = labor + health_fee + welfare + meal_cost
        net = gross - total_ded
        if net == TARGET:
            print(f"\n找到！ {dep_label}: gross = {gross:,}")
            print(f"  扣除: 勞保{labor} + 健保{health_fee} + 福利{welfare} + 便當{meal_cost} = {total_ded}")

            # 反推收入項目
            base = round(14_100 / 30 * 31)  # 14,570
            duty = round(2_850 / 30 * 31)   # 2,945
            position = 13_120
            remaining = gross - base - duty - position
            print(f"  本薪: {base}")
            print(f"  職務津貼: {duty}")
            print(f"  職務加給: {position}")
            print(f"  剩餘 (其他加給+全勤): {remaining}")

            for attn_bonus in [1_600, 1_300, 1_000, 0]:
                other = remaining - attn_bonus
                if other > 0:
                    days = other / 50
                    print(f"    全勤={attn_bonus} → 其他加給={other} → 出勤天={days:.1f}")

            # 也試試 position 被比例扣除的情況
            print(f"\n  -- 如果職務加給被特休扣除 --")
            for leave_day in [0.5]:
                for attn_bonus in [1_600, 1_300, 0]:
                    for pos_method in ["÷30", "÷22"]:
                        if pos_method == "÷30":
                            pos_deduct = round(13_120 / 30 * leave_day)
                        else:
                            pos_deduct = round(13_120 / 22 * leave_day)
                        pos_actual = 13_120 - pos_deduct
                        other_needed = gross - base - duty - pos_actual - attn_bonus
                        if other_needed > 0:
                            days = other_needed / 50
                            print(f"    職務加給{pos_method}扣{pos_deduct}={pos_actual}, 全勤={attn_bonus} → 其他加給={other_needed} → 天={days:.1f}")
