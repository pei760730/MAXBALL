"""讀取所有工作表資料以理解結構"""

from sheets_client import connect, open_sheet_by_url, read_all

SHEET_URL = "https://docs.google.com/spreadsheets/d/1s_Q1BrR-TcOF00vSyR0kPp0jVKuzeq85UfoDB2JS928/edit"


def main():
    client = connect("service_account.json")

    # 讀取所有四個工作表
    sheet_names = ["核定", "出勤", "明細", "總表"]

    for i, name in enumerate(sheet_names):
        print(f"\n{'='*60}")
        print(f"工作表 {i+1}: {name}")
        print(f"{'='*60}")

        try:
            ws = open_sheet_by_url(client, SHEET_URL, worksheet_index=i)
            data = read_all(ws)
            print(f"共 {len(data)} 列, {len(data[0]) if data else 0} 欄")
            print()
            for row_idx, row in enumerate(data):
                # Show all rows with row number
                display = [f"{cell}" for cell in row]
                print(f"  [{row_idx+1:3d}] {display}")
        except Exception as e:
            print(f"  錯誤: {e}")


if __name__ == "__main__":
    main()
