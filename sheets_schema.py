"""
Google Sheets 分頁結構初始化
============================
第一次使用時執行此程式，會自動在你的 Google Sheet 建立 4 個分頁，
並填入正確的欄位表頭，讓你直接開始輸入資料。

執行方式：
  python sheets_schema.py

注意：執行前請先在 main_sync.py 中設定正確的 SHEET_URL。
"""

from main_sync import SHEET_URL, CREDENTIALS_FILE
from sheets_client import connect, write_rows

# ──────────────────────────────────────────────────────────────
# 各分頁的欄位表頭定義（與 main_sync.py 讀取邏輯完全對應）
# ──────────────────────────────────────────────────────────────

# 分頁 1：員工設定（薪資核定，17 欄 A-Q）
#   對應 main_sync.load_employee_configs() 的讀取順序
EMPLOYEE_HEADER = [[
    "員工編號",           # A
    "姓名",               # B
    "本薪(月)",           # C
    "職務津貼(月)",       # D
    "其他加給(固定)",     # E
    "職務加給(月)",       # F
    "全勤獎金",           # G
    "出勤加給/天",        # H  daily_work_allowance
    "夜班津貼/天",        # I  night_shift_daily
    "伙食津貼/天",        # J  meal_allowance_daily
    "勞保投保薪資",       # K
    "健保投保薪資",       # L
    "健保眷屬數",         # M
    "退休金投保薪資",     # N
    "自提退休金(Y/N)",    # O
    "不扣便當(Y/N)",      # P  meal_exempt
    "不扣福利金(Y/N)",    # Q  welfare_exempt
]]

EMPLOYEE_EXAMPLE = [
    ["005", "王靖銘", 16350, 7950, 2850, 17850, 1600, 235, 0, 0,
     45800, 45800, 0, 45800, "N", "N", "N"],
    ["011", "鄧志展", 16350, 7950, 2850, 17850, 1600, 260, 0, 0,
     45800, 60800, 0, 60800, "Y", "Y", "N"],
]

# 分頁 2：出勤記錄（每月填寫，14 欄 A-N）
#   對應 main_sync.load_attendance() 的讀取順序
ATTENDANCE_HEADER = [[
    "姓名",               # A
    "曆日數",             # B
    "工作日數",           # C
    "實際出勤日數",       # D
    "假日加班日(六)",     # E  holiday_overtime_days
    "週日加班日",         # F  sunday_overtime_days
    "加班時數(1.33倍)",   # G  overtime_hours_1
    "加班時數(1.66倍)",   # H  overtime_hours_2
    "事假日數",           # I  personal_leave_days
    "病假日數",           # J  sick_leave_days
    "無薪假日數",         # K  unpaid_leave_days
    "特休日數",           # L  annual_leave_days
    "請假次數(扣全勤)",   # M  leave_instances
    "有節金(Y/N)",        # N  has_festival_bonus
]]

ATTENDANCE_EXAMPLE = [
    ["王靖銘", 31, 22, 22.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, "N"],
    ["鄧志展", 31, 22, 22.0, 4.0, 0, 50, 60, 0, 0, 0, 0, 0, "N"],
]

# 分頁 3：便當訂購（每月填寫，欄位 B 起為每天）
MEAL_HEADER = [
    ["姓名"] + [str(d) for d in range(1, 32)] + ["合計"]
]

MEAL_EXAMPLE = [
    ["王靖銘"] + ["V"] * 22 + [""] * 9 + ["22"],
    ["鄧志展"] + [""] * 31 + ["0"],  # meal_exempt，但仍可列出
]

MEAL_NOTE = [[
    "※ 標記說明：V 或 v = 普通便當 | 素 或 S = 素食便當 | X 或空白 = 不訂",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
]]

# 分頁 4：薪資結算（程式自動寫入，22 欄）
#   對應 main_sync.write_salary_results() 的輸出順序
SALARY_HEADER = [[
    "年度", "月份", "姓名",
    "本薪", "職務津貼", "其他加給", "職務加給",
    "全勤獎金", "假日加班費", "延時加班(1.33)", "延時加班(1.66)",
    "夜班津貼", "伙食津貼", "節金",
    "應領合計",
    "勞保費", "健保費", "退休金自提", "福利金", "便當費",
    "扣除合計", "實領薪資",
]]


# ──────────────────────────────────────────────────────────────
# 建立分頁
# ──────────────────────────────────────────────────────────────
def _get_or_create_tab(spreadsheet, tab_name: str):
    """取得已有的分頁，或建立新分頁。"""
    existing = [ws.title for ws in spreadsheet.worksheets()]
    if tab_name in existing:
        print(f"  [已存在] {tab_name}（跳過建立）")
        return spreadsheet.worksheet(tab_name)
    ws = spreadsheet.add_worksheet(title=tab_name, rows=100, cols=40)
    print(f"  [新建立] {tab_name}")
    return ws


def setup_all_tabs(with_examples: bool = True):
    """
    建立所有分頁並填入表頭（與範例資料）。

    Args:
        with_examples: True = 同時填入範例員工資料（方便測試）
    """
    print("\n連線 Google Sheets ...")
    client = connect(CREDENTIALS_FILE)
    spreadsheet = client.open_by_url(SHEET_URL)

    print("建立分頁結構 ...")

    # 員工設定（17 欄）
    ws_emp = _get_or_create_tab(spreadsheet, "員工設定")
    ws_emp.clear()
    data = EMPLOYEE_HEADER + (EMPLOYEE_EXAMPLE if with_examples else [])
    write_rows(ws_emp, data, start_row=1)

    # 月出勤（14 欄）
    ws_att = _get_or_create_tab(spreadsheet, "月出勤")
    ws_att.clear()
    data = ATTENDANCE_HEADER + (ATTENDANCE_EXAMPLE if with_examples else [])
    write_rows(ws_att, data, start_row=1)

    # 便當訂購
    ws_meal = _get_or_create_tab(spreadsheet, "便當訂購")
    ws_meal.clear()
    data = MEAL_NOTE + MEAL_HEADER + (MEAL_EXAMPLE if with_examples else [])
    write_rows(ws_meal, data, start_row=1)

    # 薪資結算（22 欄，程式自動寫入）
    ws_sal = _get_or_create_tab(spreadsheet, "薪資結算")
    ws_sal.clear()
    write_rows(ws_sal, SALARY_HEADER, start_row=1)

    print("\n完成！分頁結構：")
    print("  員工設定  → 17 欄（A-Q），固定薪資核定資料")
    print("  月出勤    → 14 欄（A-N），每月出勤/加班/請假")
    print("  便當訂購  → 每天打勾（V/素/X）")
    print("  薪資結算  → 22 欄，程式自動計算寫入")
    if with_examples:
        print("\n  ※ 已填入範例資料，確認格式後請替換為真實員工資料")


if __name__ == "__main__":
    setup_all_tabs(with_examples=True)
