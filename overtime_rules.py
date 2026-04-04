"""
公司加班規則模組
================

【標準上班時間】
  08:00 上班 → 12:00 午休
  13:00 上班 → 17:00 下班
  17:00 ~ 17:30 吃飯休息（不計加班）
  正常工時：8 小時／日

【一、平日加班（週一～週五）】

  早班加班（提早上班）：
    - 到班時間往後推到下一個 30 分鐘整點，該時間點到 08:00 = 早班加班時數
    - 例：06:40 → 07:00 起算 → 07:00~08:00 = 1.0 小時
    - 例：07:20 → 07:30 起算 → 07:30~08:00 = 0.5 小時
    - 08:00 以後到班 = 0（遲到另計，不算早班加班）

  晚班加班（延遲下班）：
    - 17:30 之後繼續工作才算加班（17:00~17:30 為吃飯休息）

  早班 ＋ 晚班 合計計算加班費率：
    第 1 ～ 2 小時：1.33 倍
    第 3 小時起　：1.66 倍

【二、假日加班（週六、週日、國定例假日）】

  工作時數   倍率
  1 ～ 2 hr  1.33 倍
  3 ～ 8 hr  1.66 倍
  9 ～ 10 hr 1.33 倍（重設）
  11 hr 起   1.66 倍

【三、加班費計算公式】

  時薪基準 = (本薪 + 職務津貼 + 職務加給) ÷ 30 ÷ 8
  加班費   = 時薪基準 × 加班時數 × 倍率
"""

import math


# ── 時間常數（分鐘）──────────────────────────────
WORK_START     = 8 * 60        # 08:00 正常上班
EVENING_START  = 17 * 60 + 30  # 17:30 晚班加班開始
MEAL_BREAK_END = 17 * 60 + 30  # 17:00-17:30 吃飯休息

# 倍率
RATE_1 = 1.33
RATE_2 = 1.66


def _to_minutes(time_str: str) -> int:
    """'HH:MM' → 分鐘數"""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def round_up_to_half_hour(minutes: int) -> int:
    """
    往後推到下一個 30 分鐘整點。
    例：06:40 (400) → 07:00 (420)
        07:20 (440) → 07:30 (450)
        07:00 (420) → 07:00 (420)  ← 已在整點，不動
    """
    return math.ceil(minutes / 30) * 30


def calc_early_overtime(checkin_str: str) -> float:
    """
    計算早班加班時數。

    規則：
      - 到班時間往後推到下一個 30 分鐘整點
      - 該整點到 08:00 的時數 = 早班加班時數
      - 08:00 以後到班 = 0

    Args:
        checkin_str: 打卡時間，格式 'HH:MM'

    Returns:
        早班加班時數（小時，最小單位 0.5）
    """
    ci = _to_minutes(checkin_str)
    if ci >= WORK_START:
        return 0.0
    rounded = round_up_to_half_hour(ci)
    rounded = min(rounded, WORK_START)  # 不超過 08:00
    return (WORK_START - rounded) / 60


def calc_evening_overtime(checkout_str: str) -> float:
    """
    計算晚班加班時數（17:30 之後）。

    Args:
        checkout_str: 打卡時間，格式 'HH:MM'

    Returns:
        晚班加班時數（小時）
    """
    co = _to_minutes(checkout_str)
    if co <= EVENING_START:
        return 0.0
    return (co - EVENING_START) / 60


def calc_weekday_overtime_pay(checkin_str: str, checkout_str: str,
                               hourly_base: float) -> dict:
    """
    計算平日（週一～週五）加班費明細。

    早班 ＋ 晚班加班時數合計：
      第 1～2 小時 → 1.33 倍
      第 3 小時起  → 1.66 倍

    Args:
        checkin_str:  上班打卡 'HH:MM'
        checkout_str: 下班打卡 'HH:MM'
        hourly_base:  時薪基準（元）

    Returns:
        {
          'early_hrs': float,    早班加班時數
          'evening_hrs': float,  晚班加班時數
          'total_hrs': float,    合計加班時數
          'rate1_hrs': float,    1.33 倍時數
          'rate2_hrs': float,    1.66 倍時數
          'pay': float,          加班費（元）
        }
    """
    early   = calc_early_overtime(checkin_str)
    evening = calc_evening_overtime(checkout_str)
    total   = early + evening

    rate1_hrs = min(total, 2.0)
    rate2_hrs = max(total - 2.0, 0.0)
    pay = round(hourly_base * (rate1_hrs * RATE_1 + rate2_hrs * RATE_2))

    return {
        'early_hrs':   early,
        'evening_hrs': evening,
        'total_hrs':   total,
        'rate1_hrs':   rate1_hrs,
        'rate2_hrs':   rate2_hrs,
        'pay':         pay,
    }


