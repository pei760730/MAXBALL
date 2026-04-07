"""
主控同步程式
============
Google Sheets ↔ 薪資計算引擎 雙向同步

執行流程：
  1. 從「員工設定」讀取薪資核定資料
  2. 從「月出勤」讀取出勤資料
  3. 從「便當訂購」讀取便當份數
  4. 計算每人當月薪資
  5. 將薪資明細寫回「薪資結算」

用法：
  python main_sync.py --year 2026 --month 3
  python main_sync.py --dry-run               # 只計算不寫回
"""

import argparse
import datetime

from sheets_client import connect, read_all, write_rows
from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary, SalaryResult

# ──────────────────────────────────────────────────────────────
# Google Sheets 設定
# ──────────────────────────────────────────────────────────────
SHEET_URL = "https://docs.google.com/spreadsheets/d/1s_Q1BrR-TcOF00vSyR0kPp0jVKuzeq85UfoDB2JS928/edit"
CREDENTIALS_FILE = "service_account.json"

TAB_EMPLOYEE   = "員工設定"
TAB_ATTENDANCE = "月出勤"
TAB_MEAL       = "便當訂購"
TAB_SALARY_OUT = "薪資結算"


# ──────────────────────────────────────────────────────────────
# 從 Sheets 讀取員工設定（完整 SalaryConfig）
# ──────────────────────────────────────────────────────────────
def load_employee_configs(ws) -> list[SalaryConfig]:
    """
    讀取「員工設定」工作表，回傳 SalaryConfig 清單。

    欄位對應（第 1 列為表頭）：
      A: 員工編號  B: 姓名  C: 本薪  D: 職務津貼  E: 其他加給(固定)
      F: 職務加給  G: 全勤獎金  H: 出勤加給/天  I: 夜班津貼/天  J: 伙食津貼/天
      K: 勞保投保  L: 健保投保  M: 健保眷屬數  N: 退休金投保
      O: 自提退休金(Y/N)  P: 不扣便當(Y/N)  Q: 不扣福利金(Y/N)
    """
    rows = read_all(ws)
    configs = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        try:
            configs.append(SalaryConfig(
                employee_id=row[0].strip(),
                name=row[1].strip(),
                base_salary=_float(row, 2),
                duty_allowance=_float(row, 3),
                other_allowance=_float(row, 4),
                position_allowance=_float(row, 5),
                full_attendance_bonus=_float(row, 6),
                daily_work_allowance=_float(row, 7),
                night_shift_daily=_float(row, 8),
                meal_allowance_daily=_float(row, 9),
                labor_insurance_base=_float(row, 10),
                health_insurance_base=_float(row, 11),
                health_dependents=int(_float(row, 12)),
                pension_base=_float(row, 13),
                pension_self_contribute=_yn(row, 14),
                meal_exempt=_yn(row, 15),
                welfare_exempt=_yn(row, 16),
            ))
        except (IndexError, ValueError) as e:
            print(f"  [警告] 員工資料讀取錯誤（{row[:2]}）：{e}")
    return configs


def load_attendance(ws, year: int, month: int) -> dict[str, AttendanceRecord]:
    """
    讀取「月出勤」工作表。

    欄位對應（第 1 列為表頭）：
      A: 姓名  B: 曆日數  C: 工作日  D: 實際出勤  E: 假日加班日(六)
      F: 週日加班日  G: 加班時數(1.33)  H: 加班時數(1.66)
      I: 事假日  J: 病假日  K: 無薪假日  L: 特休日
      M: 請假次數(扣全勤)  N: 有節金(Y/N)
    """
    rows = read_all(ws)
    records = {}
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        try:
            records[name] = AttendanceRecord(
                year=year, month=month,
                calendar_days=int(_float(row, 1)),
                work_days=int(_float(row, 2)),
                actual_work_days=_float(row, 3),
                holiday_overtime_days=_float(row, 4),
                sunday_overtime_days=_float(row, 5),
                overtime_hours_1=_float(row, 6),
                overtime_hours_2=_float(row, 7),
                personal_leave_days=_float(row, 8),
                sick_leave_days=_float(row, 9),
                unpaid_leave_days=_float(row, 10),
                annual_leave_days=_float(row, 11),
                leave_instances=int(_float(row, 12)),
                has_festival_bonus=_yn(row, 13),
            )
        except (IndexError, ValueError) as e:
            print(f"  [警告] 出勤資料讀取錯誤（{name}）：{e}")
    return records


