"""
薪資計算不變式（executable invariants）
====================================
每條規則 = 對 (SalaryConfig, AttendanceRecord, SalaryResult) 的可執行斷言
           + 一個 `applies` 前置條件。

規則 kind（三分；報告中以 I / M / C 顯示）：

  independent ── 與引擎不共用算術、不重抄公式。
                 例：「未自提 → pension_self == 0」、「meal_exempt → meal_deduction == 0」。
                 演算法錯誤時會獨立發聲，是規則層最有保護力的本職。

  mirror ──────  以與引擎相同的常數 / helper 重抄公式再 assert 相等。
                 只能擋「engine 改動但 helper 沒同步」這類漂移，
                 *無法* 攔截演算法本身錯誤（兩邊會一起錯、一起綠燈）。
                 真正的金額守門靠 verified_cases 的 target 比對；mirror 是輔助。

  composition ─ 合計關係（gross = Σ income；net = gross − deduction）。
                 不重算個別公式，只驗組成。任何欄位被破壞、且未同步調整其他欄位
                 都會被它擋下；mutation testing 的兜底守衛。

Coverage matrix（runtime）會：
  1. 印每條規則 applies=True 的 case 數（零觸發 = 死規則或漏 case）。
  2. 對每個 SalaryResult 數值欄位 +1 跑全部規則，列出 *非 composition* 的守衛。
     若某欄位無任何 independent / mirror 守衛 → 只剩 sums_consistent 兜底。

新增規則前先問：
  - 它與引擎是否共用 helper / 常數？若是 → 是 mirror，問是否值得新增。
  - 同一份保護是否 case 的 target 已能提供？若是 → 別新增。
  - 它與既有規則會不會同時炸？若是 → 信號重疊。

註：`verified_by` 名單已移除——這份資訊由 runtime coverage matrix derive，
   不該再以靜態 metadata 重複表達。
"""

from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple

from salary_calculator import (
    SalaryConfig, AttendanceRecord, SalaryResult, _r, health_insurance_fee,
)
from constants import (
    OVERTIME_DIVISOR, OVERTIME_RATE_FRONT, OVERTIME_RATE_BACK,
    HOLIDAY_OT_FRONT_HOURS, HOLIDAY_OT_BACK_HOURS,
    LABOR_INSURANCE_RATE, PENSION_SELF_RATE, WELFARE_RATE, WELFARE_CAP,
)


Predicate = Callable[[SalaryConfig, AttendanceRecord, SalaryResult], Optional[str]]
Applies   = Callable[[SalaryConfig, AttendanceRecord, SalaryResult], bool]

KIND_INDEPENDENT = "independent"
KIND_MIRROR      = "mirror"
KIND_COMPOSITION = "composition"
KIND_TAGS = {KIND_INDEPENDENT: "I", KIND_MIRROR: "M", KIND_COMPOSITION: "C"}


@dataclass
class Rule:
    id: str
    kind: str               # independent | mirror | composition
    describe: str
    applies: Applies
    check: Predicate


def _ok(cond: bool, msg: str) -> Optional[str]:
    return None if cond else msg


def _always(c, a, r) -> bool:
    return True


def _hourly_base(c: SalaryConfig) -> float:
    return (
        c.base_salary + c.duty_allowance + c.other_allowance
        + c.full_attendance_bonus + c.position_allowance
    ) / OVERTIME_DIVISOR


# ──────────────────────────────────────────────────────────────
# INDEPENDENT ── 不重抄公式；演算法錯誤時會獨立發聲
# ──────────────────────────────────────────────────────────────

def _annual_leave_applies(c, a, r):
    # 觸發：有特休、且 *沒有* 其他扣項（事假/病假/無薪假/扣全勤次數）。
    return (
        a.annual_leave_days > 0
        and a.personal_leave_days == 0
        and a.sick_leave_days == 0
        and a.unpaid_leave_days == 0
        and a.leave_instances == 0
    )


