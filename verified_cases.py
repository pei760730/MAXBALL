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
from rules import RULES, check_all


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
        "tolerance": 0,  # ROUND_HALF_UP 已修正（原差 -1 為 Python 銀行家捨入）
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
    {
        "name": "鄧志展",
        "month": "2026-03",
        "target": 90106,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "holiday_overtime_days": 4.0,
            "overtime_hours_1": 50.0,
            "overtime_hours_2": 60.0,
            "meal_count": 0,
        },
        "notes": "前段50hr+後段60hr, 假日加班4天=9802, meal_exempt, pension自提6%",
    },
    {
        "name": "陳沛思",
        "month": "2026-03",
        "target": 34150,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 0,
        },
        "notes": "22天全勤, welfare_exempt=True(家族), 無便當",
    },
    {
        "name": "莊明燦",
        "month": "2026-03",
        "target": 30359,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.5,
            "annual_leave_days": 0.5,
            "meal_count": 22,
        },
        "notes": "特休0.5天, 勞保=0(免繳), pension自提6% base=30300",
    },
    {
        "name": "黃郁愛",
        "month": "2026-03",
        "target": 33800,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 0,
        },
        "notes": "22天全勤, 無加班, 無便當",
    },
    {
        "name": "許連灯",
        "month": "2026-03",
        "target": 32046,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 20,
        },
        "notes": "特休1天, pension=False. 截圖實領30205含特殊扣除1841(勞退健保自付)",
    },
    {
        "name": "王淑如",
        "month": "2026-03",
        "target": 31324,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "meal_count": 22,
        },
        "notes": "22天全勤, pension自提6%=1908",
    },
    {
        "name": "許天賜",
        "month": "2026-03",
        "target": 41980,
        "tolerance": 0,  # ROUND_HALF_UP 已修正（其他加給 .5 邊界）
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 18.5,
            "annual_leave_days": 3.5,
            "meal_count": 18,
        },
        "notes": "特休3.5天, base=16350, dep=0",
    },
    {
        "name": "陳佩欣",
        "month": "2026-03",
        "target": 27888,
        "tolerance": 1,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 21.0,
            "annual_leave_days": 1.0,
            "meal_count": 13,
        },
        "notes": "特休1天, duty=2000, dep=1; 殘差+1 為健保局查表 vs 公式差異（非捨入）",
    },
    {
        "name": "吳慧娟",
        "month": "2026-03",
        "target": 32563,
        "tolerance": 0,  # ROUND_HALF_UP 已修正（勞保 33300×2.5%=832.5 邊界）
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 19.0,
            "annual_leave_days": 3.0,
            "meal_count": 0,
        },
        "notes": "特休3天. 截圖實領31975含特殊扣588(勞退健保自付)",
    },
    {
        "name": "莊志成",
        "month": "2026-03",
        "target": 63377,
        "tolerance": 0,
        "attendance": {
            "calendar_days": 31, "work_days": 22,
            "actual_work_days": 22.0,
            "holiday_overtime_days": 3.0,
            "overtime_hours_1": 44.0,
            "overtime_hours_2": 44.0,
            "meal_count": 0,
        },
        "notes": "dwa=95, 夜班250×25, 伙食100×25, 前段44hr+後段44hr, 假日3天. 截圖實領53377含代扣互展10000",
    },
]


# ──────────────────────────────────────────────
# 執行驗證
# ──────────────────────────────────────────────
def run_all(verbose: bool = False) -> bool:
    """
    執行所有驗證案例 + 規則不變式檢查。
    回傳：全部 case 通過 AND 無任何規則破損。
    """
    passed = 0
    failed = 0
    rule_violations = 0

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
        value_ok = diff <= case["tolerance"]

        violations = check_all(config, att, result)
        rule_ok = len(violations) == 0
        ok = value_ok and rule_ok

        if ok:
            passed += 1
            mark = "✓"
        else:
            failed += 1
            mark = "✗"

        print(f"  {mark} {case['name']}: {result.net_salary:.0f} vs {case['target']} "
              f"(diff={result.net_salary - case['target']:+.0f}, tol={case['tolerance']})")

        if violations:
            rule_violations += len(violations)
            for rid, msg in violations:
                print(f"      ⚠ rule '{rid}': {msg}")

        if verbose and not ok:
            result.print_detail()

    print(f"\n  結果: {passed} 通過, {failed} 失敗 (共 {len(CASES)} 案例)")
    print(f"  規則不變式: {len(RULES)} 條, 破損 {rule_violations} 次")
    for rule in RULES:
        print(f"    - [{rule.id}] {rule.describe}")

    return failed == 0 and rule_violations == 0


if __name__ == "__main__":
    print("=" * 50)
    print("  薪資計算引擎 — 回歸測試")
    print("=" * 50)
    success = run_all(verbose=True)
    if not success:
        exit(1)
