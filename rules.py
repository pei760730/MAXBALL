"""
薪資計算不變式（executable invariants）
====================================
每條規則 = 一段對 (SalaryConfig, AttendanceRecord, SalaryResult) 的語義約束
           + 首次驗證它的 case 名單。

verified_cases 在每個 case 跑完 calculate_salary 後逐條檢查。
規則破損 = engine 偏離已沉澱的語義 → CI 擋。

規則為什麼不只是把 engine 再寫一次：
  - 寫成不變式後，任何 engine 重構都要同時通過 17 個 case 值比對 + 全部規則語義比對，
    比單靠 case 數字更能抓到「剛好對一半」的回歸。
  - 規則可獨立顯示、可追溯到觸發 case、可當作新人理解 engine 的最短路徑。

新增規則流程：
  1. 從 case 發現新語義（通常是驗證誤差收斂後找到的）
  2. 寫成 predicate（純函數，無副作用）
  3. 附上首次驗證它的 case 名單
  4. 跑全部 case 確認新規則不誤殺舊案例
"""

from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple

from salary_calculator import SalaryConfig, AttendanceRecord, SalaryResult, _r
from constants import (
    OVERTIME_DIVISOR, OVERTIME_RATE_FRONT, OVERTIME_RATE_BACK,
    HEALTH_INSURANCE_RATE, HEALTH_EMPLOYEE_SHARE,
    PENSION_SELF_RATE, WELFARE_RATE, WELFARE_CAP,
)


Predicate = Callable[[SalaryConfig, AttendanceRecord, SalaryResult], Optional[str]]


@dataclass
class Rule:
    id: str
    describe: str
    check: Predicate
    verified_by: List[str]


def _ok(cond: bool, msg: str) -> Optional[str]:
    return None if cond else msg


def _hourly_base(c: SalaryConfig) -> float:
    return (
        c.base_salary + c.duty_allowance + c.other_allowance
        + c.full_attendance_bonus + c.position_allowance
    ) / OVERTIME_DIVISOR


# ── 規則定義 ────────────────────────────────────────────────

def _base_duty_formula(c, a, r):
    return _ok(
        r.base_pay == _r(c.base_salary / 30 * a.calendar_days)
        and r.duty_pay == _r(c.duty_allowance / 30 * a.calendar_days),
        f"base/duty prorate by calendar broken: base={r.base_pay}, duty={r.duty_pay}",
    )


def _annual_leave_no_deduct(c, a, r):
    # 觸發條件：沒有事/病/無薪假，也沒有扣全勤次數。
    # 特休本身可以有，不影響 full attendance / position。
    has_non_annual = (
        a.personal_leave_days > 0
        or a.sick_leave_days > 0
        or a.unpaid_leave_days > 0
        or a.leave_instances > 0
    )
    if has_non_annual:
        return None
    return _ok(
        r.full_attendance_bonus == c.full_attendance_bonus
        and r.position_pay == _r(c.position_allowance),
        f"annual leave should not deduct: full={r.full_attendance_bonus} "
        f"(exp {c.full_attendance_bonus}), pos={r.position_pay} (exp {_r(c.position_allowance)})",
    )


def _pension_annual_leave_full(c, a, r):
    if not c.pension_self_contribute:
        return None
    effective = a.actual_work_days + a.annual_leave_days
    if effective < a.work_days:
        return None
    return _ok(
        r.pension_self == _r(c.pension_base * PENSION_SELF_RATE),
        f"pension with annual leave should be full ratio: got {r.pension_self}, "
        f"exp {_r(c.pension_base * PENSION_SELF_RATE)}",
    )


def _pension_off(c, a, r):
    if c.pension_self_contribute:
        return None
    return _ok(
        r.pension_self == 0,
        f"pension should be 0 when opted out: got {r.pension_self}",
    )


def _overtime_base_240(c, a, r):
    hourly = _hourly_base(c)
    exp_ot1 = _r(_r(hourly * OVERTIME_RATE_FRONT) * a.overtime_hours_1)
    exp_ot2 = _r(_r(hourly * OVERTIME_RATE_BACK) * a.overtime_hours_2)
    return _ok(
        r.overtime_pay_1 == exp_ot1 and r.overtime_pay_2 == exp_ot2,
        f"overtime divisor broken: ot1={r.overtime_pay_1} vs {exp_ot1}, "
        f"ot2={r.overtime_pay_2} vs {exp_ot2}",
    )


def _meal_exempt(c, a, r):
    if not c.meal_exempt:
        return None
    return _ok(
        r.meal_deduction == 0,
        f"meal_exempt but meal_deduction={r.meal_deduction}",
    )


def _daily_work_allowance(c, a, r):
    exp = _r(
        c.other_allowance
        + (a.actual_work_days + a.holiday_overtime_days) * c.daily_work_allowance
    )
    return _ok(r.other_pay == exp, f"other_pay formula broken: got {r.other_pay}, exp {exp}")


