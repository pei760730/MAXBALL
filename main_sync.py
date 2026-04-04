"""
主控同步程式
============
Claude Code ↔ Google Sheets 雙向同步

執行流程：
  1. 從 Google Sheets「便當訂購表」讀取當月打勾記錄
  2. 計算每人便當費用
  3. 從「員工設定表」讀取薪資核定資料
  4. 從「出勤記錄表」讀取出勤資料
  5. 計算每人當月薪資（含便當扣款）
  6. 將薪資明細結果寫回「薪資計算表」

用法：
  python main_sync.py                          # 自動抓今年今月
  python main_sync.py --year 2026 --month 3   # 指定年月
  python main_sync.py --dry-run               # 只計算不寫回 Sheets
"""

import argparse
import datetime
from dataclasses import dataclass

from sheets_client import connect, open_sheet_by_url, read_all, write_rows, update_cell
from meal_tracker import parse_meal_sheet, summarize, print_summary, MEAL_PRICE_NORMAL, MEAL_PRICE_VEG
from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary, SalaryResult

# ──────────────────────────────────────────────────────────────
# Google Sheets URL 設定（請替換成你的 Sheet URL）
# ──────────────────────────────────────────────────────────────
SHEET_URL = "https://docs.google.com/spreadsheets/d/你的SHEET_ID/edit"

# 各工作表名稱（依你的 Google Sheet 分頁名稱填寫）
TAB_MEAL       = "便當訂購"    # 每月便當打勾表
TAB_EMPLOYEE   = "員工設定"    # 薪資核定資料（固定，不常變動）
TAB_ATTENDANCE = "出勤記錄"    # 每月出勤輸入
TAB_SALARY_OUT = "薪資明細"    # 計算結果輸出（程式自動寫入）

CREDENTIALS_FILE = "service_account.json"


# ──────────────────────────────────────────────────────────────
# 從 Google Sheets 讀取員工設定
# ──────────────────────────────────────────────────────────────
def load_employee_configs(ws) -> list[SalaryConfig]:
    """
    讀取「員工設定」工作表，回傳 SalaryConfig 清單。

    工作表格式（第 1 列為表頭）：
      A: 員工編號 | B: 姓名 | C: 本薪 | D: 職務津貼 | E: 其他加給
      F: 全勤獎金 | G: 勞保投保薪資 | H: 健保投保薪資 | I: 退休金投保薪資
      J: 自提退休金(Y/N)
    """
    rows = read_all(ws)
    configs = []
    for row in rows[1:]:  # 跳過表頭
        if not row or not row[0].strip():
            continue
        try:
            configs.append(SalaryConfig(
                employee_id=row[0].strip(),
                name=row[1].strip(),
                base_salary=_to_float(row[2]),
                duty_allowance=_to_float(row[3]),
                other_allowance=_to_float(row[4]),
                full_attendance_bonus=_to_float(row[5]),
                labor_insurance_base=_to_float(row[6]),
                health_insurance_base=_to_float(row[7]),
                pension_base=_to_float(row[8]),
                pension_self_contribute=row[9].strip().upper() == "Y" if len(row) > 9 else False,
            ))
        except (IndexError, ValueError) as e:
            print(f"[警告] 員工資料讀取錯誤（列 {row}）：{e}")
    return configs


def load_attendance_records(ws, year: int, month: int) -> dict[str, AttendanceRecord]:
    """
    讀取「出勤記錄」工作表，回傳以姓名為 key 的 AttendanceRecord dict。

    工作表格式（第 1 列為表頭）：
      A: 姓名 | B: 曆日數 | C: 工作日 | D: 實際出勤日 | E: 假日加班日
      F: 加班時數(1.33) | G: 加班時數(1.66) | H: 無薪假 | I: 病假 | J: 事假
      K: 特休 | L: 有節金(Y/N)
    """
    rows = read_all(ws)
    records = {}
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        name = row[0].strip()
        try:
            records[name] = AttendanceRecord(
                year=year,
                month=month,
                calendar_days=int(_to_float(row[1])),
                work_days=int(_to_float(row[2])),
                actual_work_days=_to_float(row[3]),
                holiday_overtime_days=_to_float(row[4]) if len(row) > 4 else 0.0,
                overtime_hours_1=_to_float(row[5]) if len(row) > 5 else 0.0,
                overtime_hours_2=_to_float(row[6]) if len(row) > 6 else 0.0,
                unpaid_leave_days=_to_float(row[7]) if len(row) > 7 else 0.0,
                sick_leave_days=_to_float(row[8]) if len(row) > 8 else 0.0,
                personal_leave_days=_to_float(row[9]) if len(row) > 9 else 0.0,
                annual_leave_days=_to_float(row[10]) if len(row) > 10 else 0.0,
                has_festival_bonus=row[11].strip().upper() == "Y" if len(row) > 11 else False,
            )
        except (IndexError, ValueError) as e:
            print(f"[警告] 出勤資料讀取錯誤（{name}）：{e}")
    return records