def _annual_leave_no_deduct(c, a, r):
    # 獨立斷言：特休不應改變全勤獎金、不應比例扣職務加給。
    return _ok(
        r.full_attendance_bonus == c.full_attendance_bonus
        and r.position_pay == _r(c.position_allowance),
        f"annual leave should not deduct: full={r.full_attendance_bonus} "
        f"(exp {c.full_attendance_bonus}), pos={r.position_pay} (exp {_r(c.position_allowance)})",
    )


def _pension_off_applies(c, a, r):
    return not c.pension_self_contribute


def _pension_off(c, a, r):
    # 獨立斷言：未自提 → 退休金自提欄為 0。不重算公式。
    return _ok(r.pension_self == 0,
               f"pension should be 0 when opted out: got {r.pension_self}")


def _meal_exempt_applies(c, a, r):
    return c.meal_exempt


def _meal_exempt(c, a, r):
    # 獨立斷言：meal_exempt → 便當扣款為 0，無論 meal_count 多少。
    return _ok(r.meal_deduction == 0,
               f"meal_exempt but meal_deduction={r.meal_deduction}")


# ──────────────────────────────────────────────────────────────
# MIRROR ── 重抄公式；擋 helper 漂移，不擋演算法錯誤
# ──────────────────────────────────────────────────────────────

def _pension_full_applies(c, a, r):
    if not c.pension_self_contribute:
        return False
    effective = a.actual_work_days + a.annual_leave_days
    return effective >= a.work_days


def _pension_annual_leave_full(c, a, r):
    exp = _r(c.pension_base * PENSION_SELF_RATE)
    return _ok(r.pension_self == exp,
               f"pension with annual leave should be full ratio: got {r.pension_self}, exp {exp}")


def _pension_partial_applies(c, a, r):
    if not c.pension_self_contribute:
        return False
    effective = a.actual_work_days + a.annual_leave_days
    return effective < a.work_days


def _pension_partial_ratio(c, a, r):
    effective = a.actual_work_days + a.annual_leave_days
    exp = _r(c.pension_base * PENSION_SELF_RATE * (effective / 30))
    return _ok(r.pension_self == exp,
               f"pension partial ratio broken: got {r.pension_self}, exp {exp}")


def _position_proration_applies(c, a, r):
    non_annual = a.personal_leave_days + a.sick_leave_days + a.unpaid_leave_days
    return non_annual > 0 and a.work_days > 0


def _position_proration(c, a, r):
    non_annual = a.personal_leave_days + a.sick_leave_days + a.unpaid_leave_days
    deduct = _r(c.position_allowance / a.work_days * non_annual)
    exp = _r(c.position_allowance - deduct)
    return _ok(r.position_pay == exp,
               f"position_pay proration broken: got {r.position_pay}, exp {exp}")


def _welfare_applies(c, a, r):
    return True   # 福利金每張單都該被驗（exempt 與 cap 兩邊都包含）


def _welfare_cap_and_exempt(c, a, r):
    if c.welfare_exempt:
        return _ok(r.welfare_deduction == 0,
                   f"welfare_exempt but got {r.welfare_deduction}")
    exp = min(WELFARE_CAP, _r(r.gross_income * WELFARE_RATE))
    return _ok(r.welfare_deduction == exp,
               f"welfare broken: got {r.welfare_deduction}, exp {exp}")


def _base_duty_formula(c, a, r):
    return _ok(
        r.base_pay == _r(c.base_salary / 30 * a.calendar_days)
        and r.duty_pay == _r(c.duty_allowance / 30 * a.calendar_days),
        f"base/duty prorate by calendar broken: base={r.base_pay}, duty={r.duty_pay}",
    )


def _overtime_applies(c, a, r):
    return a.overtime_hours_1 > 0 or a.overtime_hours_2 > 0


