"""
2026年3月 便當訂購資料匯入
============================
從紙本訂購表（2026/3）轉入 Google Sheets「便當訂購」分頁。

標記說明：
  V  = 普通便當
  素  = 素食便當（劉英美）
  X  = 未訂
  空白 = 未訂 / 當天休假

執行方式：
  python seed_meal_march2026.py
"""

from main_sync import SHEET_URL, CREDENTIALS_FILE, _open_tab
from sheets_client import connect, write_rows

# ──────────────────────────────────────────────────────────────
# 2026 年 3 月（31天）每人每日訂購狀況
# 來源：紙本訂購表圖片辨識
#
# 格式：[姓名, 第1天, 第2天, ..., 第31天]
# ──────────────────────────────────────────────────────────────
#
# 圖片說明補充：
#   - 阮玉松（#18）整月紅線 → 當月不在職，全部空白
#   - 阮文煜（#29）紅線 → 當月離職/不在職
#   - 劉英美（#21）全部素食便當
#   - 3/16（週日）為例假日，多人未訂
#   - 3月合計：圖片底部顯示各日小計

V = "V"   # 普通便當
S = "素"   # 素食便當
X = "X"   # 未訂
_ = ""    # 空白（休假/假日）

MEAL_DATA = [
    # 姓名        1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
    ["李世彬",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, _],
    ["王淑如",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["許清賢",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, X, _, V, V, V, V, V, _, V, V, _, _],
    ["謝金萬",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, X, _, V, V, X, V, _, V, V, V, V, V, _, V, V, _, _],
    ["許連灯",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, X, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["許天賜",    V, V, X, V, V, _, V, V, V, V, V, V, V, _, X, _, X, V, V, V, _, V, V, V, V, V, _, X, V, _, _],
    ["許柏凱",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["許清輝",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["林義明",    V, V, V, V, _, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["莊明燦",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["陳佩欣",    V, V, V, V, V, _, X, V, X, V, X, V, X, _, X, _, X, V, V, V, _, X, V, X, V, V, _, X, _, _, _],
    ["簡宜君",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, X, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["阮明強",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["阮文華",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, X, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["阮進到",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, X, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["阮文玲",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, X, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["阮文維",    X, X, X, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, X, X, _, _],
    ["阮玉松",    _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _],  # 不在職
    ["阮文吳",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["鄭德凱",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, V, V],
    ["劉英美",    S, S, S, S, S, _, S, S, S, S, S, S, S, _, S, _, S, S, S, S, _, S, S, S, S, S, _, S, S, _, _],  # 素食
    ["阮文輝",    X, V, X, V, V, _, V, V, V, V, V, V, X, _, V, _, V, V, V, V, _, V, X, V, V, V, _, V, _, _, _],
    ["陳振榮",    V, V, V, V, V, _, V, V, V, V, _, X, V, _, V, _, X, V, V, V, _, _, _, _, _, _, _, _, _, _, _],
    ["莊志成",    _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _],
    ["阮文煜",    X, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _],  # 離職
    ["鄧志展",    V, V, V, V, V, _, V, V, V, V, V, V, V, _, V, _, V, V, V, V, _, V, V, V, V, V, _, V, V, _, _],
    ["吳慧娟",    _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _],
    ["王靖銘",    _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _],
]

HEADER = [["姓名"] + [str(d) for d in range(1, 32)] + ["合計"]]
NOTE   = [["※ 標記：V=普通便當  素=素食便當  X=未訂  空白=休假/假日未訂", *[""] * 32]]


def run():
    print("\n連線 Google Sheets ...")
    client = connect(CREDENTIALS_FILE)
    ws = _open_tab(client, "便當訂購")

    rows = NOTE + HEADER
    for emp in MEAL_DATA:
        name = emp[0]
        days = emp[1:]
        count = sum(1 for d in days if d in (V, S))
        rows.append([name] + days + [count])

    print(f"寫入 {len(MEAL_DATA)} 位員工 2026/3 便當資料 ...")
    ws.clear()
    write_rows(ws, rows, start_row=1)

    print("\n完成！2026年3月便當資料已寫入「便當訂購」分頁。")
    print("請確認各員工合計欄數字是否與紙本一致，如有誤差請直接在 Google Sheets 修正。")
    print(f"\n分頁連結：{SHEET_URL}")


if __name__ == "__main__":
    run()