# ──────────────────────────────────────────────────────────────
# 將薪資結果寫回 Google Sheets
# ──────────────────────────────────────────────────────────────
def write_salary_results(ws, results: list[SalaryResult], year: int, month: int):
    """
    將計算結果寫入「薪資明細」工作表。
    每次執行會先寫入表頭，再依序寫入每位員工的明細。
    """
    header = [
        "年度", "月份", "姓名",
        "本薪", "職務津貼", "其他加給", "全勤獎金",
        "假日加班費", "延時加班(1.33)", "延時加班(1.66)", "節金",
        "應領合計",
        "勞保費", "健保費", "退休金自提", "便當費", "扣除合計",
        "實領薪資",
    ]
    rows_to_write = [header]
    for r in results:
        rows_to_write.append([
            year, month, r.name,
            r.base_pay, r.duty_pay, r.other_pay, r.full_attendance_bonus,
            r.holiday_overtime_pay, r.overtime_pay_1, r.overtime_pay_2, r.festival_bonus,
            r.gross_income,
            r.labor_insurance_fee, r.health_insurance_fee, r.pension_self, r.meal_deduction,
            r.total_deduction,
            r.net_salary,
        ])
    ws.clear()
    write_rows(ws, rows_to_write, start_row=1)
    print(f"[完成] 已將 {len(results)} 筆薪資明細寫入「薪資明細」工作表")


# ──────────────────────────────────────────────────────────────
# 工具函式
# ──────────────────────────────────────────────────────────────
def _to_float(value: str) -> float:
    """將字串轉為 float，移除逗號與空白。"""
    return float(str(value).replace(",", "").replace(" ", "") or 0)


def _open_tab(client, tab_name: str):
    """用分頁名稱開啟工作表。"""
    import gspread
    spreadsheet = client.open_by_url(SHEET_URL)
    return spreadsheet.worksheet(tab_name)


# ──────────────────────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────────────────────
def run(year: int, month: int, dry_run: bool = False):
    """
    主同步流程。

    Args:
        year: 處理年度
        month: 處理月份
        dry_run: True = 只計算，不寫回 Google Sheets
    """
    print(f"\n{'='*60}")
    print(f"  MAXBALL 薪資同步系統  {year}年{month}月")
    print(f"  便當單價：普通 {MEAL_PRICE_NORMAL} 元／素食 {MEAL_PRICE_VEG} 元")
    print(f"  模式：{'試算（不寫回）' if dry_run else '正式執行（寫回 Sheets）'}")
    print(f"{'='*60}\n")

    # 1. 連線 Google Sheets
    print("[1/5] 連線 Google Sheets ...")
    client = connect(CREDENTIALS_FILE)

    # 2. 讀取便當訂購表
    print("[2/5] 讀取便當訂購表 ...")
    meal_ws   = _open_tab(client, TAB_MEAL)
    meal_rows = read_all(meal_ws)
    meal_records = parse_meal_sheet(meal_rows, header_rows=1)
    meal_summary = summarize(meal_records)
    print_summary(meal_summary, year, month)

    # 3. 讀取員工設定
    print("[3/5] 讀取員工薪資設定 ...")
    emp_ws  = _open_tab(client, TAB_EMPLOYEE)
    configs = load_employee_configs(emp_ws)
    print(f"      讀取到 {len(configs)} 位員工設定")

    # 4. 讀取出勤記錄
    print("[4/5] 讀取出勤記錄 ...")
    att_ws     = _open_tab(client, TAB_ATTENDANCE)
    attendances = load_attendance_records(att_ws, year, month)
    print(f"      讀取到 {len(attendances)} 筆出勤記錄")

    # 5. 計算薪資
    print("[5/5] 計算薪資 ...")
    meal_by_name = {r.name: r for r in meal_summary["records"]}
    results = []
    for config in configs:
        attendance = attendances.get(config.name)
        if not attendance:
            print(f"      [略過] {config.name}：無出勤記錄")
            continue
        meal = meal_by_name.get(config.name)
        result = calculate_salary(config, attendance, meal)
        result.print_detail()
        results.append(result)

    # 6. 寫回薪資明細（除非 dry_run）
    if not dry_run:
        print("[寫回] 將薪資明細寫入 Google Sheets ...")
        salary_ws = _open_tab(client, TAB_SALARY_OUT)
        write_salary_results(salary_ws, results, year, month)

        # 同步便當合計回便當表
        print("[寫回] 同步便當合計至便當訂購表 ...")
        from meal_tracker import write_summary_to_sheet
        write_summary_to_sheet(meal_ws, meal_summary)
    else:
        print("\n[試算模式] 未寫回 Google Sheets")

    print(f"\n{'='*60}")
    print(f"  完成！共處理 {len(results)} 位員工")
    print(f"  全廠便當費合計：{meal_summary['total_cost']:,} 元")
    net_total = sum(r.net_salary for r in results)
    print(f"  全廠實領薪資合計：{net_total:,.0f} 元")
    print(f"{'='*60}\n")

    return results, meal_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAXBALL 薪資便當同步系統")
    now = datetime.date.today()
    parser.add_argument("--year",    type=int, default=now.year,  help="年度（預設本年）")
    parser.add_argument("--month",   type=int, default=now.month, help="月份（預設本月）")
    parser.add_argument("--dry-run", action="store_true",          help="試算模式，不寫回 Sheets")
    args = parser.parse_args()
    run(args.year, args.month, args.dry_run)