def _overtime_base_240(c, a, r):
    hourly = _hourly_base(c)
    exp_ot1 = _r(_r(hourly * OVERTIME_RATE_FRONT) * a.overtime_hours_1)
    exp_ot2 = _r(_r(hourly * OVERTIME_RATE_BACK) * a.overtime_hours_2)
    return _ok(
        r.overtime_pay_1 == exp_ot1 and r.overtime_pay_2 == exp_ot2,
        f"overtime divisor broken: ot1={r.overtime_pay_1} vs {exp_ot1}, "
        f"ot2={r.overtime_pay_2} vs {exp_ot2}",
    )


def _holiday_ot_applies(c, a, r):
    return a.holiday_overtime_days > 0


def _holiday_ot_rounding(c, a, r):
    hourly = _hourly_base(c)
    exp = _r(
        hourly * (
            OVERTIME_RATE_FRONT * HOLIDAY_OT_FRONT_HOURS
            + OVERTIME_RATE_BACK * HOLIDAY_OT_BACK_HOURS
        ) * a.holiday_overtime_days
    )
    return _ok(r.holiday_overtime_pay == exp,
               f"holiday_ot rounding broken: got {r.holiday_overtime_pay}, exp {exp}")


def _daily_work_allowance(c, a, r):
    exp = _r(
        c.other_allowance
        + (a.actual_work_days + a.holiday_overtime_days) * c.daily_work_allowance
    )
    return _ok(r.other_pay == exp,
               f"other_pay formula broken: got {r.other_pay}, exp {exp}")


def _health_insurance_formula(c, a, r):
    # 引擎與規則共用 health_insurance_fee helper（單一 swap 點）。
    # 純 mirror — 擋 engine 沒呼叫 helper，不獨立驗證金額。
    # 健保局查表 vs 公式差 ±1 元 → verified_cases 以 tolerance_reason 處理。
    exp = health_insurance_fee(c)
    return _ok(r.health_insurance_fee == exp,
               f"health insurance broken: got {r.health_insurance_fee}, exp {exp}")


def _labor_insurance_formula(c, a, r):
    exp = _r(c.labor_insurance_base * LABOR_INSURANCE_RATE)
    return _ok(r.labor_insurance_fee == exp,
               f"labor insurance broken: got {r.labor_insurance_fee}, exp {exp}")


def _night_shift_applies(c, a, r):
    return c.night_shift_daily > 0


def _night_shift_compose(c, a, r):
    total = a.actual_work_days + a.holiday_overtime_days + a.sunday_overtime_days
    exp = _r(c.night_shift_daily * total)
    return _ok(r.night_shift_pay == exp,
               f"night_shift_pay broken: got {r.night_shift_pay}, exp {exp}")


def _meal_allowance_applies(c, a, r):
    return c.meal_allowance_daily > 0


def _meal_allowance_compose(c, a, r):
    total = a.actual_work_days + a.holiday_overtime_days + a.sunday_overtime_days
    exp = _r(c.meal_allowance_daily * total)
    return _ok(r.meal_allowance_pay == exp,
               f"meal_allowance_pay broken: got {r.meal_allowance_pay}, exp {exp}")


def _festival_applies(c, a, r):
    return a.has_festival_bonus


def _festival_compose(c, a, r):
    exp = c.duty_allowance
    return _ok(r.festival_bonus == exp,
               f"festival_bonus broken: got {r.festival_bonus}, exp {exp}")


