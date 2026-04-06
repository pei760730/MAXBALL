"""測試 Google Sheets 連線"""

from sheets_client import connect, open_sheet_by_url, read_all

SHEET_URL = "https://docs.google.com/spreadsheets/d/1s_Q1BrR-TcOF00vSyR0kPp0jVKuzeq85UfoDB2JS928/edit"

def main():
    print("正在連線 Google Sheets...")
    client = connect("service_account.json")

    print("正在開啟「MAX 薪資總表」...")
    # 讀取「核定」工作表（第一張，index=0）
    ws = open_sheet_by_url(client, SHEET_URL, worksheet_index=0)

    print(f"工作表名稱：{ws.title}")
    print(f"---")

    data = read_all(ws)
    print(f"共 {len(data)} 列資料：\n")
    for i, row in enumerate(data):
        # 過濾空值，顯示比較乾淨
        display = [cell for cell in row if cell]
        if display:
            print(f"  第 {i+1} 列: {display}")

    print("\n連線測試成功！")


if __name__ == "__main__":
    main()
