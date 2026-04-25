"""
薪資計算不變式（executable invariants）
====================================
每條規則 = 對 (SalaryConfig, AttendanceRecord, SalaryResult) 的可執行斷言
           + 一個 `applies` 前置條件 + 首次驗證它的 case 名單。

verified_cases 在每個 case 跑完 calculate_salary 後逐條檢查；
規則破損 = engine 偏離已沉澱語義 → CI 擋。

兩類規則：

  SEMANTIC（語義不變式）
    獨立斷言 ── 與引擎不共用算術、不重算金額。例：「未自提 → pension_self == 0」。
    這類最有保護力，是規則層的本職。

  STRUCTURAL（結構性契約）
    重算引擎輸出來確認組成 ── 主要抓「engine 改動 helper 但忘了同步」。
    與 case 數值斷言部分重疊，但能在新增員工沒有 case target 時提供保險。

新增規則流程：
  1. 從 case 發現新語義／新欄位
  2. 寫 applies + check
  3. 跑全部 case 確認新規則不誤殺舊案例
  4. coverage matrix 會在每次回歸自動印出觸發次數，零觸發即死規則。
"""

from dataclasses import dataclass
from typing import Callable, Optional, List, Tuple

from salary_calculator import (
    SalaryConfig, AttendanceRecord, SalaryResult, _r, health_insurance_fee,
)
from constants import (
    OVERTIME_DIVISOR, OVERTIME_RATE_FRONT, OVERTIME_RATE_BACK,
    HOLIDAY_OT_FRONT_HOURS, HOLIDAY_OT_BACK_HOURS,
    PENSION_SELF_RATE, WELFARE_RATE, WELFARE_CAP,
)


Predicate = Callable[[SalaryConfig, AttendanceRecord, SalaryResult], Optional[str]]
Applies   = Callable[[SalaryConfig, AttendanceRecord, SalaryResult], bool]


@dataclass
class Rule:
    id: str
    kind: str               # "semantic" | "structural"
    describe: str
    applies: Applies
    check: Predicate
    verified_by: List[str]


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
# SEMANTIC ── 與引擎獨立的語義斷言
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
    return _ok(
        r.full_attendance_bonus == c.full_attendance_bonus
        and r.position_pay == _r(c.position_allowance),
        f"annual leave should not deduct: full={r.full_attendance_bonus} "
        f"(exp {c.full_attendance_bonus}), pos={r.position_pay} (exp {_r(c.position_allowance)})",
    )


def _pension_off_applies(c, a, r):
    return not c.pension_self_contribute


def _pension_off(c, a, r):
    return _ok(r.pension_self == 0,
               f"pension should be 0 when opted out: got {r.pension_self}")


def _pension_full_applies(c, a, r):
    if not c.pension_self_contribute:
        return False
    effective = a.actual_work_days + a.annual_leave_days
    return effective >= a.work_days


def _pension_annual_leave_full(c, a, r):
    exp = _r(c.pension_base * PENSION_SELF_RATE)
    return _ok(r.pension_self == exp,
               f"pension with annual leave should be full ratio: got {r.pension_self}, exp {exp}")


def _meal_exempt_applies(c, a, r):
    return c.meal_exempt


def _meal_exempt(c, a, r):
    return _ok(r.meal_deduction == 0,
               f"meal_exempt but meal_deduction={r.meal_deduction}")


def _welfare_applies(c, a, r):
    return True   # 福利金每張單都該被驗（exempt 與 cap 兩邊都包含）


def _welfare_cap_and_exempt(c, a, r):
    if c.welfare_exempt:
        return _ok(r.welfare_deduction == 0,
                   f"welfare_exempt but got {r.welfare_deduction}")
    exp = min(WELFARE_CAP, _r(r.gross_income * WELFARE_RATE))
    return _ok(r.welfare_deduction == exp,
               f"welfare broken: got {r.welfare_deduction}, exp {exp}")


