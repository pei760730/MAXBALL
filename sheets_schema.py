"""
Google Sheets 分頁結構初始化
============================
第一次使用時執行此程式，會自動在你的 Google Sheet 建立 4 個分頁，
並填入正確的欄位表頭，讓你直接開始輸入資料。

執行方式：
  python sheets_schema.py

注意：執行前請先在 main_sync.py 中設定正確的 SHEET_URL。
"""

from main_sync import SHEET_URL, CREDENTIALS_FILE  # URL 已設定在 main_sync.py
from sheets_client import connect, write_rows

# ──────────────────────────────────────────────────────────────
# 各分頁的欄位表頭定義
# ──────────────────────────────────────────────────────────────

# 分頁 1：員工設定（薪資核定，固定資料）
EMPLOYEE_HEADER = [[
    "員工編號", "姓名",
    "本薪(月)", "職務津貼(月)", "其他加給(月)", "全勤獎金",
    "勞保投保薪資", "健保投保薪資", "退休金投保薪資",
    "自提退休金(Y/N)",
]]

EMPLOYEE_EXAMPLE = [
    ["001", "王小明", 27000, 13500, 7108, 1600, 45800, 60800, 60800, "Y"],
    ["002", "李小花", 25000, 12000, 5000, 1600, 40100, 53000, 53000, "N"],
]

# 分頁 2：出勤記錄（每月填寫）
ATTENDANCE_HEADER = [[
    "姓名",
    "曆日數", "工作日數", "實際出勤日數",
    "假日加班日(週六)", "加班時數(1.33倍)", "加班時數(1.66倍)",
    "無薪假日數", "病假日數", "事假日數", "特休日數",
    "有節金(Y/N)",
]]

ATTENDANCE_EXAMPLE = [
    ["王小明", 31, 22, 22.0, 2.0, 4, 2, 0, 0, 0, 0, "N"],
    ["李小花", 31, 22, 20.0, 0.0, 0, 0, 0, 1, 0, 0, "N"],
]

# 分頁 3：便當訂購（每月填寫，欄位 B 起為每天）
MEAL_HEADER = [
    ["姓名"] + [str(d) for d in range(1, 32)] + ["合計"]
]

MEAL_EXAMPLE = [
    ["王小明"] + ["V"] * 22 + [""] * 9 + ["22"],
    ["李小花"] + ["V"] * 20 + ["X"] * 2 + [""] * 9 + ["20"],
    ["陳阿花"] + ["素"] * 21 + [""] * 10 + ["21"],  # 素食便當
]

MEAL_NOTE = [[
    "※ 標記說明：V 或 v = 普通便當 | 素 或 S = 素食便當 | X 或空白 = 不訂",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "",
    "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""
]]

# 分頁 4：薪資明細（程式自動寫入，勿手動修改）
SALARY_HEADER = [[
    "年度", "月份", "姓名",
    "本薪", "職務津貼", "其他加給", "全勤獎金",
    "假日加班費", "延時加班(1.33)", "延時加班(1.66)", "節金",
    "應領合計",
    "勞保費", "健保費", "退休金自提", "便當費", "扣除合計",
    "實領薪資",
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

    # 員工設定（全員）
    ws_emp = _get_or_create_tab(spreadsheet, "員工設定")
    ws_emp.clear()
    data = EMPLOYEE_HEADER + (EMPLOYEE_EXAMPLE if with_examples else [])
    write_rows(ws_emp, data, start_row=1)

    # 月出勤（全員）
    ws_att = _get_or_create_tab(spreadsheet, "月出勤")
    ws_att.clear()
    data = ATTENDANCE_HEADER + (ATTENDANCE_EXAMPLE if with_examples else [])
    write_rows(ws_att, data, start_row=1)

    # 便當訂購（全員）
    ws_meal = _get_or_create_tab(spreadsheet, "便當訂購")
    ws_meal.clear()
    data = MEAL_NOTE + MEAL_HEADER + (MEAL_EXAMPLE if with_examples else [])
    write_rows(ws_meal, data, start_row=1)

    # 薪資結算（全員，程式自動寫入）
    ws_sal = _get_or_create_tab(spreadsheet, "薪資結算")
    ws_sal.clear()
    write_rows(ws_sal, SALARY_HEADER, start_row=1)

    print("\n完成！Google Sheets 分頁結構如下：")
    print("  ┌─────────────┬──────────────────────────────────────┐")
    print("  │ 分頁名稱    │ 說明                                 │")
    print("  ├─────────────┼──────────────────────────────────────┤")
    print("  │ 核定        │ 舊格式（鄧志展單人，保留不動）       │")
    print("  │ 出勤        │ 舊格式（鄧志展單人，保留不動）       │")
    print("  │ 明細        │ 舊格式（鄧志展單人，保留不動）       │")
    print("  │ 總表        │ 舊格式（鄧志展單人，保留不動）       │")
    print("  ├─────────────┼──────────────────────────────────────┤")
    print("  │ 員工設定 ★  │ 全員薪資核定資料（固定，不常變動）   │")
    print("  │ 月出勤   ★  │ 每月全員出勤輸入（事假/加班/特休）   │")
    print("  │ 便當訂購 ★  │ 每月打V/素/X（同現在的紙本表格）     │")
    print("  │ 薪資結算 ★  │ 自動計算輸出（程式寫入，勿手動改）   │")
    print("  └─────────────┴──────────────────────────────────────┘")
    print("  ★ = 新增分頁（舊分頁保留，不影響現有資料）")
    if with_examples:
        print("\n  ※ 已填入範例資料，確認格式後請替換為真實員工資料")
    print("\n下一步：")
    print("  1. 在「員工設定」填入全部員工薪資核定資料")
    print("  2. 每月初在「便當訂購」輸入打勾記錄（或月底彙整）")
    print("  3. 每月底在「出勤記錄」輸入出勤資料")
    print("  4. 執行：python main_sync.py --year 2026 --month 3")


if __name__ == "__main__":
    setup_all_tabs(with_examples=True)