def _holiday_ot_rounding(c, a, r):
    hourly = _hourly_base(c)
    exp = _r(
        hourly * (OVERTIME_RATE_FRONT * 2 + OVERTIME_RATE_BACK * 6)
        * a.holiday_overtime_days
    )
    return _ok(
        r.holiday_overtime_pay == exp,
        f"holiday_ot rounding broken: got {r.holiday_overtime_pay}, exp {exp}",
    )


def _health_insurance_formula(c, a, r):
    # 註：此為公式值；健保局查表可能差 ±1 元，verified_cases 以 tolerance 處理。
    exp = _r(
        c.health_insurance_base * HEALTH_INSURANCE_RATE
        * (1 + c.health_dependents) * HEALTH_EMPLOYEE_SHARE
    )
    return _ok(
        r.health_insurance_fee == exp,
        f"health insurance formula broken: got {r.health_insurance_fee}, exp {exp}",
    )


def _welfare_cap_and_exempt(c, a, r):
    if c.welfare_exempt:
        return _ok(r.welfare_deduction == 0, f"welfare_exempt but got {r.welfare_deduction}")
    exp = min(WELFARE_CAP, _r(r.gross_income * WELFARE_RATE))
    return _ok(
        r.welfare_deduction == exp,
        f"welfare broken: got {r.welfare_deduction}, exp {exp}",
    )


def _sums_consistent(c, a, r):
    gross = (
        r.base_pay + r.duty_pay + r.other_pay + r.position_pay
        + r.full_attendance_bonus + r.holiday_overtime_pay
        + r.overtime_pay_1 + r.overtime_pay_2
        + r.night_shift_pay + r.meal_allowance_pay + r.festival_bonus
    )
    total = (
        r.labor_insurance_fee + r.health_insurance_fee
        + r.pension_self + r.welfare_deduction + r.meal_deduction
    )
    if r.gross_income != gross:
        return f"gross mismatch: {r.gross_income} vs sum {gross}"
    if r.total_deduction != total:
        return f"total_deduction mismatch: {r.total_deduction} vs sum {total}"
    if r.net_salary != r.gross_income - r.total_deduction:
        return f"net mismatch: {r.net_salary} vs {r.gross_income - r.total_deduction}"
    return None


RULES: List[Rule] = [
    Rule("base_duty_formula",
         "本薪/職務津貼 = 月額 ÷ 30 × 曆日，不受任何請假影響",
         _base_duty_formula,
         ["許柏凱#13", "林義明#18", "劉英美#39"]),
    Rule("annual_leave_no_deduct",
         "特休不扣全勤獎金、不扣職務加給",
         _annual_leave_no_deduct,
         ["林義明#18"]),
    Rule("pension_annual_leave_full",
         "退休金自提：特休視為出勤，effective_days≥work_days → ratio=1.0",
         _pension_annual_leave_full,
         ["許清輝#10"]),
    Rule("pension_off",
         "未自提退休金 → pension_self == 0",
         _pension_off,
         ["劉英美#39"]),
    Rule("overtime_base_240",
         "加班時薪 = (本薪+職務津貼+其他加給固定+全勤+職務加給) ÷ 240",
         _overtime_base_240,
         ["鄧志展#11"]),
    Rule("meal_exempt",
         "meal_exempt=True 永不扣便當費，無論 meal_count 多少",
         _meal_exempt,
         ["陳姿惠#14", "鄧志展#11", "莊明燦#19"]),
    Rule("daily_work_allowance",
         "其他加給 = 固定加給 + (actual + holiday_ot) × dwa",
         _daily_work_allowance,
         ["王靖銘#5", "許柏凱#13"]),
    Rule("holiday_ot_rounding",
         "假日加班費 = _r(hourly × (1.33×2+1.66×6) × 天數)，不先 round 每天",
         _holiday_ot_rounding,
         ["鄧志展#11"]),
    Rule("health_insurance_formula",
         "健保費 = 投保薪資 × 5.17% × (1+眷屬) × 30%（查表可能差 ±1 元）",
         _health_insurance_formula,
         ["鄧志展#11", "許清輝#10"]),
    Rule("welfare_cap_and_exempt",
         "福利金 = min(應領 × 1%, 350)；welfare_exempt → 0",
         _welfare_cap_and_exempt,
         ["陳沛思#16"]),
    Rule("sums_consistent",
         "gross = Σ 收入項；total_deduction = Σ 扣除項；net = gross − total_deduction",
         _sums_consistent,
         ["*"]),
]


def check_all(config: SalaryConfig, attendance: AttendanceRecord,
              result: SalaryResult) -> List[Tuple[str, str]]:
    """跑所有規則；回傳 [(rule_id, violation_msg), ...]，空 list 代表全過。"""
    violations = []
    for rule in RULES:
        msg = rule.check(config, attendance, result)
        if msg:
            violations.append((rule.id, msg))
    return violations
