"""
已驗證薪資案例（回歸測試）+ 規則 coverage 自我檢查
=================================================
每個 Case = 一位員工的當月出勤 + 實際薪資（截圖）+ tolerance 歸因。

執行：
  python verified_cases.py

跑完會印三件事：
  1. 每個 case 的金額對齊（vs target）+ 該 case 觸發的規則違規
  2. Coverage matrix：每條規則被觸發幾次、零觸發的規則有哪些
  3. Result 欄位中「無專屬公式規則守護」的欄位（只受 sums_consistent 約束的）

若任何 case 違規 / 任一規則破損 / verified_by 名單漂移 → exit 1。

新增案例流程：
  1. 從打卡紀錄讀取出勤資料
  2. 用 calculate_salary() 計算
  3. 與實際薪資比對，必要時設定 tolerance + tolerance_reason
  4. 通過後加入 CASES 清單

新增 tolerance>0 必須在 TOLERANCE_REASONS 登記 swap 點，否則啟動驗證會 raise。
"""

from dataclasses import dataclass, field
from typing import Optional

from salary_calculator import calculate_salary, AttendanceRecord, SalaryResult
from employee_configs import CONFIGS_BY_NAME
from rules import RULES, evaluate, validate_verified_by


# ──────────────────────────────────────────────────────────────
# Tolerance reasons：每筆 tolerance > 0 必須對得回一個 swap 點
# ──────────────────────────────────────────────────────────────
TOLERANCE_REASONS = {}


@dataclass
class Case:
    name: str
    month: str
    target: int
    attendance: dict
    notes: str = ""
    tolerance: int = 0
    tolerance_reason: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# 結果欄位 → 守護它的「公式規則」對照
#   個別收入/扣除欄位列出 *專屬公式規則*（不列 sums_consistent，否則所有欄位都會被它兜底，
#   失去「找出無公式守護欄位」的訊號）。
#   gross_income / total_deduction / net_salary 三個合計欄位的公式 *本身就是* sums_consistent，
#   所以該規則就是它們的專屬公式，列出來。
#   未列任何規則（[]）的欄位 → coverage matrix 末段自動標記為「無公式規則守護」。
# ──────────────────────────────────────────────────────────────
FIELD_FORMULA_RULES = {
    "base_pay":               ["base_duty_formula"],
    "duty_pay":               ["base_duty_formula"],
    "other_pay":              ["daily_work_allowance"],
    "position_pay":           ["annual_leave_no_deduct", "position_proration"],
    "full_attendance_bonus":  ["annual_leave_no_deduct"],          # 條件覆蓋
    "holiday_overtime_pay":   ["holiday_ot_rounding"],
    "overtime_pay_1":         ["overtime_base_240"],
    "overtime_pay_2":         ["overtime_base_240"],
    "night_shift_pay":        ["night_shift_compose"],
    "meal_allowance_pay":     ["meal_allowance_compose"],
    "festival_bonus":         ["festival_compose"],
    "labor_insurance_fee":    ["labor_insurance_formula"],
    "health_insurance_fee":   ["health_insurance_formula"],
    "pension_self":           ["pension_off", "pension_annual_leave_full", "pension_partial_ratio"],
    "welfare_deduction":      ["welfare_cap_and_exempt"],
    "meal_deduction":         ["meal_exempt"],                     # 條件覆蓋
    "gross_income":           ["sums_consistent"],
    "total_deduction":        ["sums_consistent"],
    "net_salary":             ["sums_consistent"],
}


