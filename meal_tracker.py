"""
便當訂購追蹤模組

功能：
- 讀取 Google Sheets 上的便當訂購明細表
- 統計每位員工每月訂購次數
- 計算每位員工的便當費用
- 支援普通便當 / 素食便當 / 不訂（X 或空白）
- 將統計結果寫回 Google Sheets

Google Sheets 格式（便當訂購表）：
  A欄: 員工姓名
  B欄起: 第1天、第2天 ... 第31天
  最後欄: 合計（可由程式自動寫入）

儲存格標記說明：
  "V" 或 "v" 或 "✓"  → 普通便當
  "素" 或 "S" 或 "s" → 素食便當
  "X" 或 "x" 或 ""   → 不訂
"""

import calendar
from dataclasses import dataclass, field
from sheets_client import connect, open_sheet_by_url, read_all, write_rows, update_cell


# 便當單價設定
MEAL_PRICE_NORMAL = 70   # 普通便當每份價格（元）
MEAL_PRICE_VEG    = 70   # 素食便當每份價格（元）


@dataclass
class EmployeeMealRecord:
    """單一員工的便當訂購記錄"""
    name: str
    normal_count: int = 0   # 普通便當天數
    veg_count: int = 0      # 素食便當天數
    daily: list = field(default_factory=list)  # 每天的狀態 ('normal', 'veg', 'none')

    @property
    def total_count(self) -> int:
        return self.normal_count + self.veg_count

    @property
    def total_cost(self) -> int:
        return self.normal_count * MEAL_PRICE_NORMAL + self.veg_count * MEAL_PRICE_VEG

    def __str__(self):
        return (
            f"{self.name}: 普通 {self.normal_count} 次, "
            f"素食 {self.veg_count} 次, "
            f"合計 {self.total_count} 次, "
            f"費用 {self.total_cost} 元"
        )


def _parse_cell(value: str) -> str:
    """
    解析單一儲存格標記，回傳 'normal' / 'veg' / 'none'。
    """
    v = value.strip().lower()
    if v in ("v", "✓", "√", "ˇ"):
        return "normal"
    if v in ("素", "s"):
        return "veg"
    return "none"


def parse_meal_sheet(rows: list[list[str]], header_rows: int = 1) -> list[EmployeeMealRecord]:
    """
    解析從 Google Sheets 讀回的二維資料，回傳員工訂購記錄清單。

    Args:
        rows: read_all() 傳回的二維 list。
        header_rows: 表頭列數（預設 1，跳過後才是員工資料）。

    Returns:
        list[EmployeeMealRecord]
    """
    records = []
    for row in rows[header_rows:]:
        if not row or not row[0].strip():
            continue  # 跳過空列

        name = row[0].strip()
        # 第 2 欄起為每天資料，最後一欄可能是「合計」，先全部讀入再過濾
        day_cells = row[1:]

        record = EmployeeMealRecord(name=name)
        for cell in day_cells:
            status = _parse_cell(cell)
            record.daily.append(status)
            if status == "normal":
                record.normal_count += 1
            elif status == "veg":
                record.veg_count += 1

        records.append(record)
    return records


def summarize(records: list[EmployeeMealRecord]) -> dict:
    """
    產生月度統計摘要。

    Returns:
        {
            "records": [...],          # EmployeeMealRecord 清單
            "total_normal": int,       # 全廠普通便當總份數
            "total_veg": int,          # 全廠素食便當總份數
            "total_cost": int,         # 全廠總費用
            "per_employee": {          # 每人費用 dict
                "姓名": cost, ...
            }
        }
    """
    total_normal = sum(r.normal_count for r in records)
    total_veg    = sum(r.veg_count    for r in records)
    total_cost   = sum(r.total_cost   for r in records)
    per_employee = {r.name: r.total_cost for r in records}

    return {
        "records": records,
        "total_normal": total_normal,
        "total_veg": total_veg,
        "total_cost": total_cost,
        "per_employee": per_employee,
    }


def print_summary(summary: dict, year: int, month: int):
    """列印月度便當統計至終端機。"""
    print(f"\n{'='*50}")
    print(f"  {year} 年 {month} 月  便當訂購統計")
    print(f"{'='*50}")
    for r in summary["records"]:
        print(f"  {r}")
    print(f"{'-'*50}")
    print(f"  全廠普通便當：{summary['total_normal']} 份")
    print(f"  全廠素食便當：{summary['total_veg']} 份")
    print(f"  全廠總費用　：{summary['total_cost']} 元")
    print(f"{'='*50}\n")


def write_summary_to_sheet(worksheet, summary: dict, start_row: int = 2, total_col_index: int = 33):
    """
    將統計合計回寫到 Google Sheets。
    - 在每個員工的「合計」欄位填入當月訂購次數。
    - 在「費用」欄位填入費用（若有此欄）。

    Args:
        worksheet: gspread Worksheet 物件。
        summary: summarize() 回傳的摘要 dict。
        start_row: 員工資料起始列（1-based）。
        total_col_index: 合計欄的欄位索引（1-based，預設 33 = AG 欄）。
    """
    for i, record in enumerate(summary["records"]):
        row = start_row + i
        update_cell(worksheet, row, total_col_index, record.total_count)


def run(sheet_url: str, year: int, month: int,
        credentials_file: str = "service_account.json",
        worksheet_index: int = 0):
    """
    主執行流程：讀取 → 計算 → 列印 → 回寫。

    Args:
        sheet_url: 便當訂購 Google Sheet 的 URL。
        year: 年份（例如 2026）。
        month: 月份（例如 3）。
        credentials_file: Service Account JSON 路徑。
        worksheet_index: 工作表索引。

    Returns:
        summary dict
    """
    client    = connect(credentials_file)
    worksheet = open_sheet_by_url(client, sheet_url, worksheet_index)
    rows      = read_all(worksheet)

    records = parse_meal_sheet(rows, header_rows=1)
    summary = summarize(records)
    print_summary(summary, year, month)
    write_summary_to_sheet(worksheet, summary)

    return summary


# ---------- 單機測試（不連 Google Sheets）----------
def demo():
    """用範例資料示範解析結果（不需要 Google Sheets 帳號）。"""
    # 模擬 2026 年 3 月的資料（簡化為 5 天）
    sample_rows = [
        # header
        ["姓名", "1", "2", "3", "4", "5", "合計"],
        # 員工資料
        ["李世彬",  "V",  "V",  "V",  "X",  "V",  ""],
        ["王淑如",  "V",  "V",  "V",  "V",  "V",  ""],
        ["謝金萬",  "V",  "X",  "V",  "V",  "X",  ""],
        ["劉英美",  "素",  "素",  "素",  "素",  "素",  ""],
        ["阮玉松",  "",   "",   "",   "",   "",   ""],  # 全月未訂
    ]

    records = parse_meal_sheet(sample_rows, header_rows=1)
    summary = summarize(records)
    print_summary(summary, 2026, 3)
    return summary


if __name__ == "__main__":
    demo()
