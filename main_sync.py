"""
主控同步程式
============
員工設定 來自 employee_configs.py（唯一權威源，版本控管於 Python）。
出勤 / 便當 來自 Google Sheets。計算結果寫回 Sheets。

執行流程：
  1. 載入員工設定（Python）
  2. 從「月出勤」讀取出勤資料
  3. 從「便當訂購」讀取便當份數
  4. 校驗出勤（姓名比對 + 值域檢查）→ 計算薪資
  5. 將薪資明細寫回「薪資結算」

用法：
  python main_sync.py --year 2026 --month 3
  python main_sync.py --dry-run               # 只計算不寫回
"""

import argparse
import datetime

from sheets_client import connect, read_all, write_rows
from salary_calculator import SalaryConfig, AttendanceRecord, calculate_salary, SalaryResult
from employee_configs import EMPLOYEE_CONFIGS

# ──────────────────────────────────────────────────────────────
# Google Sheets 設定
# ──────────────────────────────────────────────────────────────
SHEET_URL = "https://docs.google.com/spreadsheets/d/1s_Q1BrR-TcOF00vSyR0kPp0jVKuzeq85UfoDB2JS928/edit"
CREDENTIALS_FILE = "service_account.json"

TAB_ATTENDANCE = "月出勤"
TAB_MEAL       = "便當訂購"
TAB_SALARY_OUT = "薪資結算"


# ──────────────────────────────────────────────────────────────
# Header 驗證（schema drift → fail loud，不再 silently 0 賠錢）
# ──────────────────────────────────────────────────────────────
ATTENDANCE_HEADER_KEYWORDS = [
    "姓名", "曆日", "工作日", "實際出勤", "假日加班", "週日加班",
    "1.33", "1.66", "事假", "病假", "無薪", "特休", "全勤", "節金",
]


def _col_letter(idx: int) -> str:
    # 0→A, 1→B, ..., 25→Z, 26→AA 略
    return chr(ord("A") + idx) if idx < 26 else f"col{idx+1}"


def _validate_header(header_row, expected_keywords, sheet_name):
    """每個預期關鍵字必須以 substring 形式出現在對應欄的 header；否則 raise。"""
    if len(header_row) < len(expected_keywords):
        raise ValueError(
            f"{sheet_name}: header 僅 {len(header_row)} 欄，預期 ≥ {len(expected_keywords)} 欄"
        )
    for i, kw in enumerate(expected_keywords):
        cell = (header_row[i] or "").strip()
        if kw not in cell:
            raise ValueError(
                f"{sheet_name}: 第 {i+1} 欄 ({_col_letter(i)}) 預期含 '{kw}'，實際為 '{cell}'；"
                f"若 Sheet 欄位順序已變動，請同步更新 {sheet_name} 的讀取邏輯。"
            )


def load_attendance(ws, year: int, month: int) -> dict[str, AttendanceRecord]:
    """
    讀取「月出勤」工作表。

    欄位對應（第 1 列為表頭）：
      A: 姓名  B: 曆日數  C: 工作日  D: 實際出勤  E: 假日加班日(六)
      F: 週日加班日  G: 加班時數(1.33)  H: 加班時數(1.66)
      I: 事假日  J: 病假日  K: 無薪假日  L: 特休日
      M: 請假次數(扣全勤)  N: 有節金(Y/N)

    欄位若漂移 → header 驗證直接 raise，不再 silently 讀到 0。
    """
    rows = read_all(ws)
    if not rows:
        raise ValueError("月出勤: 空白工作表")
    _validate_header(rows[0], ATTENDANCE_HEADER_KEYWORDS, "月出勤")
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
# 出勤資料校驗（姓名比對 + 值域檢查；[錯誤] 開頭即中止）
# ──────────────────────────────────────────────────────────────
def validate_attendance(configs: list[SalaryConfig],
                        attendances: dict[str, AttendanceRecord]) -> list[str]:
    """回傳訊息列表；含 `[錯誤]` 前綴者視為致命，由 run() 判斷是否中止。"""
    messages: list[str] = []
    config_names = {c.name for c in configs}
    att_names = set(attendances.keys())

    # 姓名比對：configs 多出 → 有人漏填出勤；attendance 多出 → 姓名打錯或該人不在 config
    missing_att = config_names - att_names
    extra_att = att_names - config_names
    if missing_att:
        messages.append(f"[警告] 員工無出勤記錄：{', '.join(sorted(missing_att))}")
    if extra_att:
        messages.append(f"[錯誤] 出勤表有不明姓名（typo 或未登錄員工）：{', '.join(sorted(extra_att))}")

    # 值域檢查
    for name, att in attendances.items():
        if not (28 <= att.calendar_days <= 31):
            messages.append(f"[錯誤] {name} 曆日={att.calendar_days}（應 28-31）")
        if not (0 <= att.work_days <= att.calendar_days):
            messages.append(f"[錯誤] {name} 工作日={att.work_days}（應 ≤ 曆日 {att.calendar_days}）")
        if att.actual_work_days < 0 or att.actual_work_days > att.work_days:
            messages.append(f"[警告] {name} 實際出勤={att.actual_work_days}（工作日={att.work_days}）")
        if att.overtime_hours_1 < 0 or att.overtime_hours_2 < 0:
            messages.append(f"[錯誤] {name} 加班時數為負數")
        if att.holiday_overtime_days < 0 or att.sunday_overtime_days < 0:
            messages.append(f"[錯誤] {name} 假日/週日加班日為負數")

    return messages


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

    # 1. 員工設定：Python 為唯一權威源
    configs = EMPLOYEE_CONFIGS
    print(f"[1/4] 員工設定：{len(configs)} 位（來源：employee_configs.py）")

    client = connect(CREDENTIALS_FILE)

    # 2. 讀取出勤
    print("[2/4] 讀取出勤記錄 ...")
    attendances = load_attendance(_open_tab(client, TAB_ATTENDANCE), year, month)
    print(f"  {len(attendances)} 筆出勤")

    # 3. 讀取便當
    print("[3/4] 讀取便當訂購 ...")
    meal_counts = load_meal_counts(_open_tab(client, TAB_MEAL))
    print(f"  {len(meal_counts)} 筆便當")

    # 3.5 校驗出勤資料（姓名比對 + 值域）→ 致命錯誤直接中止
    msgs = validate_attendance(configs, attendances)
    for m in msgs:
        print(f"  {m}")
    if any(m.startswith("[錯誤]") for m in msgs):
        print("\n  出勤資料有致命錯誤，中止計算。請修正 Sheet 後重試。")
        return []

    # 4. 計算薪資
    print("[4/4] 計算薪資 ...")
    results = []
    for config in configs:
        att = attendances.get(config.name)
        if not att:
            continue  # 非致命：前面 validate 已警告
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
