"""
TradePost Pro - マルチタイムゾーン対応強化
海外ユーザー向けのタイムゾーン自動検出・変換
"""

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json


# 主要タイムゾーン定義
TIMEZONE_DATABASE = {
    # アジア
    "Asia/Tokyo": {"offset": 9, "name_ja": "日本標準時", "name_en": "Japan Standard Time", "abbr": "JST"},
    "Asia/Shanghai": {"offset": 8, "name_ja": "中国標準時", "name_en": "China Standard Time", "abbr": "CST"},
    "Asia/Hong_Kong": {"offset": 8, "name_ja": "香港時間", "name_en": "Hong Kong Time", "abbr": "HKT"},
    "Asia/Singapore": {"offset": 8, "name_ja": "シンガポール時間", "name_en": "Singapore Time", "abbr": "SGT"},
    "Asia/Seoul": {"offset": 9, "name_ja": "韓国標準時", "name_en": "Korea Standard Time", "abbr": "KST"},
    "Asia/Taipei": {"offset": 8, "name_ja": "台湾標準時", "name_en": "Taiwan Standard Time", "abbr": "TST"},
    "Asia/Bangkok": {"offset": 7, "name_ja": "インドシナ時間", "name_en": "Indochina Time", "abbr": "ICT"},
    "Asia/Kolkata": {"offset": 5.5, "name_ja": "インド標準時", "name_en": "India Standard Time", "abbr": "IST"},
    "Asia/Dubai": {"offset": 4, "name_ja": "湾岸標準時", "name_en": "Gulf Standard Time", "abbr": "GST"},
    # ヨーロッパ
    "Europe/London": {"offset": 0, "name_ja": "グリニッジ標準時", "name_en": "Greenwich Mean Time", "abbr": "GMT"},
    "Europe/Paris": {"offset": 1, "name_ja": "中央ヨーロッパ時間", "name_en": "Central European Time", "abbr": "CET"},
    "Europe/Berlin": {"offset": 1, "name_ja": "中央ヨーロッパ時間", "name_en": "Central European Time", "abbr": "CET"},
    "Europe/Moscow": {"offset": 3, "name_ja": "モスクワ時間", "name_en": "Moscow Time", "abbr": "MSK"},
    # アメリカ
    "America/New_York": {"offset": -5, "name_ja": "米国東部時間", "name_en": "Eastern Time", "abbr": "ET"},
    "America/Chicago": {"offset": -6, "name_ja": "米国中部時間", "name_en": "Central Time", "abbr": "CT"},
    "America/Denver": {"offset": -7, "name_ja": "米国山岳部時間", "name_en": "Mountain Time", "abbr": "MT"},
    "America/Los_Angeles": {"offset": -8, "name_ja": "米国太平洋時間", "name_en": "Pacific Time", "abbr": "PT"},
    # オセアニア
    "Australia/Sydney": {"offset": 11, "name_ja": "オーストラリア東部時間", "name_en": "Australian Eastern Time", "abbr": "AEDT"},
    "Pacific/Auckland": {"offset": 13, "name_ja": "ニュージーランド時間", "name_en": "New Zealand Time", "abbr": "NZDT"},
}

# FXマーケットセッション
FX_SESSIONS = {
    "sydney": {"open": 5, "close": 14, "tz": "Australia/Sydney", "name_ja": "シドニー", "name_en": "Sydney"},
    "tokyo": {"open": 9, "close": 18, "tz": "Asia/Tokyo", "name_ja": "東京", "name_en": "Tokyo"},
    "london": {"open": 8, "close": 17, "tz": "Europe/London", "name_ja": "ロンドン", "name_en": "London"},
    "newyork": {"open": 8, "close": 17, "tz": "America/New_York", "name_ja": "ニューヨーク", "name_en": "New York"},
}


@dataclass
class UserTimezone:
    """ユーザーのタイムゾーン設定"""
    user_id: str = ""
    timezone_id: str = "Asia/Tokyo"
    auto_detected: bool = False
    post_time_local: str = "07:00"   # ローカル時間での投稿時間
    post_time_utc: str = "22:00"     # UTC変換後
    market_close_notify: bool = True  # マーケット終了通知


