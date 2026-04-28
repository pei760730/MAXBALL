"""
台籍員工薪資核定基準
（依公司核定表，不含外籍員工）

daily_work_allowance 年份累加邏輯（台灣基本工資調漲補差額，依表現）：
  #9  李世彬=40 (2026)
  #10 許清輝=160 (40+40+40+40)
  #11 鄧志展=260 (110+50+50+50)
  #13 許柏凱=175 (60+30+40+45)
  #18 林義明=280 (150+40+40+50)
  #19 莊明燦=50 (2026)
  #22 許連灯=175 (45+50+50+30)
  #26 王淑如=135 (45+30+30+30)
  #29 許天賜=245 (85+50+50+60)
  #8,#14,#16,#17,#20 = 0（薪資已達標）
  #31 陳佩欣=0（薪資已達標）
  #37 吳慧娟=155 (45+30+40+40)
  #39 劉英美=95 (45+30+20)
  #45 莊志成=95 (55+40)
  #5 王靖銘 待確認
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
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=45_800,
        health_dependents=0,
        pension_base=45_800,
        pension_self_contribute=False,
        daily_work_allowance=235,        # 反推確認：50,375 exact match
    ),

    # ── #8 陳麥斯 ── 薪資已達標，無需加給
    SalaryConfig(
        employee_id="8",
        name="陳麥斯",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=1,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,
    ),

    # ── #9 李世彬 ──
    SalaryConfig(
        employee_id="9",
        name="李世彬",
        base_salary=16_350,
        duty_allowance=8_550,
        other_allowance=9_860,
        position_allowance=16_800,
        full_attendance_bonus=1_600,
        labor_insurance_base=45_800,
        health_insurance_base=55_400,
        health_dependents=0,
        pension_base=55_400,
        pension_self_contribute=False,
        daily_work_allowance=40,
    ),

    # ── #10 許清輝 ──
    SalaryConfig(
        employee_id="10",
        name="許清輝",
        base_salary=16_350,
        duty_allowance=7_200,
        other_allowance=0,
        position_allowance=7_450,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=True,
        daily_work_allowance=160,
    ),

    # ── #11 鄧志展 ──
    SalaryConfig(
        employee_id="11",
        name="鄧志展",
        base_salary=16_350,
        duty_allowance=7_950,
        other_allowance=2_850,
        position_allowance=17_850,
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
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        meal_exempt=True,               # 陳姿惠不訂便當
        daily_work_allowance=0,
    ),

    # ── #16 陳沛思 ── 薪資已達標，無需加給
    SalaryConfig(
        employee_id="16",
        name="陳沛思",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,
        welfare_exempt=True,            # 家族成員，不扣福利金
    ),

    # ── #17 簡宜君 ── 薪資已達標，無需加給
    SalaryConfig(
        employee_id="17",
        name="簡宜君",
        base_salary=14_100,
        duty_allowance=2_000,
        other_allowance=1_120,
        position_allowance=10_680,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=0,
    ),

    # ── #18 林義明 ──
    SalaryConfig(
        employee_id="18",
        name="林義明",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=3_650,
        position_allowance=10_150,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=False,
        daily_work_allowance=280,
    ),

    # ── #19 莊明燦 ──
    SalaryConfig(
        employee_id="19",
        name="莊明燦",
        base_salary=14_100,
        duty_allowance=2_850,
        other_allowance=0,
        position_allowance=13_120,
        full_attendance_bonus=1_600,
        labor_insurance_base=0,             # 免繳勞保（截圖勞保=0）
        health_insurance_base=30_300,
        health_dependents=0,
        pension_base=30_300,
        pension_self_contribute=True,
        daily_work_allowance=50,        # 50 (2026)
    ),

    # ── #20 黃郁愛 ── 薪資已達標，無需加給
    SalaryConfig(
        employee_id="20",
        name="黃郁愛",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=0,
        position_allowance=16_600,
        full_attendance_bonus=1_600,
        labor_insurance_base=34_800,
        health_insurance_base=34_800,
        health_dependents=0,
        pension_base=34_800,
        pension_self_contribute=False,
        daily_work_allowance=0,
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
        full_attendance_bonus=1_600,
        labor_insurance_base=38_200,
        health_insurance_base=38_200,
        health_dependents=0,
        pension_base=38_200,
        pension_self_contribute=False,  # 截圖確認：退休金自提=0
        daily_work_allowance=175,       # 45+50+50+30
    ),

    # ── #26 王淑如 ──
    SalaryConfig(
        employee_id="26",
        name="王淑如",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=4_680,
        position_allowance=8_590,
        full_attendance_bonus=1_600,
        labor_insurance_base=31_800,
        health_insurance_base=31_800,
        health_dependents=0,
        pension_base=31_800,
        pension_self_contribute=True,   # 截圖確認：退休金自提6%=1908
        daily_work_allowance=135,       # 45+30+30+30
    ),

    # ── #29 許天賜 ──
    SalaryConfig(
        employee_id="29",
        name="許天賜",
        base_salary=16_350,             # 截圖確認（非14100）
        duty_allowance=7_000,
        other_allowance=0,
        position_allowance=16_560,
        full_attendance_bonus=1_600,
        labor_insurance_base=42_000,
        health_insurance_base=42_000,
        health_dependents=0,            # 截圖確認：dep=0；健保查表 42000 → 651
        pension_base=42_000,
        pension_self_contribute=True,
        daily_work_allowance=245,       # 85+50+50+60
    ),

    # ── #31 陳佩欣 ──
    SalaryConfig(
        employee_id="31",
        name="陳佩欣",
        base_salary=14_100,
        duty_allowance=2_000,           # 截圖: 2067=2000/30*31
        other_allowance=1_120,
        position_allowance=10_680,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=1,            # 截圖: 健保+眷屬1人=916
        pension_base=29_500,
        pension_self_contribute=False,  # 截圖: 退休金=0
        daily_work_allowance=0,
    ),

    # ── #37 吳慧娟 ──
    SalaryConfig(
        employee_id="37",
        name="吳慧娟",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=3_580,
        position_allowance=8_770,
        full_attendance_bonus=1_600,
        labor_insurance_base=33_300,
        health_insurance_base=33_300,
        health_dependents=0,
        pension_base=33_300,
        pension_self_contribute=False,
        daily_work_allowance=155,       # 45+30+40+40
    ),

    # ── #39 劉英美 ──
    SalaryConfig(
        employee_id="39",
        name="劉英美",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=2_000,
        position_allowance=9_600,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=95,        # 45+30+20
    ),

    # ── #45 莊志成 ──
    SalaryConfig(
        employee_id="45",
        name="莊志成",
        base_salary=14_100,
        duty_allowance=2_700,
        other_allowance=2_300,
        position_allowance=10_500,
        full_attendance_bonus=1_600,
        labor_insurance_base=29_500,
        health_insurance_base=29_500,
        health_dependents=0,
        pension_base=29_500,
        pension_self_contribute=False,
        daily_work_allowance=95,        # 截圖確認: 2300+25×95=4675
        meal_exempt=True,               # 截圖無便當扣款
        night_shift_daily=250,          # 夜班津貼/天
        meal_allowance_daily=100,       # 截圖確認: 100×25=2500（非150）
    ),
]

# 方便查詢
CONFIGS_BY_ID   = {c.employee_id: c for c in EMPLOYEE_CONFIGS}
CONFIGS_BY_NAME = {c.name: c for c in EMPLOYEE_CONFIGS}
