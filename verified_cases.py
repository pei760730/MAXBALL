"""
已驗證薪資案例（回歸測試）
==========================
每個案例 = 一位員工的打卡紀錄 + 實際薪資。
執行此檔案可驗證計算引擎是否正確。

新增案例流程：
  1. 從打卡紀錄讀取出勤資料
  2. 用 calculate_salary() 計算
  3. 與實際薪資比對
  4. 通過後加入 CASES 清單
"""

from salary_calculator import calculate_salary, AttendanceRecord, SalaryConfig
from employee_configs import CONFIGS_BY_NAME


# ──────────────────────────────────────────────
# 已確認規則（從驗證中沉澱）
# ──────────────────────────────────────────────
CONFIRMED_RULES = {
    "base_duty_formula": {
        "rule": "本薪÷30×曆日, 職務津貼÷30×曆日（不受請假影響）",
        "verified_by": ["許柏凱#13", "林義明#18", "劉英美#39"],
    },
    "annual_leave_no_deduct": {
        "rule": "特休不扣全勤、不扣職務加給，只減少 actual_work_days 影響每日加給",
        "verified_by": ["林義明#18（特休1天, 全勤1600不扣, exact 36687）"],
    },
    "pension_annual_leave": {
        "rule": "退休金自提：特休視為出勤，effective_days = actual + annual_leave",
        "verified_by": ["許清輝#10（特休1天, ratio=1.0, diff=-1）"],
    },
    "overtime_base_240": {
        "rule": "加班時薪 = (本薪+職務津貼+其他加給固定+全勤+職務加給) ÷ 240 × 倍率",
        "verified_by": ["鄧志展#11（diff=-2）"],
    },
    "meal_exempt": {
        "rule": "meal_exempt=True 的員工永遠不扣便當費",
        "verified_by": ["陳姿惠#14（exact 33800）"],
    },
    "daily_work_allowance": {
        "rule": "其他加給 = 固定加給 + (actual_work_days + holiday_ot_days) × dwa",
        "verified_by": ["王靖銘#5（dwa=235, exact 50375）", "許柏凱#13（dwa=175, exact 34262）"],
    },
    "health_insurance_formula": {
        "rule": "健保費 = 投保薪資 × 5.17% × (1+眷屬) × 30%，可能與查表有1-2元差",
        "verified_by": ["鄧志展#11（diff=-2）", "許清輝#10（diff=-1）"],
    },
}


# ──────────────────────────────────────────────
# 驗證案例定義
# ──────────────────────────────────────────────
CASES = [
    {
        "name": "王靖銘",
        "month": "2026-03",
        "target": 50375,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
        },
        "notes": "22天全勤, 無加班, 無便當. dwa=235 反推確認",
    },
    {
        "name": "李世彬",
        "month": "2026-03",
        "target": 52116,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 19.5,
            "annual_leave_days": 2.5,
            "meal_count": 20,
        },
        "notes": "特休2.5天, 伙食20×15=300",
    },
    {
        "name": "許清輝",
        "month": "2026-03",
        "target": 36233,
        "tolerance": 1,  # 健保查表差異
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "overtime_hours_1": 18.5,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        "notes": "特休1天, 加班18.5hr全前段, pension=True ratio=1.0",
    },
    {
        "name": "許柏凱",
        "month": "2026-03",
        "target": 34262,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 22,
        },
        "notes": "22天全勤, 無加班, dep=2",
    },
    {
        "name": "陳姿惠",
        "month": "2026-03",
        "target": 33800,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
        },
        "notes": "22天全勤, meal_exempt=True",
    },
    {
        "name": "林義明",
        "month": "2026-03",
        "target": 36687,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        "notes": "特休1天, 驗證特休不扣全勤/職務加給",
    },
    {
        "name": "劉英美",
        "month": "2026-03",
        "target": 30718,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        "notes": "特休1天, pension=False",
    },
]


# ──────────────────────────────────────────────
# 執行驗證
# ──────────────────────────────────────────────
def run_all(verbose: bool = False) -> bool:
    """執行所有驗證案例，回傳是否全部通過。"""
    passed = 0
    failed = 0

    for case in CASES:
        config = CONFIGS_BY_NAME[case["name"]]

        att_kwargs = {
            "year": 2026,
            "month": int(case["month"].split("-")[1]),
            **case["attendance"],
        }
        att = AttendanceRecord(**att_kwargs)
        result = calculate_salary(config, att)

        diff = abs(result.net_salary - case["target"])
        ok = diff <= case["tolerance"]

        if ok:
            passed += 1
            mark = "✓"
        else:
            failed += 1
            mark = "✗"

        print(f"  {mark} {case['name']}: {result.net_salary:.0f} vs {case['target']} "
              f"(diff={result.net_salary - case['target']:+.0f}, tol={case['tolerance']})")

        if verbose and not ok:
            result.print_detail()

    print(f"\n  結果: {passed} 通過, {failed} 失敗 (共 {len(CASES)} 案例)")

    if CONFIRMED_RULES:
        print(f"\n  已確認規則: {len(CONFIRMED_RULES)} 條")
        for key, rule in CONFIRMED_RULES.items():
            print(f"    - {rule['rule']}")

    return failed == 0


if __name__ == "__main__":
    print("=" * 50)
    print("  薪資計算引擎 — 回歸測試")
    print("=" * 50)
    success = run_all(verbose=True)
    if not success:
        exit(1)