class TimezoneService:
    """マルチタイムゾーンサービス"""

    def __init__(self):
        self.user_settings: Dict[str, UserTimezone] = {}

    # ============================================================
    # タイムゾーン情報
    # ============================================================

    def get_timezone_list(self, lang: str = "ja") -> List[Dict]:
        """タイムゾーン一覧を取得"""
        result = []
        for tz_id, info in TIMEZONE_DATABASE.items():
            offset_h = int(info["offset"])
            offset_m = int((info["offset"] % 1) * 60)
            sign = "+" if info["offset"] >= 0 else "-"
            offset_str = f"UTC{sign}{abs(offset_h):02d}:{offset_m:02d}"

            result.append({
                "id": tz_id,
                "name": info["name_ja"] if lang == "ja" else info["name_en"],
                "abbr": info["abbr"],
                "offset": info["offset"],
                "offset_display": offset_str,
            })

        result.sort(key=lambda x: x["offset"])
        return result

    def detect_timezone_from_offset(self, utc_offset_hours: float) -> List[Dict]:
        """UTCオフセットからタイムゾーンを推定"""
        matches = []
        for tz_id, info in TIMEZONE_DATABASE.items():
            if info["offset"] == utc_offset_hours:
                matches.append({
                    "id": tz_id,
                    "name_ja": info["name_ja"],
                    "name_en": info["name_en"],
                    "abbr": info["abbr"],
                })
        return matches

    # ============================================================
    # 時間変換
    # ============================================================

    def convert_time(
        self,
        time_str: str,
        from_tz: str,
        to_tz: str,
        date_str: Optional[str] = None,
    ) -> Dict:
        """タイムゾーン間の時間変換"""
        from_info = TIMEZONE_DATABASE.get(from_tz)
        to_info = TIMEZONE_DATABASE.get(to_tz)

        if not from_info or not to_info:
            return {"error": "無効なタイムゾーンです"}

        # 時間パース
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        # UTC変換
        utc_hour = hour - from_info["offset"]
        utc_minute = minute - int((from_info["offset"] % 1) * 60)

        # 目的TZ変換
        target_hour = utc_hour + to_info["offset"]
        target_minute = utc_minute + int((to_info["offset"] % 1) * 60)

        # 正規化
        if target_minute >= 60:
            target_hour += 1
            target_minute -= 60
        if target_minute < 0:
            target_hour -= 1
            target_minute += 60

        day_offset = 0
        if target_hour >= 24:
            target_hour -= 24
            day_offset = 1
        elif target_hour < 0:
            target_hour += 24
            day_offset = -1

        return {
            "from_time": f"{hour:02d}:{minute:02d}",
            "from_tz": from_tz,
            "from_abbr": from_info["abbr"],
            "to_time": f"{int(target_hour):02d}:{int(target_minute):02d}",
            "to_tz": to_tz,
            "to_abbr": to_info["abbr"],
            "day_offset": day_offset,
            "day_note": "" if day_offset == 0 else ("翌日" if day_offset > 0 else "前日"),
        }

    def local_to_utc(self, time_str: str, tz_id: str) -> str:
        """ローカル時間をUTCに変換"""
        result = self.convert_time(time_str, tz_id, "Europe/London")
        return result.get("to_time", time_str)

    def utc_to_local(self, time_str: str, tz_id: str) -> str:
        """UTCをローカル時間に変換"""
        result = self.convert_time(time_str, "Europe/London", tz_id)
        return result.get("to_time", time_str)

    # ============================================================
    # ユーザー設定
    # ============================================================

    def set_user_timezone(
        self,
        user_id: str,
        timezone_id: str,
        post_time_local: str = "07:00",
        auto_detected: bool = False,
    ) -> Dict:
        """ユーザーのタイムゾーンを設定"""
        if timezone_id not in TIMEZONE_DATABASE:
            return {"status": "error", "message": "無効なタイムゾーンです"}

        post_time_utc = self.local_to_utc(post_time_local, timezone_id)

        setting = UserTimezone(
            user_id=user_id,
            timezone_id=timezone_id,
            auto_detected=auto_detected,
            post_time_local=post_time_local,
            post_time_utc=post_time_utc,
        )
        self.user_settings[user_id] = setting

        tz_info = TIMEZONE_DATABASE[timezone_id]
        return {
            "status": "success",
            "timezone": timezone_id,
            "timezone_name": tz_info["name_ja"],
            "post_time_local": post_time_local,
            "post_time_utc": post_time_utc,
        }

    def get_user_local_time(self, user_id: str) -> Dict:
        """ユーザーの現在のローカル時間を取得"""
        setting = self.user_settings.get(user_id)
        if not setting:
            setting = UserTimezone(user_id=user_id)

        tz_info = TIMEZONE_DATABASE[setting.timezone_id]
        utc_now = datetime.utcnow()
        offset = timedelta(hours=tz_info["offset"])
        local_now = utc_now + offset

        return {
            "timezone": setting.timezone_id,
            "local_time": local_now.strftime("%Y-%m-%d %H:%M:%S"),
            "utc_time": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
            "abbr": tz_info["abbr"],
        }

    # ============================================================
    # FXマーケットセッション
    # ============================================================

    def get_active_sessions(self, user_tz: str = "Asia/Tokyo") -> List[Dict]:
        """現在アクティブなFXセッションを取得"""
        user_info = TIMEZONE_DATABASE.get(user_tz)
        if not user_info:
            return []

        utc_now = datetime.utcnow()
        active = []

        for session_id, session in FX_SESSIONS.items():
            session_tz = TIMEZONE_DATABASE[session["tz"]]
            session_local = utc_now + timedelta(hours=session_tz["offset"])
            current_hour = session_local.hour

            is_open = session["open"] <= current_hour < session["close"]

            # ユーザーのローカル時間に変換
            open_converted = self.convert_time(
                f"{session['open']:02d}:00", session["tz"], user_tz
            )
            close_converted = self.convert_time(
                f"{session['close']:02d}:00", session["tz"], user_tz
            )

            active.append({
                "session": session["name_ja"],
                "is_open": is_open,
                "status": "開場中" if is_open else "閉場",
                "local_open": open_converted.get("to_time", ""),
                "local_close": close_converted.get("to_time", ""),
            })

        return active

    def get_next_market_events(self, user_tz: str = "Asia/Tokyo", count: int = 5) -> List[Dict]:
        """次のマーケットイベント（開場/閉場）を取得"""
        events = []
        user_info = TIMEZONE_DATABASE.get(user_tz)
        if not user_info:
            return events

        for session_id, session in FX_SESSIONS.items():
            open_conv = self.convert_time(f"{session['open']:02d}:00", session["tz"], user_tz)
            close_conv = self.convert_time(f"{session['close']:02d}:00", session["tz"], user_tz)

            events.append({
                "session": session["name_ja"],
                "event": "開場",
                "time": open_conv.get("to_time", ""),
                "day_note": open_conv.get("day_note", ""),
            })
            events.append({
                "session": session["name_ja"],
                "event": "閉場",
                "time": close_conv.get("to_time", ""),
                "day_note": close_conv.get("day_note", ""),
            })

        events.sort(key=lambda x: x["time"])
        return events[:count]


