"""
已驗證薪資案例（回歸測試）+ 規則 coverage 自我檢查
=================================================
單一守門進入點：`python verified_cases.py`

跑完依序檢查：
  1. boundary self-test（不依賴 Google Sheets）
  2. tolerance 歸因驗證（每筆 tolerance>0 必須對得回 TOLERANCE_REASONS 的 swap 點）
  3. 17 個 case：金額 vs target、規則 0 破損
  4. Coverage matrix（runtime derived）：
     a. 每條規則 applies=True 的 case 數 + I/M/C 標籤；零觸發 = 死規則或漏 case
     b. 每個 SalaryResult 數值欄位的 mutation-based 守衛清單
        （只剩 sums_consistent 的欄位 = 真實覆蓋缺口）

任何環節失敗 → exit 1。

新增案例流程：
  1. 從打卡紀錄讀取出勤資料
  2. 用 calculate_salary() 計算
  3. 與實際薪資比對，必要時設定 tolerance + tolerance_reason
  4. 通過後加入 CASES 清單

新增 tolerance>0 必須在 TOLERANCE_REASONS 登記 swap 點，否則啟動驗證會 fail。
"""

from dataclasses import dataclass, fields
from typing import Optional

from salary_calculator import calculate_salary, AttendanceRecord, SalaryResult
from employee_configs import CONFIGS_BY_NAME
from rules import RULES, evaluate, KIND_COMPOSITION, KIND_TAGS
import boundary


# ──────────────────────────────────────────────────────────────
# Tolerance reasons：每筆 tolerance > 0 必須對得回一個 swap 點
#   接健保表後（salary_calculator.health_insurance_fee 改查表）原本陳佩欣 #16 的
#   tolerance=1 已收掉，目前 17/17 全部 exact，本字典為空。
#   未來若再出現 tolerance>0 的 case，必須先在這裡登記 swap 點，否則啟動驗證會 fail。
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
        notes="特休1天, duty=2000, dep=1（健保接表後 exact）",
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
# 啟動驗證
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


# ──────────────────────────────────────────────────────────────
# Mutation-based field guard derivation
#   對每個 SalaryResult 數值欄位 +1，跑所有規則；
#   聚合「哪條規則攔下了這個欄位的擾動」。
#   composition (sums_consistent) 會攔幾乎所有 mutation；
#   只有 composition 攔到的欄位 = 真實覆蓋缺口。
# ──────────────────────────────────────────────────────────────
def _numeric_result_fields() -> list[str]:
    return [f.name for f in fields(SalaryResult) if f.name != "name"]


def _derive_field_guards() -> dict[str, set[str]]:
    """回傳 {field_name -> set(rule_id) that catches +1 mutation in any case}."""
    guards: dict[str, set[str]] = {f: set() for f in _numeric_result_fields()}
    for case in CASES:
        config = CONFIGS_BY_NAME[case.name]
        att = AttendanceRecord(
            year=2026, month=int(case.month.split("-")[1]), **case.attendance,
        )
        baseline = calculate_salary(config, att)
        baseline_dict = baseline.__dict__.copy()

        for fname in _numeric_result_fields():
            current = baseline_dict[fname]
            if not isinstance(current, (int, float)):
                continue
            mutated = SalaryResult(**baseline_dict)
            setattr(mutated, fname, current + 1)
            for o in evaluate(config, att, mutated):
                if o.applied and o.violation:
                    guards[fname].add(o.rule_id)
            # 還原（這個 dict 是 copy 但保險起見）
            mutated = None
    return guards


# ──────────────────────────────────────────────────────────────
# 執行驗證 + coverage matrix
# ──────────────────────────────────────────────────────────────
def run_all(verbose: bool = False) -> bool:
    """
    跑所有 case + 規則不變式 + coverage matrix + boundary self-test。
    回傳：boundary OK AND 啟動驗證 OK AND 全部 case 通過 AND 無任何規則破損。
    """
    # ── boundary self-test ──
    print("[boundary]")
    try:
        boundary.selftest()
    except AssertionError as e:
        print(f"  ✗ {e}")
        return False

    # ── 啟動驗證 ──
    startup = _validate_tolerances()
    if startup:
        print("\n啟動驗證失敗：")
        for p in startup:
            print(f"  ✗ {p}")
        return False

    print()
    passed = 0
    failed = 0
    rule_violations = 0
    rule_apply_count: dict[str, int] = {r.id: 0 for r in RULES}
    rule_apply_cases: dict[str, list[str]] = {r.id: [] for r in RULES}

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
        for o in outcomes:
            if o.applied:
                rule_apply_count[o.rule_id] += 1
                rule_apply_cases[o.rule_id].append(case.name)

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

    # ── Coverage matrix：規則觸發次數 ──
    print(f"\n{'─'*50}")
    print("  Coverage matrix")
    print(f"{'─'*50}")

    print("\n  規則觸發次數（applies=True 的 case 數，I=independent / M=mirror / C=composition）:")
    zero_trigger = []
    for rule in RULES:
        cnt = rule_apply_count[rule.id]
        tag = KIND_TAGS[rule.kind]
        mark = "  " if cnt > 0 else "⚠ "
        if cnt == 0:
            zero_trigger.append(rule.id)
        sample = ", ".join(rule_apply_cases[rule.id][:3])
        if len(rule_apply_cases[rule.id]) > 3:
            sample += f", +{len(rule_apply_cases[rule.id]) - 3}"
        print(f"    {mark}[{tag}] {rule.id:<32} {cnt:2d} / {len(CASES)}  {sample}")

    if zero_trigger:
        print(f"\n  ⚠ 零觸發規則（無 case 證明它有作用）: {', '.join(zero_trigger)}")
        print("     → 該規則可能是死規則，或缺對應 case；ISSUES.md 候選項。")

    # ── Coverage matrix：欄位守衛（mutation-based） ──
    guards = _derive_field_guards()
    composition_only = []
    print("\n  欄位守衛（result 欄位 +1 時，會被攔下的非 composition 規則）:")
    for fname in _numeric_result_fields():
        non_comp = sorted(
            rid for rid in guards[fname]
            if next((r.kind for r in RULES if r.id == rid), None) != KIND_COMPOSITION
        )
        if non_comp:
            print(f"    {fname:<24} {', '.join(non_comp)}")
        else:
            comp = sorted(guards[fname])
            tag = "(無人攔)" if not comp else f"(僅 {', '.join(comp)})"
            print(f"  ⚠ {fname:<24} {tag}")
            composition_only.append(fname)

    if composition_only:
        print(f"\n  ⚠ 僅 composition 兜底的欄位: {', '.join(composition_only)}")
        print("     → 這些欄位若算錯且被另一欄位以反向誤差抵銷，無獨立規則攔下。")

    print()
    return failed == 0 and rule_violations == 0


if __name__ == "__main__":
    print("=" * 50)
    print("  薪資計算引擎 — 回歸測試（單一守門進入點）")
    print("=" * 50)
    success = run_all(verbose=True)
    if not success:
        exit(1)
