from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from urllib.request import urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
APP_DIR = SCRIPT_DIR.parent
DEFAULT_RUNTIME_DIR = (
    Path(os.getenv("APPDATA", str(APP_DIR))) / "StockListenerAssistant" / "runtime"
)
RUNTIME_DIR = Path(os.getenv("LISTENER_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

MODULE_SEARCH_PATHS = [
    SCRIPT_DIR,
    SCRIPT_DIR / "backend",
    APP_DIR / "electron",
    APP_DIR / "electron" / "backend",
    Path(r"E:\PythonProject\stock_intraday_fetch"),
    Path(r"E:\Project\stock_intraday_fetch"),
]
for module_path in MODULE_SEARCH_PATHS:
    if module_path.exists() and str(module_path) not in sys.path:
        sys.path.append(str(module_path))

from fetch_tdx_intraday_30d import MARKET_SH, fetch_bars  # type: ignore  # noqa: E402
from live_divergence_incremental import load_bars, replay_bars  # type: ignore  # noqa: E402


MARKET_SZ = 0
POLL_SECONDS = 30
FETCH_DAYS = 7
INTRADAY_POLL_DAYS = 1
SNAPSHOT_PATH = RUNTIME_DIR / "live_snapshot.json"
WATCHLIST_PATH = RUNTIME_DIR / "watchlist.json"
RULES_PATH = RUNTIME_DIR / "rules_config.json"

DEFAULT_STOCKS = []

SIGNAL_LABELS = {
    "bearish_divergence": "顶背离卖出",
    "bullish_divergence": "底背离买入",
    "macd_dead_cross_sell": "MACD死叉卖出",
    "macd_golden_cross_buy": "MACD金叉买入",
}

DEFAULT_RULES = {
    "signals": {
        "顶背离卖出": True,
        "底背离买入": True,
        "MACD金叉买入": True,
        "MACD死叉卖出": True,
    },
    "period": "5分钟",
    "limit": "",
}

TRADING_WINDOWS = (
    (dt_time(9, 30), dt_time(11, 30)),
    (dt_time(13, 0), dt_time(15, 0)),
)


def infer_market(symbol: str) -> int:
    return MARKET_SH if symbol.startswith(("5", "6", "9")) else MARKET_SZ


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_debug_log(message: str) -> None:
    log_path = RUNTIME_DIR / "data_service_debug.log"
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(line)
    except Exception:
        pass


def safe_fetch_realtime_quote(symbol: str, market: int, fallback_name: str) -> dict:
    market_prefix = "sh" if market == MARKET_SH else "sz"
    url = f"https://qt.gtimg.cn/q={market_prefix}{symbol}"

    try:
        raw = urlopen(url, timeout=10).read().decode("gbk", errors="ignore")
        payload = raw.split('"', 1)[1].rsplit('"', 1)[0]
        parts = payload.split("~")
        if len(parts) < 5:
            raise RuntimeError(f"unexpected quote payload: {raw[:120]}")
        name = (parts[1] or fallback_name or symbol).strip()
        price = float(parts[3]) if parts[3] else 0.0
        prev_close = float(parts[4]) if parts[4] else 0.0
        return {
            "name": name,
            "price": price,
            "prev_close": prev_close,
        }
    except Exception as exc:
        append_debug_log(
            f"safe_fetch_realtime_quote failed symbol={symbol} error={exc}"
        )
        return {
            "name": fallback_name,
            "price": 0.0,
            "prev_close": 0.0,
        }


def load_rules() -> dict:
    payload = load_json(RULES_PATH, None)
    if not isinstance(payload, dict):
        return DEFAULT_RULES
    signals_payload = payload.get("signals")
    signals = signals_payload if isinstance(signals_payload, dict) else {}
    merged_signals = dict(DEFAULT_RULES["signals"])
    merged_signals.update(signals)
    return {
        "signals": merged_signals,
        "period": payload.get("period") or DEFAULT_RULES["period"],
        "limit": payload.get("limit") or DEFAULT_RULES["limit"],
    }


def get_signal_period(rules: dict) -> str:
    period = f"{rules.get('period') or DEFAULT_RULES['period']}"
    return period if period in {"1分钟", "5分钟"} else DEFAULT_RULES["period"]


def is_trading_time(now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if now.weekday() >= 5:
        return False

    current_time = now.time().replace(tzinfo=None)
    for start, end in TRADING_WINDOWS:
        if start <= current_time <= end:
            return True
    return False


def ensure_watchlist() -> list[dict]:
    watchlist = load_json(WATCHLIST_PATH, None)
    if isinstance(watchlist, list) and watchlist:
        return normalize_watchlist(watchlist)

    watchlist = []
    for stock in DEFAULT_STOCKS:
        watchlist.append(
            {
                "code": stock["code"],
                "name": stock["name"],
                "status": "ready",
                "message": "已接入实时轮询",
                "lastProcessedAt": None,
                "updatedAt": None,
            }
        )
    save_json(WATCHLIST_PATH, watchlist)
    return watchlist


def normalize_watchlist(watchlist: list[dict]) -> list[dict]:
    normalized = []
    seen = set()
    for item in watchlist:
        code = f"{item.get('code', '')}".strip()
        if not code or code in seen:
            continue
        seen.add(code)
        normalized.append(
            {
                "code": code,
                "name": f"{item.get('name', code)}".strip() or code,
                "status": item.get("status", "ready"),
                "message": item.get("message", "已接入实时轮询"),
                "lastProcessedAt": item.get("lastProcessedAt"),
                "updatedAt": item.get("updatedAt"),
            }
        )
    return normalized


def save_csv(rows: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["datetime", "open", "close", "high", "low", "volume", "amount"],
        )
        writer.writeheader()
        writer.writerows(rows)


def read_intraday_rows(csv_path: Path) -> list[dict]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def merge_intraday_rows(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    merged = {}
    for row in existing_rows + new_rows:
        dt = f"{row.get('datetime', '')}".strip()
        if not dt:
            continue
        merged[dt] = {
            "datetime": dt,
            "open": float(row["open"]),
            "close": float(row["close"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "volume": int(float(row["volume"])),
            "amount": float(row["amount"]),
        }

    ordered = [merged[key] for key in sorted(merged.keys())]
    unique_days = sorted({row["datetime"].split(" ")[0] for row in ordered})
    keep_days = set(unique_days[-FETCH_DAYS:]) if unique_days else set()
    return [row for row in ordered if row["datetime"].split(" ")[0] in keep_days]


def read_signal_rows(signal_path: Path) -> list[dict]:
    if not signal_path.exists() or signal_path.stat().st_size == 0:
        return []
    with signal_path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def read_last_signal(signal_path: Path) -> dict | None:
    rows = read_signal_rows(signal_path)
    return rows[-1] if rows else None


def build_status(signal_name: str | None, watch_status: str) -> tuple[str, str]:
    if watch_status == "loading":
        return "下载中", "neutral"
    if watch_status == "error":
        return "处理失败", "sell"
    if not signal_name:
        return "监控中", "neutral"
    if "卖出" in signal_name or "死叉" in signal_name or "顶背离" in signal_name:
        return "高风险", "sell"
    return "已买入", "buy"


def build_badge(signal_name: str | None) -> str:
    if not signal_name:
        return "neutral"
    if "卖出" in signal_name or "死叉" in signal_name or "顶背离" in signal_name:
        return "sell"
    if "买入" in signal_name or "金叉" in signal_name or "突破" in signal_name:
        return "buy"
    return "neutral"


def is_signal_enabled(signal_name: str | None, rules: dict) -> bool:
    if not signal_name:
        return False
    signals = rules.get("signals") if isinstance(rules, dict) else {}
    if not isinstance(signals, dict):
        return True
    return bool(signals.get(signal_name, False))


def sort_rows_by_time_desc(rows: list[dict]) -> list[dict]:
    def sort_key(row: dict) -> tuple[int, str]:
        raw = f"{row.get('sortTime') or row.get('fullTime') or row.get('time') or ''}"
        try:
            if len(raw) == 5:
                parsed = datetime.strptime(raw, "%H:%M")
            elif len(raw) == 8:
                parsed = datetime.strptime(raw, "%H:%M:%S")
            else:
                fmt = "%Y-%m-%d %H:%M:%S" if len(raw) >= 19 else "%Y-%m-%d %H:%M"
                parsed = datetime.strptime(raw[:19] if len(raw) >= 19 else raw, fmt)
            return (1, parsed.strftime("%Y%m%d%H%M%S"))
        except Exception:
            return (0, raw)

    return sorted(rows, key=sort_key, reverse=True)


def format_signal_time(value: str | None, fallback: str | None = None) -> str:
    raw = (value or fallback or "").strip()
    if not raw:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d":
                return parsed.strftime("%Y-%m-%d 00:00:00")
            if fmt == "%Y-%m-%d %H:%M":
                return parsed.strftime("%Y-%m-%d %H:%M:00")
            return parsed.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    return raw


def format_detection_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_rows_by_datetime(rows: list[dict]) -> dict[str, dict]:
    return {f"{row.get('datetime', '')}": row for row in rows if row.get("datetime")}


def build_previous_close_map(rows: list[dict]) -> dict[str, float]:
    day_last_close = {}
    for row in rows:
        day = row["datetime"].split(" ")[0]
        day_last_close[day] = float(row["close"])

    previous_close_map = {}
    ordered_days = sorted(day_last_close.keys())
    previous_close = None
    for day in ordered_days:
        if previous_close is not None:
            previous_close_map[day] = previous_close
        previous_close = day_last_close[day]
    return previous_close_map


def resolve_signal_price(
    item: dict, row_at_signal: dict | None, latest_close: float
) -> float:
    for key in ("trigger_price", "current_price"):
        raw = f"{item.get(key, '')}".strip()
        if raw:
            try:
                return float(raw)
            except ValueError:
                pass
    if row_at_signal:
        try:
            return float(row_at_signal["close"])
        except Exception:
            pass
    return latest_close


def resolve_signal_change(
    signal_dt: str,
    signal_price: float,
    rows: list[dict],
    previous_close_map: dict[str, float],
) -> str:
    signal_day = signal_dt.split(" ")[0]
    reference_close = float(previous_close_map.get(signal_day) or 0)
    if reference_close:
        change_pct = (signal_price - reference_close) / reference_close * 100
        return f"{change_pct:+.2f}%"

    day_rows = [row for row in rows if row["datetime"].split(" ")[0] == signal_day]
    if not day_rows:
        return "--"
    first_open = float(day_rows[0]["open"])
    if not first_open:
        return "--"
    change_pct = (signal_price - first_open) / first_open * 100
    return f"{change_pct:+.2f}%"


def process_stock(
    stock: dict, fetch_days: int, reset_state: bool = False, period: str = "1分钟"
) -> tuple[dict, dict, str | None, list[dict]]:
    symbol = stock["code"]
    market = infer_market(symbol)
    append_debug_log(
        f"process_stock start symbol={symbol} fetch_days={fetch_days} reset_state={reset_state}"
    )
    rows = fetch_bars(symbol=symbol, market=market, days=fetch_days, period=period)
    if not rows:
        raise RuntimeError(f"empty rows for {symbol}")

    realtime_quote = safe_fetch_realtime_quote(symbol, market, stock["name"])
    resolved_name = realtime_quote.get("name") or stock["name"]
    stock["name"] = resolved_name

    period_suffix = "5m" if period == "5分钟" else "1m"
    csv_path = RUNTIME_DIR / f"{symbol}_{period_suffix}_intraday.csv"
    state_path = RUNTIME_DIR / f"{symbol}_{period_suffix}_state.json"
    signal_path = RUNTIME_DIR / f"{symbol}_{period_suffix}_signals.csv"

    if reset_state:
        if state_path.exists():
            state_path.unlink()
        if signal_path.exists():
            signal_path.unlink()

    existing_rows = read_intraday_rows(csv_path)
    merged_rows = merge_intraday_rows(existing_rows, rows)
    save_csv(merged_rows, csv_path)
    replay_bars(load_bars(csv_path), state_path, signal_path)

    latest = rows[-1]
    rows_by_datetime = build_rows_by_datetime(merged_rows)
    previous_close_map = build_previous_close_map(merged_rows)
    current_price = float(realtime_quote.get("price") or latest["close"])
    prev_close = float(realtime_quote.get("prev_close") or 0)
    if prev_close:
        change_pct = ((current_price - prev_close) / prev_close) * 100
    else:
        today_rows = [
            row
            for row in rows
            if row["datetime"].split(" ")[0] == latest["datetime"].split(" ")[0]
        ]
        first_open = float(today_rows[0]["open"])
        change_pct = (
            ((current_price - first_open) / first_open * 100) if first_open else 0.0
        )
    change_text = f"{change_pct:+.2f}%"

    signal_rows = read_signal_rows(signal_path)
    last_signal = signal_rows[-1] if signal_rows else None
    signal_key = last_signal.get("signal") if last_signal else None
    signal_name = SIGNAL_LABELS.get(signal_key, signal_key) if signal_key else None
    status_text, tone = build_status(signal_name, stock.get("status", "ready"))
    badge = build_badge(signal_name)
    signal_text = signal_name or "等待信号"
    signal_time = format_signal_time(
        last_signal.get("pivot_time") if last_signal else latest["datetime"],
        latest["datetime"],
    )
    signal_price = resolve_signal_price(
        last_signal or {}, rows_by_datetime.get(signal_time), current_price
    )
    signal_change = resolve_signal_change(
        signal_time, signal_price, merged_rows, previous_close_map
    )

    dashboard_row = {
        "code": symbol,
        "name": resolved_name,
        "signal": signal_text,
        "price": f"{signal_price:.2f}",
        "change": signal_change,
        "time": signal_time,
        "status": status_text,
        "badge": badge,
        "tone": tone,
        "sortTime": signal_time,
    }
    monitor_row = {
        "code": symbol,
        "name": resolved_name,
        "price": f"{signal_price:.2f}",
        "change": signal_change,
        "signal": signal_text,
        "time": signal_time[11:16],
        "fullTime": signal_time,
    }

    recent_signal_rows = []
    for item in reversed(signal_rows):
        raw_signal = item.get("signal") or ""
        label = SIGNAL_LABELS.get(raw_signal, raw_signal or "等待信号")
        item_time = format_signal_time(item.get("pivot_time", ""), latest["datetime"])
        row_at_signal = rows_by_datetime.get(item_time)
        item_price = resolve_signal_price(item, row_at_signal, current_price)
        item_change = resolve_signal_change(
            item_time, item_price, merged_rows, previous_close_map
        )
        recent_signal_rows.append(
            {
                "code": symbol,
                "name": resolved_name,
                "signal": label,
                "price": f"{item_price:.2f}",
                "change": item_change,
                "time": item_time,
                "status": build_status(label, "ready")[0],
                "badge": build_badge(label),
                "tone": build_status(label, "ready")[1],
                "sortTime": item_time,
            }
        )

    append_debug_log(
        f"process_stock done symbol={symbol} rows={len(rows)} signals={len(signal_rows)} latest_signal={signal_name or 'none'}"
    )
    return dashboard_row, monitor_row, signal_name, recent_signal_rows


def build_loading_row(stock: dict) -> dict:
    return {
        "code": stock["code"],
        "name": stock["name"],
        "signal": "正在下载最新7个交易日分时数据",
        "price": "--",
        "change": "--",
        "time": datetime.now().strftime("%H:%M:%S"),
        "status": "下载中",
        "badge": "neutral",
        "tone": "neutral",
        "sortTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_snapshot(watchlist: list[dict]) -> dict:
    rules = load_rules()
    period = get_signal_period(rules)
    dashboard_rows = []
    monitor_rows = []
    logs = []
    errors = []

    for stock in watchlist:
        status = stock.get("status", "ready")
        message = stock.get("message", "")

        if status == "loading":
            dashboard_rows.append(build_loading_row(stock))
            logs.append(
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": f"{stock['name']}({stock['code']}) {message or '正在抓取最近7个交易日分时数据'}。",
                }
            )
            continue

        try:
            dashboard_row, monitor_row, signal_name, recent_signal_rows = process_stock(
                stock,
                fetch_days=INTRADAY_POLL_DAYS,
                reset_state=False,
                period=period,
            )
            monitor_rows.append(monitor_row)
            filtered_recent_rows = [
                row
                for row in recent_signal_rows
                if is_signal_enabled(row.get("signal"), rules)
            ]
            if filtered_recent_rows:
                dashboard_rows.extend(filtered_recent_rows)
            elif is_signal_enabled(signal_name, rules):
                dashboard_rows.append(dashboard_row)
            logs.append(
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": f"{stock['name']}({stock['code']}) 最新价格 {monitor_row['price']}，当前信号：{signal_name or '等待信号'}。",
                }
            )
        except Exception as exc:
            stock["status"] = "error"
            stock["message"] = f"轮询失败: {exc}"
            stock["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            errors.append(f"{stock['code']}: {exc}")
            dashboard_rows.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "signal": "暂无可用数据",
                    "price": "--",
                    "change": "--",
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "status": "处理失败",
                    "badge": "sell",
                    "tone": "sell",
                    "sortTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    save_json(WATCHLIST_PATH, watchlist)
    return {
        "brand": "监听助手",
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dashboardRows": sort_rows_by_time_desc(dashboard_rows),
        "monitorRows": sort_rows_by_time_desc(monitor_rows),
        "logs": logs[:6],
        "errors": errors,
    }


def process_pending_downloads(watchlist: list[dict]) -> list[dict]:
    rules = load_rules()
    period = get_signal_period(rules)
    changed = False
    for stock in watchlist:
        if stock.get("status") != "loading":
            continue

        try:
            append_debug_log(
                f"process_pending_downloads handling symbol={stock['code']}"
            )
            _, _, signal_name, recent_signal_rows = process_stock(
                stock,
                fetch_days=FETCH_DAYS,
                reset_state=True,
                period=period,
            )
            stock["status"] = "ready"
            stock["message"] = signal_name or "最近7个交易日未检测到触发信号"
            stock["lastProcessedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stock["updatedAt"] = stock["lastProcessedAt"]
            changed = True

            snapshot = build_snapshot(watchlist)
            if recent_signal_rows:
                merged_rows = sort_rows_by_time_desc(
                    [
                        row
                        for row in recent_signal_rows
                        if is_signal_enabled(row.get("signal"), rules)
                    ]
                    + snapshot["dashboardRows"]
                )
                snapshot["dashboardRows"] = merged_rows
            snapshot["logs"] = [
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": f"{stock['name']}({stock['code']}) 已完成7个交易日分时下载，最新结果：{stock['message']}。",
                }
            ] + snapshot["logs"]
            SNAPSHOT_PATH.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            append_debug_log(
                f"process_pending_downloads success symbol={stock['code']} message={stock['message']}"
            )
        except Exception as exc:
            stock["status"] = "error"
            stock["message"] = f"下载失败: {exc}"
            stock["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True
            append_debug_log(
                f"process_pending_downloads failed symbol={stock['code']} error={exc}"
            )

    if changed:
        save_json(WATCHLIST_PATH, watchlist)
    return watchlist


def loop() -> None:
    watchlist = ensure_watchlist()
    append_debug_log("loop started")
    while True:
        watchlist = normalize_watchlist(load_json(WATCHLIST_PATH, watchlist))
        loading_exists = any(item.get("status") == "loading" for item in watchlist)
        in_session = is_trading_time()
        append_debug_log(
            f"loop tick watchlist={len(watchlist)} loading_exists={loading_exists} in_session={in_session}"
        )

        if not loading_exists and not in_session:
            time.sleep(POLL_SECONDS)
            continue

        snapshot = build_snapshot(watchlist)
        SNAPSHOT_PATH.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if loading_exists:
            watchlist = process_pending_downloads(watchlist)
            snapshot = build_snapshot(watchlist)
            SNAPSHOT_PATH.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    loop()
