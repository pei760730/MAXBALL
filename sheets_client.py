"""Google Sheets 連線模組 - 提供讀寫 Google Sheets 的功能"""

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def connect(credentials_file: str = "service_account.json") -> gspread.Client:
    """使用 Service Account 連線到 Google Sheets。

    Args:
        credentials_file: Service Account JSON 金鑰檔案路徑。

    Returns:
        已認證的 gspread Client。
    """
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return gspread.authorize(creds)


def open_sheet(client: gspread.Client, spreadsheet_name: str, worksheet_index: int = 0):
    """開啟指定的 Google Sheet 工作表。

    Args:
        client: gspread Client。
        spreadsheet_name: Google Sheet 的名稱。
        worksheet_index: 工作表索引（預設第一張 = 0）。

    Returns:
        gspread Worksheet 物件。
    """
    spreadsheet = client.open(spreadsheet_name)
    return spreadsheet.get_worksheet(worksheet_index)


def open_sheet_by_url(client: gspread.Client, url: str, worksheet_index: int = 0):
    """用 URL 開啟 Google Sheet。

    Args:
        client: gspread Client。
        url: Google Sheet 的完整 URL。
        worksheet_index: 工作表索引（預設第一張 = 0）。

    Returns:
        gspread Worksheet 物件。
    """
    spreadsheet = client.open_by_url(url)
    return spreadsheet.get_worksheet(worksheet_index)


def read_all(worksheet) -> list[list[str]]:
    """讀取工作表所有資料。"""
    return worksheet.get_all_values()


def read_as_dicts(worksheet) -> list[dict]:
    """讀取工作表資料，回傳 dict list（第一列為欄位名稱）。"""
    return worksheet.get_all_records()


def write_row(worksheet, row_data: list, row_number: int | None = None):
    """寫入一列資料。

    Args:
        worksheet: gspread Worksheet。
        row_data: 要寫入的資料（list）。
        row_number: 指定列號。若為 None 則追加到最後一列。
    """
    if row_number is None:
        worksheet.append_row(row_data)
    else:
        worksheet.update(f"A{row_number}", [row_data])


def write_rows(worksheet, rows_data: list[list], start_row: int | None = None):
    """批次寫入多列資料。

    Args:
        worksheet: gspread Worksheet。
        rows_data: 二維 list。
        start_row: 起始列號。若為 None 則追加到最後。
    """
    if start_row is None:
        worksheet.append_rows(rows_data)
    else:
        worksheet.update(f"A{start_row}", rows_data)


def update_cell(worksheet, row: int, col: int, value):
    """更新單一儲存格。"""
    worksheet.update_cell(row, col, value)


def clear_worksheet(worksheet):
    """清空整張工作表。"""
    worksheet.clear()