# ──────────────────────────────────────────────────────────────
# STRUCTURAL ── engine 組成契約（會重算金額，當 helper 漂移時擋下）
# ──────────────────────────────────────────────────────────────

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
    # 等於斷言「engine 沒繞過 helper」，不是獨立公式驗證。
    # 健保局查表 vs 公式差 ±1 元 → verified_cases 以 tolerance_reason 處理。
    exp = health_insurance_fee(c)
    return _ok(r.health_insurance_fee == exp,
               f"health insurance broken: got {r.health_insurance_fee}, exp {exp}")


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
    # SEMANTIC
    Rule("annual_leave_no_deduct", "semantic",
         "特休不扣全勤獎金、不扣職務加給",
         _annual_leave_applies, _annual_leave_no_deduct,
         ["林義明#18"]),
    Rule("pension_off", "semantic",
         "未自提退休金 → pension_self == 0",
         _pension_off_applies, _pension_off,
         ["劉英美#39"]),
    Rule("pension_annual_leave_full", "semantic",
         "退休金自提：特休視為出勤，effective_days≥work_days → ratio=1.0",
         _pension_full_applies, _pension_annual_leave_full,
         ["許清輝#10"]),
    Rule("meal_exempt", "semantic",
         "meal_exempt=True 永不扣便當費，無論 meal_count 多少",
         _meal_exempt_applies, _meal_exempt,
         ["陳姿惠#14", "鄧志展#11", "莊明燦#19"]),
    Rule("welfare_cap_and_exempt", "semantic",
         "福利金 = min(應領 × 1%, 350)；welfare_exempt → 0",
         _welfare_applies, _welfare_cap_and_exempt,
         ["陳沛思#16"]),

    # STRUCTURAL
    Rule("base_duty_formula", "structural",
         "本薪/職務津貼 = 月額 ÷ 30 × 曆日，不受任何請假影響",
         _always, _base_duty_formula,
         ["許柏凱#13", "林義明#18", "劉英美#39"]),
    Rule("overtime_base_240", "structural",
         "加班時薪 = (本薪+職務津貼+其他加給固定+全勤+職務加給) ÷ 240",
         _overtime_applies, _overtime_base_240,
         ["鄧志展#11"]),
    Rule("holiday_ot_rounding", "structural",
         "假日加班費 = _r(hourly × (1.33×前段時數+1.66×後段時數) × 天數)",
         _holiday_ot_applies, _holiday_ot_rounding,
         ["鄧志展#11"]),
    Rule("daily_work_allowance", "structural",
         "其他加給 = 固定加給 + (actual + holiday_ot) × dwa",
         _always, _daily_work_allowance,
         ["王靖銘#5", "許柏凱#13"]),
    Rule("health_insurance_formula", "structural",
         "健保費 = 投保薪資 × 5.17% × (1+眷屬) × 30%（查表可能差 ±1 元）",
         _always, _health_insurance_formula,
         ["鄧志展#11", "許清輝#10"]),
    Rule("night_shift_compose", "structural",
         "夜班津貼 = night_shift_daily × (actual + holiday_ot + sunday_ot)",
         _night_shift_applies, _night_shift_compose,
         ["莊志成#45"]),
    Rule("meal_allowance_compose", "structural",
         "伙食津貼 = meal_allowance_daily × (actual + holiday_ot + sunday_ot)",
         _meal_allowance_applies, _meal_allowance_compose,
         ["莊志成#45"]),
    Rule("festival_compose", "structural",
         "節金 = duty_allowance（has_festival_bonus=True 時）",
         _festival_applies, _festival_compose,
         []),  # 尚無 case 觸發 — coverage matrix 會自動標 zero-trigger
    Rule("sums_consistent", "structural",
         "gross = Σ 收入；total_deduction = Σ 扣除；net = gross − total_deduction",
         _always, _sums_consistent,
         ["*"]),
]


# ──────────────────────────────────────────────────────────────
# 執行 / 驗證 / 自我檢查
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


def validate_verified_by(known_case_names: set) -> List[str]:
    """
    啟動時呼叫；驗證每條 rule 的 verified_by 名單都是已存在的 case 名稱
    （或 "*" 代表通用）。回傳違規訊息列表，空即通過。

    name 格式: "<姓名>" 或 "<姓名>#<id>"，比對前者部分。
    """
    problems = []
    for rule in RULES:
        for label in rule.verified_by:
            if label == "*":
                continue
            name = label.split("#", 1)[0]
            if name not in known_case_names:
                problems.append(f"rule '{rule.id}' verified_by '{label}': 未知 case '{name}'")
    return problems