# テスト用
if __name__ == "__main__":
    service = TimezoneService()

    print("=== タイムゾーン一覧（一部） ===")
    for tz in service.get_timezone_list()[:5]:
        print(f"  {tz['offset_display']} {tz['name']} ({tz['abbr']})")

    print(f"\n=== 時間変換テスト ===")
    # 東京7:00 → ニューヨーク
    result = service.convert_time("07:00", "Asia/Tokyo", "America/New_York")
    print(f"  東京 07:00 → NY {result['to_time']} {result['day_note']}")

    # 東京7:00 → ロンドン
    result = service.convert_time("07:00", "Asia/Tokyo", "Europe/London")
    print(f"  東京 07:00 → ロンドン {result['to_time']} {result['day_note']}")

    # 東京7:00 → 上海
    result = service.convert_time("07:00", "Asia/Tokyo", "Asia/Shanghai")
    print(f"  東京 07:00 → 上海 {result['to_time']} {result['day_note']}")

    print(f"\n=== ユーザーTZ設定 ===")
    # NYユーザー
    result = service.set_user_timezone("user_ny", "America/New_York", "07:00")
    print(f"  NYユーザー: ローカル {result['post_time_local']} → UTC {result['post_time_utc']}")

    # 東京ユーザー
    result = service.set_user_timezone("user_jp", "Asia/Tokyo", "07:00")
    print(f"  東京ユーザー: ローカル {result['post_time_local']} → UTC {result['post_time_utc']}")

    print(f"\n=== TZ自動検出 ===")
    matches = service.detect_timezone_from_offset(9)
    for m in matches:
        print(f"  UTC+9: {m['name_ja']} ({m['id']})")

    print(f"\n=== FXセッション ===")
    sessions = service.get_active_sessions("Asia/Tokyo")
    for s in sessions:
        print(f"  {s['session']}: {s['status']} ({s['local_open']}〜{s['local_close']} JST)")

    print(f"\n=== 次のマーケットイベント ===")
    events = service.get_next_market_events("Asia/Tokyo")
    for e in events:
        print(f"  {e['time']} {e['session']} {e['event']} {e['day_note']}")

    print("\n✓ マルチタイムゾーンサービス テスト完了")
