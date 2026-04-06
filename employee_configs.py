"""
台籍員工薪資核定基準
（依公司核定表，不含外籍員工）

daily_work_allowance: 已知 鄧志展=260, 許柏凱=175；其餘待人事確認後補入。
"""

from salary_calculator import SalaryConfig

EMPLOYEE_CONFIGS: list[SalaryConfig] = [

    # ── #5 王靖銘 ──
    SalaryConfig(
        employee_id="5",
        name="王靖銘",
        base_salary=16_350,
        duty_allowance=7_950,
        other_allowance=2_850,
        position_allowance=17_850,
        front_overtime_rate=258,
        back_overtime_rate=322,
        holiday_overtime_daily=2_450,
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=45_800,
        health_dependents=0,
        pension_base=45_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #8 陳麥斯 ──
    SalaryConfig(
        employee_id="8",
        name="陳麥斯",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        front_overtime_rate=194,
        back_overtime_rate=242,
        holiday_overtime_daily=1_840,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=1,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #9 李世彬 ──
    SalaryConfig(
        employee_id="9",
        name="李世彬",
        base_salary=16_350,
        duty_allowance=8_550,
        other_allowance=9_860,
        position_allowance=16_800,
        front_overtime_rate=295,
        back_overtime_rate=368,
        holiday_overtime_daily=2_795,
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=55_400,
        health_dependents=0,
        pension_base=55_400,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #10 許清輝 ──
    SalaryConfig(
        employee_id="10",
        name="許清輝",
        base_salary=16_350,
        duty_allowance=7_200,
        other_allowance=0,
        position_allowance=7_450,
        front_overtime_rate=181,
        back_overtime_rate=225,
        holiday_overtime_daily=1_714,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=True,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #11 鄧志展 ──
    SalaryConfig(
        employee_id="11",
        name="鄧志展",
        base_salary=16_350,
        duty_allowance=7_950,
        other_allowance=2_850,
        position_allowance=17_850,
        front_overtime_rate=258,
        back_overtime_rate=322,
        holiday_overtime_daily=2_450,
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=60_800,
        health_dependents=0,
        pension_base=60_800,
        pension_self_contribute=True,
        meal_exempt=True,               # 鄧志展不訂便當，永遠不扣便當費
        daily_work_allowance=260,
    ),

    # ── #13 許柏凱 ──
    SalaryConfig(
        employee_id="13",
        name="許柏凱",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=4_800,
        position_allowance=9_500,
        front_overtime_rate=181,
        back_overtime_rate=226,
        holiday_overtime_daily=1_719,
        full_attendance_bonus=1_600,
        labor_insurance_base=30_300,
        health_insurance_base=30_300,
        health_dependents=2,
        pension_base=30_300,
        pension_self_contribute=False,
        daily_work_allowance=175,
    ),

    # ── #14 陳姿惠 ──
    SalaryConfig(
        employee_id="14",
        name="陳姿惠",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        front_overtime_rate=194,
        back_overtime_rate=242,
        holiday_overtime_daily=1_840,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #16 陳沛思 ──
    SalaryConfig(
        employee_id="16",
        name="陳沛思",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        front_overtime_rate=194,
        back_overtime_rate=242,
        holiday_overtime_daily=1_840,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #17 簡宜君 ──
    SalaryConfig(
        employee_id="17",
        name="簡宜君",
        base_salary=14_100,
        duty_allowance=2_000,
        other_allowance=1_120,
        position_allowance=10_680,
        front_overtime_rate=163,
        back_overtime_rate=204,
        holiday_overtime_daily=1_551,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #18 林義明 ──
    SalaryConfig(
        employee_id="18",
        name="林義明",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=3_650,
        position_allowance=10_150,
        front_overtime_rate=178,
        back_overtime_rate=223,
        holiday_overtime_daily=1_693,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #19 莊明燦 ──
    SalaryConfig(
        employee_id="19",
        name="莊明燦",
        base_salary=14_100,
        duty_allowance=2_850,
        other_allowance=0,
        position_allowance=13_120,
        front_overtime_rate=176,
        back_overtime_rate=219,
        holiday_overtime_daily=1_665,
        full_attendance_bonus=1_600,
        labor_insurance_base=30_300,
        health_insurance_base=30_300,
        health_dependents=1,
        pension_base=30_300,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #20 黃郁愛 ──
    SalaryConfig(
        employee_id="20",
        name="黃郁愛",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        front_overtime_rate=194,
        back_overtime_rate=242,
        holiday_overtime_daily=1_840,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #22 許連灯 ──
    # 自提狀態待確認（核定表標記為 ?）
    SalaryConfig(
        employee_id="22",
        name="許連灯",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=3_120,
        position_allowance=8_480,
        front_overtime_rate=166,
        back_overtime_rate=208,
        holiday_overtime_daily=1_578,
        full_attendance_bonus=1_600,
        labor_insurance_base=38_200,
        health_insurance_base=38_200,
        health_dependents=0,
        pension_base=38_200,
        pension_self_contribute=False,  # TODO: 核定表標記 ?，待確認
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #26 王淑如 ──
    SalaryConfig(
        employee_id="26",
        name="王淑如",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=4_680,
        position_allowance=8_590,
        front_overtime_rate=176,
        back_overtime_rate=219,
        holiday_overtime_daily=1_665,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #29 許天賜 ──
    SalaryConfig(
        employee_id="29",
        name="許天賜",
        base_salary=14_100,
        duty_allowance=7_000,
        other_allowance=0,
        position_allowance=16_560,
        front_overtime_rate=230,
        back_overtime_rate=287,
        holiday_overtime_daily=2_183,
        full_attendance_bonus=1_600,
        labor_insurance_base=42_000,
        health_insurance_base=42_000,
        health_dependents=1,
        pension_base=42_000,
        pension_self_contribute=True,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #31 陳佩欣 ──
    SalaryConfig(
        employee_id="31",
        name="陳佩欣",
        base_salary=16_350,
        duty_allowance=2_700,
        other_allowance=1_120,
        position_allowance=10_680,
        front_overtime_rate=163,
        back_overtime_rate=204,
        holiday_overtime_daily=1_551,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=True,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #37 吳慧娟 ──
    SalaryConfig(
        employee_id="37",
        name="吳慧娟",
        base_salary=14_100,
        duty_allowance=2_000,
        other_allowance=3_580,
        position_allowance=8_770,
        front_overtime_rate=170,
        back_overtime_rate=213,
        holiday_overtime_daily=1_617,
        full_attendance_bonus=1_600,
        labor_insurance_base=33_300,
        health_insurance_base=33_300,
        health_dependents=0,
        pension_base=33_300,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #39 劉英美 ──
    SalaryConfig(
        employee_id="39",
        name="劉英美",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=2_000,
        position_allowance=9_600,
        front_overtime_rate=166,
        back_overtime_rate=208,
        holiday_overtime_daily=1_578,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),

    # ── #45 莊志成 ──
    SalaryConfig(
        employee_id="45",
        name="莊志成",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=2_300,
        position_allowance=10_500,
        front_overtime_rate=173,
        back_overtime_rate=216,
        holiday_overtime_daily=1_641,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=0,         # TODO: 待確認
    ),
]

# 方便查詢
CONFIGS_BY_ID   = {c.employee_id: c for c in EMPLOYEE_CONFIGS}
CONFIGS_BY_NAME = {c.name: c for c in EMPLOYEE_CONFIGS}
