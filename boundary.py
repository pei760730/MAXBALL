"""
邊界驗證層
==========
Sheet ↔ 引擎之間「靜默漂移 → fail loud」的閘門集中於此。

兩道獨立守門：
  1. validate_header(header_row, expected_keywords, sheet_name)
     —— 欄位順序漂移時 raise ValueError。
  2. validate_attendance(configs, attendances) -> list[str]
     —— 姓名 typo / 值域異常 → 訊息列表。
     含 [錯誤] 前綴者由 is_fatal() 判定為致命，呼叫端應中止。

這層必須能不依賴 Google Sheets 被獨立測試（見檔尾 __main__）。
"""

from salary_calculator import SalaryConfig, AttendanceRecord


ATTENDANCE_HEADER_KEYWORDS = [
    "姓名", "曆日", "工作日", "實際出勤", "假日加班", "週日加班",
    "1.33", "1.66", "事假", "病假", "無薪", "特休", "全勤", "節金",
]

MEAL_MARKERS = {"V", "素"}


def _col_letter(idx: int) -> str:
    # 0→A, 1→B, ..., 25→Z, 26→col27 略
    return chr(ord("A") + idx) if idx < 26 else f"col{idx+1}"


def validate_header(header_row, expected_keywords, sheet_name):
    """每個預期關鍵字必須以 substring 形式出現在對應欄；否則 raise。"""
    if len(header_row) < len(expected_keywords):
        raise ValueError(
            f"{sheet_name}: header 僅 {len(header_row)} 欄，預期 ≥ {len(expected_keywords)} 欄"
        )
    for i, kw in enumerate(expected_keywords):
        cell = (header_row[i] or "").strip()
        if kw not in cell:
            raise ValueError(
                f"{sheet_name}: 第 {i+1} 欄 ({_col_letter(i)}) 預期含 '{kw}'，實際為 '{cell}'；"
                f"若 Sheet 欄位順序已變動，請同步更新 {sheet_name} 的讀取邏輯。"
            )


def validate_attendance(configs: list, attendances: dict) -> list[str]:
    """
    姓名比對 + 值域檢查；回傳訊息列表。

    Args:
        configs: list[SalaryConfig]
        attendances: dict[name -> AttendanceRecord]
    """
    messages: list[str] = []
    config_names = {c.name for c in configs}
    att_names = set(attendances.keys())

    missing_att = config_names - att_names
    extra_att = att_names - config_names
    if missing_att:
        messages.append(f"[警告] 員工無出勤記錄：{', '.join(sorted(missing_att))}")
    if extra_att:
        messages.append(
            f"[錯誤] 出勤表有不明姓名（typo 或未登錄員工）：{', '.join(sorted(extra_att))}"
        )

    for name, att in attendances.items():
        if not (28 <= att.calendar_days <= 31):
            messages.append(f"[錯誤] {name} 曆日={att.calendar_days}（應 28-31）")
        if not (0 <= att.work_days <= att.calendar_days):
            messages.append(
                f"[錯誤] {name} 工作日={att.work_days}（應 ≤ 曆日 {att.calendar_days}）"
            )
        if att.actual_work_days < 0 or att.actual_work_days > att.work_days:
            messages.append(
                f"[警告] {name} 實際出勤={att.actual_work_days}（工作日={att.work_days}）"
            )
        if att.overtime_hours_1 < 0 or att.overtime_hours_2 < 0:
            messages.append(f"[錯誤] {name} 加班時數為負數")
        if att.holiday_overtime_days < 0 or att.sunday_overtime_days < 0:
            messages.append(f"[錯誤] {name} 假日/週日加班日為負數")

    return messages