# ──────────────────────────────────────────────────────────────
# COMPOSITION ── 合計關係；mutation testing 的兜底
# ──────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────
# 規則登記
# ──────────────────────────────────────────────────────────────
RULES: List[Rule] = [
    # INDEPENDENT
    Rule("annual_leave_no_deduct", KIND_INDEPENDENT,
         "特休不扣全勤獎金、不扣職務加給",
         _annual_leave_applies, _annual_leave_no_deduct),
    Rule("pension_off", KIND_INDEPENDENT,
         "未自提退休金 → pension_self == 0",
         _pension_off_applies, _pension_off),
    Rule("meal_exempt", KIND_INDEPENDENT,
         "meal_exempt=True 永不扣便當費，無論 meal_count 多少",
         _meal_exempt_applies, _meal_exempt),

    # MIRROR
    Rule("pension_annual_leave_full", KIND_MIRROR,
         "退休金自提：特休視為出勤，effective_days≥work_days → ratio=1.0",
         _pension_full_applies, _pension_annual_leave_full),
    Rule("pension_partial_ratio", KIND_MIRROR,
         "退休金自提：effective_days<work_days → ratio=effective/30",
         _pension_partial_applies, _pension_partial_ratio),
    Rule("position_proration", KIND_MIRROR,
         "事假/病假/無薪假按 work_days 比例扣職務加給（特休不扣）",
         _position_proration_applies, _position_proration),
    Rule("welfare_cap_and_exempt", KIND_MIRROR,
         "福利金 = min(應領 × 1%, 350)；welfare_exempt → 0",
         _welfare_applies, _welfare_cap_and_exempt),
    Rule("base_duty_formula", KIND_MIRROR,
         "本薪/職務津貼 = 月額 ÷ 30 × 曆日，不受任何請假影響",
         _always, _base_duty_formula),
    Rule("overtime_base_240", KIND_MIRROR,
         "加班時薪 = (本薪+職務津貼+其他加給固定+全勤+職務加給) ÷ 240",
         _overtime_applies, _overtime_base_240),
    Rule("holiday_ot_rounding", KIND_MIRROR,
         "假日加班費 = _r(hourly × (1.33×前段時數+1.66×後段時數) × 天數)",
         _holiday_ot_applies, _holiday_ot_rounding),
    Rule("daily_work_allowance", KIND_MIRROR,
         "其他加給 = 固定加給 + (actual + holiday_ot) × dwa",
         _always, _daily_work_allowance),
    Rule("health_insurance_formula", KIND_MIRROR,
         "健保費 = 投保薪資 × 5.17% × (1+眷屬) × 30%（查表可能差 ±1 元）",
         _always, _health_insurance_formula),
    Rule("labor_insurance_formula", KIND_MIRROR,
         "勞保費 = 投保薪資 × 2.5%；免繳者 base=0 → fee=0",
         _always, _labor_insurance_formula),
    Rule("night_shift_compose", KIND_MIRROR,
         "夜班津貼 = night_shift_daily × (actual + holiday_ot + sunday_ot)",
         _night_shift_applies, _night_shift_compose),
    Rule("meal_allowance_compose", KIND_MIRROR,
         "伙食津貼 = meal_allowance_daily × (actual + holiday_ot + sunday_ot)",
         _meal_allowance_applies, _meal_allowance_compose),
    Rule("festival_compose", KIND_MIRROR,
         "節金 = duty_allowance（has_festival_bonus=True 時）",
         _festival_applies, _festival_compose),

    # COMPOSITION
    Rule("sums_consistent", KIND_COMPOSITION,
         "gross = Σ 收入；total_deduction = Σ 扣除；net = gross − total_deduction",
         _always, _sums_consistent),
]


# ──────────────────────────────────────────────────────────────
# 執行 / 驗證
# ──────────────────────────────────────────────────────────────
@dataclass
class RuleOutcome:
    rule_id: str
    applied: bool
    violation: Optional[str]


def evaluate(config: SalaryConfig, attendance: AttendanceRecord,
             result: SalaryResult) -> List[RuleOutcome]:
    """跑所有規則；每條輸出 (id, 是否觸發, 違規訊息)。"""
    out: List[RuleOutcome] = []
    for rule in RULES:
        if rule.applies(config, attendance, result):
            msg = rule.check(config, attendance, result)
            out.append(RuleOutcome(rule.id, True, msg))
        else:
            out.append(RuleOutcome(rule.id, False, None))
    return out


def check_all(config: SalaryConfig, attendance: AttendanceRecord,
              result: SalaryResult) -> List[Tuple[str, str]]:
    """回傳 [(rule_id, violation_msg), ...]，空 list 代表全過（保留舊介面）。"""
    return [
        (o.rule_id, o.violation)
        for o in evaluate(config, attendance, result)
        if o.applied and o.violation
    ]
