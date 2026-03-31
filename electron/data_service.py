from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = APP_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_PROJECT = Path(r"E:\PythonProject\stock_intraday_fetch")
if str(SOURCE_PROJECT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PROJECT))

from fetch_tdx_intraday_30d import MARKET_SH, fetch_bars  # type: ignore  # noqa: E402
from live_divergence_incremental import load_bars, replay_bars  # type: ignore  # noqa: E402


MARKET_SZ = 0
POLL_SECONDS = 8
FETCH_DAYS = 30
INTRADAY_POLL_DAYS = 1
SNAPSHOT_PATH = RUNTIME_DIR / "live_snapshot.json"
WATCHLIST_PATH = RUNTIME_DIR / "watchlist.json"

DEFAULT_STOCKS = [
    {"code": "600519", "name": "贵州茅台"},
    {"code": "000858", "name": "五粮液"},
    {"code": "300750", "name": "宁德时代"},
    {"code": "000001", "name": "平安银行"},
    {"code": "601318", "name": "中国平安"},
]

SIGNAL_LABELS = {
    "bearish_divergence": "顶背离卖出",
    "bullish_divergence": "底背离买入",
    "macd_dead_cross_sell": "MACD死叉卖出",
    "macd_golden_cross_buy": "MACD金叉买入",
}


def infer_market(symbol: str) -> int:
    return MARKET_SH if symbol.startswith(("5", "6", "9")) else MARKET_SZ


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def process_stock(
    stock: dict, fetch_days: int, reset_state: bool = False
) -> tuple[dict, dict, str | None, list[dict]]:
    symbol = stock["code"]
    market = infer_market(symbol)
    rows = fetch_bars(symbol=symbol, market=market, days=fetch_days)
    if not rows:
        raise RuntimeError(f"empty rows for {symbol}")

    csv_path = RUNTIME_DIR / f"{symbol}_intraday.csv"
    state_path = RUNTIME_DIR / f"{symbol}_state.json"
    signal_path = RUNTIME_DIR / f"{symbol}_signals.csv"

    if reset_state:
        if state_path.exists():
            state_path.unlink()
        if signal_path.exists():
            signal_path.unlink()

    save_csv(rows, csv_path)
    replay_bars(load_bars(csv_path), state_path, signal_path)

    latest = rows[-1]
    today_rows = [
        row
        for row in rows
        if row["datetime"].split(" ")[0] == latest["datetime"].split(" ")[0]
    ]
    first_open = float(today_rows[0]["open"])
    last_close = float(latest["close"])
    change_pct = ((last_close - first_open) / first_open * 100) if first_open else 0.0
    change_text = f"{change_pct:+.2f}%"

    signal_rows = read_signal_rows(signal_path)
    last_signal = signal_rows[-1] if signal_rows else None
    signal_key = last_signal.get("signal") if last_signal else None
    signal_name = SIGNAL_LABELS.get(signal_key, signal_key) if signal_key else None
    status_text, tone = build_status(signal_name, stock.get("status", "ready"))
    badge = build_badge(signal_name)
    signal_text = signal_name or "等待信号"
    signal_time = last_signal.get("pivot_time") if last_signal else latest["datetime"]
    signal_time = signal_time or latest["datetime"]
    display_time = signal_time[11:19] if len(signal_time) >= 19 else signal_time[-8:]

    dashboard_row = {
        "code": symbol,
        "name": stock["name"],
        "signal": signal_text,
        "time": display_time,
        "status": status_text,
        "badge": badge,
        "tone": tone,
        "sortTime": signal_time,
    }
    monitor_row = {
        "code": symbol,
        "name": stock["name"],
        "price": f"{last_close:.2f}",
        "change": change_text,
        "signal": signal_text,
        "time": latest["datetime"][-5:],
        "fullTime": latest["datetime"],
    }

    recent_signal_rows = []
    for item in reversed(signal_rows[-6:]):
        raw_signal = item.get("signal") or ""
        label = SIGNAL_LABELS.get(raw_signal, raw_signal or "等待信号")
        recent_signal_rows.append(
            {
                "code": symbol,
                "name": stock["name"],
                "signal": label,
                "time": (item.get("pivot_time", "") or "")[11:19],
                "status": build_status(label, "ready")[0],
                "badge": build_badge(label),
                "tone": build_status(label, "ready")[1],
                "sortTime": item.get("pivot_time", ""),
            }
        )

    return dashboard_row, monitor_row, signal_name, recent_signal_rows


def build_loading_row(stock: dict) -> dict:
    return {
        "code": stock["code"],
        "name": stock["name"],
        "signal": "正在下载最近30个交易日分时数据",
        "time": datetime.now().strftime("%H:%M:%S"),
        "status": "下载中",
        "badge": "neutral",
        "tone": "neutral",
        "sortTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def build_snapshot(watchlist: list[dict]) -> dict:
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
                    "text": f"{stock['name']}({stock['code']}) {message or '正在抓取最近30个交易日分时数据'}。",
                }
            )
            continue

        try:
            dashboard_row, monitor_row, signal_name, _ = process_stock(
                stock,
                fetch_days=INTRADAY_POLL_DAYS,
                reset_state=False,
            )
            dashboard_rows.append(dashboard_row)
            monitor_rows.append(monitor_row)
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
    changed = False
    for stock in watchlist:
        if stock.get("status") != "loading":
            continue

        try:
            _, _, signal_name, recent_signal_rows = process_stock(
                stock,
                fetch_days=FETCH_DAYS,
                reset_state=True,
            )
            stock["status"] = "ready"
            stock["message"] = signal_name or "最近30个交易日未检测到触发信号"
            stock["lastProcessedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            stock["updatedAt"] = stock["lastProcessedAt"]
            changed = True

            snapshot = build_snapshot(watchlist)
            if recent_signal_rows:
                merged_rows = sort_rows_by_time_desc(
                    recent_signal_rows + snapshot["dashboardRows"]
                )
                snapshot["dashboardRows"] = merged_rows
            snapshot["logs"] = [
                {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "text": f"{stock['name']}({stock['code']}) 已完成30个交易日分时下载，最新结果：{stock['message']}。",
                }
            ] + snapshot["logs"]
            SNAPSHOT_PATH.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            stock["status"] = "error"
            stock["message"] = f"下载失败: {exc}"
            stock["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True

    if changed:
        save_json(WATCHLIST_PATH, watchlist)
    return watchlist


def loop() -> None:
    watchlist = ensure_watchlist()
    while True:
        watchlist = normalize_watchlist(load_json(WATCHLIST_PATH, watchlist))
        loading_exists = any(item.get("status") == "loading" for item in watchlist)

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
