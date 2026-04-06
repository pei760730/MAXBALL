"""讀取所有 Google Sheets 工作表並存為 JSON（在本地電腦執行）"""
import gspread, json
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1s_Q1BrR-TcOF00vSyR0kPp0jVKuzeq85UfoDB2JS928/edit"

creds = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(SHEET_URL)

all_data = {}
for ws in spreadsheet.worksheets():
    print(f"讀取: {ws.title} ...")
    all_data[ws.title] = ws.get_all_values()

with open("sheets_data.json", "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"\n完成！已存到 sheets_data.json")
print(f"共 {len(all_data)} 個工作表")
for name, data in all_data.items():
    print(f"  {name}: {len(data)} 列 x {len(data[0]) if data else 0} 欄")