# ──────────────────────────────────────────────────────────────
# 驗證案例定義
# ──────────────────────────────────────────────────────────────
CASES: list[Case] = [
    Case(
        name="王靖銘",
        month="2026-03",
        target=50375,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
        },
        notes="22天全勤, 無加班, 無便當. dwa=235 反推確認",
    ),
    Case(
        name="李世彬",
        month="2026-03",
        target=52116,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 19.5,
            "annual_leave_days": 2.5,
            "meal_count": 20,
        },
        notes="特休2.5天, 伙食20×15=300",
    ),
    Case(
        name="許清輝",
        month="2026-03",
        target=36233,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "overtime_hours_1": 18.5,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        notes="特休1天, 加班18.5hr全前段, pension=True ratio=1.0（ROUND_HALF_UP 已修正）",
    ),
    Case(
        name="許柏凱",
        month="2026-03",
        target=34262,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 22,
        },
        notes="22天全勤, 無加班, dep=2",
    ),
    Case(
        name="陳姿惠",
        month="2026-03",
        target=33800,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
        },
        notes="22天全勤, meal_exempt=True",
    ),
    Case(
        name="林義明",
        month="2026-03",
        target=36687,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        notes="特休1天, 驗證特休不扣全勤/職務加給",
    ),
    Case(
        name="劉英美",
        month="2026-03",
        target=30718,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 21,
        },
        notes="特休1天, pension=False",
    ),
    Case(
        name="鄧志展",
        month="2026-03",
        target=90106,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "holiday_overtime_days": 4.0,
            "overtime_hours_1": 50.0,
            "overtime_hours_2": 60.0,
            "meal_count": 0,
        },
        notes="前段50hr+後段60hr, 假日加班4天=9802, meal_exempt, pension自提6%",
    ),
    Case(
        name="陳沛思",
        month="2026-03",
        target=34150,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 0,
        },
        notes="22天全勤, welfare_exempt=True(家族), 無便當",
    ),
    Case(
        name="莊明燦",
        month="2026-03",
        target=30359,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.5,
            "annual_leave_days": 0.5,
            "meal_count": 22,
        },
        notes="特休0.5天, 勞保=0(免繳), pension自提6% base=30300",
    ),
    Case(
        name="黃郁愛",
        month="2026-03",
        target=33800,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 0,
        },
        notes="22天全勤, 無加班, 無便當",
    ),
    Case(
        name="許連灯",
        month="2026-03",
        target=32046,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 20,
        },
        notes="特休1天, pension=False. 截圖實領30205含特殊扣除1841(勞退健保自付)",
    ),
    Case(
        name="王淑如",
        month="2026-03",
        target=31324,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 22,
        },
        notes="22天全勤, pension自提6%=1908",
    ),
    Case(
        name="許天賜",
        month="2026-03",
        target=41980,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 18.5,
            "annual_leave_days": 3.5,
            "meal_count": 18,
        },
        notes="特休3.5天, base=16350, dep=0（ROUND_HALF_UP 已修正）",
    ),
    Case(
        name="陳佩欣",
        month="2026-03",
        target=27888,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 13,
        },
        notes="特休1天, duty=2000, dep=1",
    ),
    Case(
        name="吳慧娟",
        month="2026-03",
        target=32563,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 19.0,
            "annual_leave_days": 3.0,
            "meal_count": 0,
        },
        notes="特休3天. 截圖實領31975含特殊扣588(勞退健保自付)（ROUND_HALF_UP 已修正）",
    ),
    Case(
        name="莊志成",
        month="2026-03",
        target=63377,
        attendance={
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "holiday_overtime_days": 3.0,
            "overtime_hours_1": 44.0,
            "overtime_hours_2": 44.0,
            "meal_count": 0,
        },
        notes="dwa=95, 夜班250×25, 伙食100×25, 前段44hr+後段44hr, 假日3天. 截圖實領53377含代扣互展10000",
    ),
]


# ──────────────────────────────────────────────────────────────
# 啟動驗證：tolerance 歸因 + verified_by 名單漂移
# ──────────────────────────────────────────────────────────────
def _validate_tolerances() -> list[str]:
    problems = []
    for c in CASES:
        if c.tolerance > 0:
            if c.tolerance_reason is None:
                problems.append(f"case '{c.name}' tolerance={c.tolerance} 缺 tolerance_reason")
            elif c.tolerance_reason not in TOLERANCE_REASONS:
                problems.append(
                    f"case '{c.name}' tolerance_reason='{c.tolerance_reason}' "
                    f"未在 TOLERANCE_REASONS 登記"
                )
        elif c.tolerance == 0 and c.tolerance_reason is not None:
            problems.append(
                f"case '{c.name}' tolerance=0 卻有 tolerance_reason，請刪掉"
            )
    return problems


def _startup_checks() -> list[str]:
    problems = []
    problems += _validate_tolerances()
    problems += validate_verified_by({c.name for c in CASES})
    return problems