def parse_meal_marker(name: str, col_idx_1based: int, raw: str) -> int:
    """
    便當標記 boundary：
      - 空白 / X / x / - / 0 => 0
      - V / v / 素 => 1
      - 其他非空字元 => raise ValueError（fail loud）
    """
    value = (raw or "").strip()
    if value == "":
        return 0

    normalized = value.upper()
    if normalized in MEAL_MARKERS:
        return 1
    if normalized in {"X", "-", "0"}:
        return 0

    raise ValueError(
        f"便當訂購: 未知標記 '{value}'（姓名={name}, 第{col_idx_1based}欄）"
    )


def is_fatal(messages: list[str]) -> bool:
    """是否含致命錯誤（[錯誤] 前綴）。"""
    return any(m.startswith("[錯誤]") for m in messages)


# ──────────────────────────────────────────────────────────────
# Self-test（不需要 Google Sheets）
# ──────────────────────────────────────────────────────────────
def selftest():
    # ── header 漂移：欄位數不足 ──
    try:
        validate_header(["姓名"], ATTENDANCE_HEADER_KEYWORDS, "月出勤")
        raise AssertionError("欄數不足應 raise")
    except ValueError:
        pass

    # ── header 漂移：第 7 欄缺 1.33 ──
    bad = list(ATTENDANCE_HEADER_KEYWORDS)
    bad[6] = "亂塞"
    try:
        validate_header(bad, ATTENDANCE_HEADER_KEYWORDS, "月出勤")
        raise AssertionError("關鍵字錯位應 raise")
    except ValueError as e:
        assert "1.33" in str(e)

    # ── header OK：substring 命中即可 ──
    ok_header = [k + " 文字補充" for k in ATTENDANCE_HEADER_KEYWORDS]
    validate_header(ok_header, ATTENDANCE_HEADER_KEYWORDS, "月出勤")

    # ── attendance 驗證 ──
    cfg = SalaryConfig(
        employee_id="X", name="測試員",
        base_salary=14_100, duty_allowance=0, other_allowance=0,
        position_allowance=0, full_attendance_bonus=0,
        labor_insurance_base=0, health_insurance_base=0, pension_base=0,
    )
    cfg2 = SalaryConfig(**{**cfg.__dict__, "name": "另一人"})

    # typo 姓名 → 致命
    msgs = validate_attendance(
        [cfg, cfg2],
        {"測試員": AttendanceRecord(2026, 3, 31, 22, 22.0), "錯字員": AttendanceRecord(2026, 3, 31, 22, 22.0)},
    )
    assert is_fatal(msgs), f"typo 應致命: {msgs}"
    assert any("錯字員" in m for m in msgs)
    assert any("另一人" in m for m in msgs)  # 缺出勤的警告

    # 曆日越界 → 致命
    msgs = validate_attendance(
        [cfg],
        {"測試員": AttendanceRecord(2026, 3, 99, 22, 22.0)},
    )
    assert is_fatal(msgs), f"曆日越界應致命: {msgs}"

    # 加班時數負數 → 致命
    msgs = validate_attendance(
        [cfg],
        {"測試員": AttendanceRecord(2026, 3, 31, 22, 22.0, overtime_hours_1=-1)},
    )
    assert is_fatal(msgs), f"加班負數應致命: {msgs}"

    # 全勤一切正常 → 0 訊息
    msgs = validate_attendance(
        [cfg],
        {"測試員": AttendanceRecord(2026, 3, 31, 22, 22.0)},
    )
    assert msgs == [], f"全勤應 0 訊息: {msgs}"

    # ── meal marker：未知字元應 fail loud ──
    assert parse_meal_marker("測試員", 2, "V") == 1
    assert parse_meal_marker("測試員", 3, "素") == 1
    assert parse_meal_marker("測試員", 4, "x") == 0
    try:
        parse_meal_marker("測試員", 5, "✓")
        raise AssertionError("未知標記應 raise")
    except ValueError as e:
        assert "測試員" in str(e)
        assert "第5欄" in str(e)

    print("  ✓ boundary self-test: all pass")


if __name__ == "__main__":
    selftest()