def calc_holiday_overtime_pay(checkin_str: str, checkout_str: str,
                               hourly_base: float) -> dict:
    """
    計算假日（週六、週日、國定例假日）加班費明細。

    倍率結構：
      1 ～  2 hr：1.33 倍
      3 ～  8 hr：1.66 倍
      9 ～ 10 hr：1.33 倍（重設）
      11 hr 起  ：1.66 倍

    Args:
        checkin_str:  上班打卡 'HH:MM'
        checkout_str: 下班打卡 'HH:MM'
        hourly_base:  時薪基準（元）

    Returns:
        {
          'total_hrs': float,  總工作時數
          'pay': float,        加班費（元）
          'breakdown': str,    計算明細說明
        }
    """
    ci = _to_minutes(checkin_str)
    co = _to_minutes(checkout_str)
    total_hrs = (co - ci) / 60

    # 套用假日分段倍率
    segments = [
        (2.0,  RATE_1),   # hr 1-2
        (6.0,  RATE_2),   # hr 3-8
        (2.0,  RATE_1),   # hr 9-10
        (9999, RATE_2),   # hr 11+
    ]

    remaining = total_hrs
    pay = 0.0
    breakdown_parts = []
    for limit, rate in segments:
        hrs = min(remaining, limit)
        if hrs <= 0:
            break
        pay += hourly_base * hrs * rate
        breakdown_parts.append(f"{hrs:.2f}hr×{rate}")
        remaining -= hrs

    return {
        'total_hrs': total_hrs,
        'pay':       round(pay),
        'breakdown': ' + '.join(breakdown_parts),
    }


def calc_hourly_base(base_salary: float, duty_allowance: float,
                     duty_supplement: float) -> float:
    """
    時薪基準 = (本薪 + 職務津貼 + 職務加給) ÷ 30 ÷ 8
    """
    return (base_salary + duty_allowance + duty_supplement) / 30 / 8


# ── 快速測試 ──────────────────────────────────────
if __name__ == '__main__':
    # 鄧志展薪資基準
    base = calc_hourly_base(16350, 7950, 2850)
    print(f"時薪基準: {base:.4f} 元/時")
    print(f"1.33倍時薪: {base * RATE_1:.2f} 元/時")
    print(f"1.66倍時薪: {base * RATE_2:.2f} 元/時")

    print()
    print("=== 早班加班測試 ===")
    for t in ['06:40', '06:53', '07:20', '07:30', '07:50', '08:00', '08:10']:
        hrs = calc_early_overtime(t)
        print(f"  {t} 到班 → 早班加班 {hrs} 小時")

    print()
    print("=== 平日加班測試（03/02: 06:44-21:33）===")
    result = calc_weekday_overtime_pay('06:44', '21:33', base)
    print(f"  早班: {result['early_hrs']}hr  晚班: {result['evening_hrs']:.2f}hr")
    print(f"  合計: {result['total_hrs']:.2f}hr  "
          f"(1.33x: {result['rate1_hrs']:.2f}hr, 1.66x: {result['rate2_hrs']:.2f}hr)")
    print(f"  加班費: {result['pay']:,} 元")

    print()
    print("=== 假日加班測試（週六 03/14: 06:51-19:04）===")
    hol = calc_holiday_overtime_pay('06:51', '19:04', base)
    print(f"  工作 {hol['total_hrs']:.2f}hr")
    print(f"  計算: {hol['breakdown']}")
    print(f"  加班費: {hol['pay']:,} 元")