# ──────────────────────────────────────────────────────────────
# 執行驗證 + coverage matrix
# ──────────────────────────────────────────────────────────────
def run_all(verbose: bool = False) -> bool:
    """
    跑所有 case + 規則不變式 + coverage matrix。
    回傳：全部 case 通過 AND 無任何規則破損 AND 啟動驗證通過。
    """
    # ── 啟動驗證 ──
    startup = _startup_checks()
    if startup:
        print("啟動驗證失敗：")
        for p in startup:
            print(f"  ✗ {p}")
        return False

    passed = 0
    failed = 0
    rule_violations = 0
    rule_apply_count: dict[str, int] = {r.id: 0 for r in RULES}
    rule_apply_cases: dict[str, list[str]] = {r.id: [] for r in RULES}
    case_rule_count: dict[str, int] = {}

    for case in CASES:
        config = CONFIGS_BY_NAME[case.name]

        att_kwargs = {
            "year": 2026,
            "month": int(case.month.split("-")[1]),
            **case.attendance,
        }
        att = AttendanceRecord(**att_kwargs)
        result = calculate_salary(config, att)

        diff = abs(result.net_salary - case.target)
        value_ok = diff <= case.tolerance

        outcomes = evaluate(config, att, result)
        violations = [(o.rule_id, o.violation) for o in outcomes if o.applied and o.violation]
        rule_ok = len(violations) == 0
        ok = value_ok and rule_ok

        # coverage 累積
        applied_here = [o.rule_id for o in outcomes if o.applied]
        case_rule_count[case.name] = len(applied_here)
        for rid in applied_here:
            rule_apply_count[rid] += 1
            rule_apply_cases[rid].append(case.name)

        if ok:
            passed += 1
            mark = "✓"
        else:
            failed += 1
            mark = "✗"

        tol_note = f" (tol={case.tolerance}: {case.tolerance_reason})" if case.tolerance else ""
        print(f"  {mark} {case.name}: {result.net_salary:.0f} vs {case.target} "
              f"(diff={result.net_salary - case.target:+.0f}){tol_note}")

        if violations:
            rule_violations += len(violations)
            for rid, msg in violations:
                print(f"      ⚠ rule '{rid}': {msg}")

        if verbose and not ok:
            result.print_detail()

    # ── 結果摘要 ──
    print(f"\n  結果: {passed} 通過, {failed} 失敗 (共 {len(CASES)} 案例)")
    print(f"  規則: {len(RULES)} 條, 破損 {rule_violations} 次")

    # ── Coverage matrix ──
    print(f"\n{'─'*50}")
    print("  Coverage matrix")
    print(f"{'─'*50}")

    print("\n  規則觸發次數（applies=True 的 case 數）:")
    zero_trigger = []
    for rule in RULES:
        cnt = rule_apply_count[rule.id]
        kind_tag = "S" if rule.kind == "semantic" else "T"
        mark = "  " if cnt > 0 else "⚠ "
        if cnt == 0:
            zero_trigger.append(rule.id)
        sample = ", ".join(rule_apply_cases[rule.id][:3])
        if len(rule_apply_cases[rule.id]) > 3:
            sample += f", +{len(rule_apply_cases[rule.id]) - 3}"
        print(f"    {mark}[{kind_tag}] {rule.id:<32} {cnt:2d} / {len(CASES)}  {sample}")

    if zero_trigger:
        print(f"\n  ⚠ 零觸發規則（無 case 證明它有作用）: {', '.join(zero_trigger)}")
        print("     → 該規則可能是死規則，或缺對應 case；ISSUES.md 候選項。")

    # ── 結果欄位無專屬公式規則 ──
    uncovered_fields = [f for f, rules_list in FIELD_FORMULA_RULES.items() if not rules_list]
    if uncovered_fields:
        print(f"\n  ⚠ 無公式規則的欄位（僅受 sums_consistent 兜底）: {', '.join(uncovered_fields)}")
        print("     → 若該欄位算錯且金額仍能配平，目前無法被獨立規則攔下。")

    print()
    return failed == 0 and rule_violations == 0


if __name__ == "__main__":
    print("=" * 50)
    print("  薪資計算引擎 — 回歸測試")
    print("=" * 50)
    success = run_all(verbose=True)
    if not success:
        exit(1)