def load_meal_counts(ws) -> dict[str, int]:
    """
    讀取「便當訂購」工作表，回傳 {姓名: 便當份數}。
    第 A 欄為姓名，B~AF 為每天標記（V/素/X），最後欄或自動加總。
    """
    rows = read_all(ws)
    counts = {}
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        count = 0
        for cell in row[1:]:
            v = cell.strip().lower()
            if v in ("v", "✓", "√", "ˇ", "素", "s"):
                count += 1
        counts[name] = count
    return counts


# ──────────────────────────────────────────────────────────────
# 寫回薪資結算
# ──────────────────────────────────────────────────────────────
def write_salary_results(ws, results: list[SalaryResult], year: int, month: int):
    """將計算結果寫入「薪資結算」工作表。"""
    header = [
        "年度", "月份", "姓名",
        "本薪", "職務津貼", "其他加給", "職務加給",
        "全勤獎金", "假日加班費", "延時加班(1.33)", "延時加班(1.66)",
        "夜班津貼", "伙食津貼", "節金",
        "應領合計",
        "勞保費", "健保費", "退休金自提", "福利金", "便當費",
        "扣除合計", "實領薪資",
    ]
    rows_to_write = [header]
    for r in results:
        rows_to_write.append([
            year, month, r.name,
            r.base_pay, r.duty_pay, r.other_pay, r.position_pay,
            r.full_attendance_bonus, r.holiday_overtime_pay,
            r.overtime_pay_1, r.overtime_pay_2,
            r.night_shift_pay, r.meal_allowance_pay, r.festival_bonus,
            r.gross_income,
            r.labor_insurance_fee, r.health_insurance_fee,
            r.pension_self, r.welfare_deduction, r.meal_deduction,
            r.total_deduction, r.net_salary,
        ])
    ws.clear()
    write_rows(ws, rows_to_write, start_row=1)
    print(f"  已寫入 {len(results)} 筆薪資明細")


# ──────────────────────────────────────────────────────────────
# 工具
# ──────────────────────────────────────────────────────────────
def _float(row: list, idx: int) -> float:
    if idx >= len(row):
        return 0.0
    return float(str(row[idx]).replace(",", "").replace(" ", "") or 0)

def _yn(row: list, idx: int) -> bool:
    if idx >= len(row):
        return False
    return str(row[idx]).strip().upper() == "Y"

def _open_tab(client, tab_name: str):
    spreadsheet = client.open_by_url(SHEET_URL)
    return spreadsheet.worksheet(tab_name)


# ──────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────
def run(year: int, month: int, dry_run: bool = False):
    print(f"\n{'='*50}")
    print(f"  MAXBALL 薪資系統  {year}年{month}月")
    print(f"  模式：{'試算' if dry_run else '正式（寫回 Sheets）'}")
    print(f"{'='*50}\n")

    client = connect(CREDENTIALS_FILE)

    # 1. 讀取員工設定
    print("[1/4] 讀取員工設定 ...")
    configs = load_employee_configs(_open_tab(client, TAB_EMPLOYEE))
    print(f"  {len(configs)} 位員工")

    # 2. 讀取出勤
    print("[2/4] 讀取出勤記錄 ...")
    attendances = load_attendance(_open_tab(client, TAB_ATTENDANCE), year, month)
    print(f"  {len(attendances)} 筆出勤")

    # 3. 讀取便當
    print("[3/4] 讀取便當訂購 ...")
    meal_counts = load_meal_counts(_open_tab(client, TAB_MEAL))
    print(f"  {len(meal_counts)} 筆便當")

    # 4. 計算薪資
    print("[4/4] 計算薪資 ...")
    results = []
    for config in configs:
        att = attendances.get(config.name)
        if not att:
            print(f"  [略過] {config.name}：無出勤記錄")
            continue
        # 注入便當份數到 attendance
        att.meal_count = meal_counts.get(config.name, 0)
        result = calculate_salary(config, att)
        result.print_detail()
        results.append(result)

    # 寫回
    if not dry_run:
        print("\n[寫回] 薪資結算 ...")
        write_salary_results(_open_tab(client, TAB_SALARY_OUT), results, year, month)

    net_total = sum(r.net_salary for r in results)
    print(f"\n{'='*50}")
    print(f"  完成：{len(results)} 位，實領合計 {net_total:,.0f} 元")
    print(f"{'='*50}\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAXBALL 薪資系統")
    now = datetime.date.today()
    parser.add_argument("--year",    type=int, default=now.year)
    parser.add_argument("--month",   type=int, default=now.month)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.year, args.month, args.dry_run)
