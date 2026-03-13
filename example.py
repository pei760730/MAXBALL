"""使用範例 - 示範如何讀寫 Google Sheet"""

from sheets_client import (
    connect,
    open_sheet,
    open_sheet_by_url,
    read_all,
    read_as_dicts,
    write_row,
    write_rows,
    update_cell,
)


def main():
    # 1. 連線（請先將 service_account.json 放到專案根目錄）
    client = connect("service_account.json")

    # 2. 開啟 Google Sheet（二選一）
    # 方法 A：用名稱開啟
    ws = open_sheet(client, "你的Google Sheet名稱")

    # 方法 B：用 URL 開啟（取消註解下面這行，把上面那行註解掉）
    # ws = open_sheet_by_url(client, "https://docs.google.com/spreadsheets/d/你的SHEET_ID/edit")

    # ── 讀取範例 ──────────────────────────────────
    # 讀取全部資料（二維 list）
    all_data = read_all(ws)
    print("所有資料：")
    for row in all_data:
        print(row)

    # 讀取為 dict list（第一列當欄位名）
    records = read_as_dicts(ws)
    print("\n字典格式：")
    for record in records:
        print(record)

    # ── 寫入範例 ──────────────────────────────────
    # 追加一列到最後
    write_row(ws, ["王小明", 25, "台北"])

    # 寫入到指定列（第 2 列）
    write_row(ws, ["李小花", 30, "高雄"], row_number=2)

    # 批次寫入多列
    write_rows(ws, [
        ["張大衛", 28, "台中"],
        ["陳美麗", 22, "台南"],
    ])

    # 更新單一儲存格（第 1 列第 1 欄）
    update_cell(ws, 1, 1, "姓名")

    print("\n寫入完成！")


if __name__ == "__main__":
    main()
