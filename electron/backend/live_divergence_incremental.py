import csv
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9
MIN_PIVOT_GAP = 5
REALTIME_LOOKBACK = 20
SIGNAL_FIELDNAMES = [
    "signal",
    "pivot_time",
    "previous_pivot_time",
    "previous_price",
    "current_price",
    "previous_dif",
    "current_dif",
    "trigger_price",
    "same_day_low_after_trigger",
    "same_day_low_time",
    "max_t_profit_pct",
    "cross_type",
    "dif",
    "dea",
    "histogram",
]


@dataclass
class Bar:
    dt: datetime
    open: float
    close: float
    high: float
    low: float
    volume: int
    amount: float


@dataclass
class Candidate:
    index: int
    dt: str
    price: float
    dif: float


@dataclass
class MonitorState:
    bar_index: int = -1
    last_processed_dt: str | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    dea: float | None = None
    last_high_candidate: Candidate | None = None
    last_low_candidate: Candidate | None = None
    last_bearish_signal_index: int = -MIN_PIVOT_GAP
    last_bullish_signal_index: int = -MIN_PIVOT_GAP
    last_dif: float | None = None
    last_dea: float | None = None
    recent_bars: list[dict] = field(default_factory=list)


def load_bars(csv_path: Path) -> list[Bar]:
    bars = []
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            bars.append(
                Bar(
                    dt=datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M"),
                    open=float(row["open"]),
                    close=float(row["close"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    volume=int(float(row["volume"])),
                    amount=float(row["amount"]),
                )
            )
    return bars


def load_state(state_path: Path) -> MonitorState:
    if not state_path.exists():
        return MonitorState()

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    state = MonitorState(
        bar_index=payload["bar_index"],
        last_processed_dt=payload["last_processed_dt"],
        ema_fast=payload["ema_fast"],
        ema_slow=payload["ema_slow"],
        dea=payload["dea"],
        last_bearish_signal_index=payload["last_bearish_signal_index"],
        last_bullish_signal_index=payload["last_bullish_signal_index"],
        last_dif=payload.get("last_dif"),
        last_dea=payload.get("last_dea"),
        recent_bars=payload.get("recent_bars", []),
    )
    if payload.get("last_high_candidate"):
        state.last_high_candidate = Candidate(**payload["last_high_candidate"])
    if payload.get("last_low_candidate"):
        state.last_low_candidate = Candidate(**payload["last_low_candidate"])
    return state


def save_state(state: MonitorState, state_path: Path) -> None:
    payload = asdict(state)
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_completed_bars(bars: list[Bar]) -> list[Bar]:
    if len(bars) < 2:
        return []
    return bars[:-1]


def update_macd(state: MonitorState, close: float) -> tuple[float, float]:
    if state.ema_fast is None:
        state.ema_fast = close
        state.ema_slow = close
        dif = 0.0
        state.dea = 0.0
    else:
        assert state.ema_slow is not None
        assert state.dea is not None
        fast_multiplier = 2 / (FAST_PERIOD + 1)
        slow_multiplier = 2 / (SLOW_PERIOD + 1)
        signal_multiplier = 2 / (SIGNAL_PERIOD + 1)
        state.ema_fast = (close - state.ema_fast) * fast_multiplier + state.ema_fast
        state.ema_slow = (close - state.ema_slow) * slow_multiplier + state.ema_slow
        dif = state.ema_fast - state.ema_slow
        state.dea = (dif - state.dea) * signal_multiplier + state.dea
    assert state.dea is not None
    return dif, state.dea


def is_high_candidate(state: MonitorState, bar: Bar) -> bool:
    recent_highs = [item["high"] for item in state.recent_bars]
    return not recent_highs or bar.high >= max(recent_highs)


def is_low_candidate(state: MonitorState, bar: Bar) -> bool:
    recent_lows = [item["low"] for item in state.recent_bars]
    return not recent_lows or bar.low <= min(recent_lows)


def build_signal(
    signal_type: str,
    current_bar: Bar,
    previous_candidate: Candidate,
    current_price: float,
    current_dif: float,
) -> dict:
    return {
        "signal": signal_type,
        "pivot_time": current_bar.dt.strftime("%Y-%m-%d %H:%M"),
        "previous_pivot_time": previous_candidate.dt,
        "previous_price": f"{previous_candidate.price:.2f}",
        "current_price": f"{current_price:.2f}",
        "previous_dif": f"{previous_candidate.dif:.6f}",
        "current_dif": f"{current_dif:.6f}",
        "trigger_price": "",
        "same_day_low_after_trigger": "",
        "same_day_low_time": "",
        "max_t_profit_pct": "",
        "cross_type": "",
        "dif": "",
        "dea": "",
        "histogram": "",
    }


def build_cross_signal(
    signal_type: str, bar: Bar, dif: float, dea: float, cross_type: str
) -> dict:
    return {
        "signal": signal_type,
        "pivot_time": bar.dt.strftime("%Y-%m-%d %H:%M"),
        "previous_pivot_time": "",
        "previous_price": "",
        "current_price": f"{bar.close:.2f}",
        "previous_dif": "",
        "current_dif": "",
        "trigger_price": f"{bar.close:.2f}",
        "same_day_low_after_trigger": "",
        "same_day_low_time": "",
        "max_t_profit_pct": "",
        "cross_type": cross_type,
        "dif": f"{dif:.6f}",
        "dea": f"{dea:.6f}",
        "histogram": f"{(dif - dea) * 2:.6f}",
    }


def process_bar(state: MonitorState, bar: Bar, same_day_open: float) -> list[dict]:
    state.bar_index += 1
    previous_dif = state.last_dif
    previous_dea = state.last_dea
    dif, dea = update_macd(state, bar.close)
    signals = []

    if previous_dif is not None and previous_dea is not None:
        is_dead_cross = previous_dif >= previous_dea and dif < dea
        is_above_zero_axis = dif > 0 and dea > 0
        if is_dead_cross and is_above_zero_axis and bar.close > same_day_open:
            signals.append(
                build_cross_signal("macd_dead_cross_sell", bar, dif, dea, "dead_cross")
            )

        is_golden_cross = previous_dif <= previous_dea and dif > dea
        is_below_zero_axis = dif < 0 and dea < 0
        if is_golden_cross and is_below_zero_axis and bar.close < same_day_open:
            signals.append(
                build_cross_signal(
                    "macd_golden_cross_buy", bar, dif, dea, "golden_cross"
                )
            )

    if is_high_candidate(state, bar):
        previous = state.last_high_candidate
        if (
            previous is not None
            and state.bar_index - previous.index >= MIN_PIVOT_GAP
            and state.bar_index - state.last_bearish_signal_index >= MIN_PIVOT_GAP
            and bar.high > previous.price
            and dif < previous.dif
        ):
            signals.append(
                build_signal("bearish_divergence", bar, previous, bar.high, dif)
            )
            state.last_bearish_signal_index = state.bar_index

        state.last_high_candidate = Candidate(
            index=state.bar_index,
            dt=bar.dt.strftime("%Y-%m-%d %H:%M"),
            price=bar.high,
            dif=dif,
        )

    if is_low_candidate(state, bar):
        previous = state.last_low_candidate
        if (
            previous is not None
            and state.bar_index - previous.index >= MIN_PIVOT_GAP
            and state.bar_index - state.last_bullish_signal_index >= MIN_PIVOT_GAP
            and bar.low < previous.price
            and dif > previous.dif
        ):
            signals.append(
                build_signal("bullish_divergence", bar, previous, bar.low, dif)
            )
            state.last_bullish_signal_index = state.bar_index

        state.last_low_candidate = Candidate(
            index=state.bar_index,
            dt=bar.dt.strftime("%Y-%m-%d %H:%M"),
            price=bar.low,
            dif=dif,
        )

    recent = deque(state.recent_bars, maxlen=REALTIME_LOOKBACK - 1)
    recent.append(
        {"dt": bar.dt.strftime("%Y-%m-%d %H:%M"), "high": bar.high, "low": bar.low}
    )
    state.recent_bars = list(recent)
    state.last_processed_dt = bar.dt.strftime("%Y-%m-%d %H:%M")
    state.last_dif = dif
    state.last_dea = dea
    return signals


def rewrite_signals_file(output_path: Path) -> None:
    if not output_path.exists() or output_path.stat().st_size == 0:
        return

    with output_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        current_fieldnames = reader.fieldnames or []

    if current_fieldnames == SIGNAL_FIELDNAMES:
        return

    normalized_rows = []
    for row in rows:
        normalized_rows.append(
            {field: row.get(field, "") for field in SIGNAL_FIELDNAMES}
        )

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SIGNAL_FIELDNAMES)
        writer.writeheader()
        writer.writerows(normalized_rows)


def append_signals(signals: list[dict], output_path: Path) -> None:
    if not signals:
        return

    rewrite_signals_file(output_path)

    file_exists = output_path.exists() and output_path.stat().st_size > 0
    with output_path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SIGNAL_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(signals)


def replay_bars(
    bars: list[Bar], state_path: Path, output_path: Path
) -> tuple[int, int, int, list[dict]]:
    completed_bars = get_completed_bars(bars)
    state = load_state(state_path)
    day_open_map = {}
    for bar in completed_bars:
        day_open_map.setdefault(bar.dt.date(), bar.open)
    pending_signals = []
    processed = 0

    for bar in completed_bars:
        bar_dt = bar.dt.strftime("%Y-%m-%d %H:%M")
        if state.last_processed_dt and bar_dt <= state.last_processed_dt:
            continue
        pending_signals.extend(process_bar(state, bar, day_open_map[bar.dt.date()]))
        processed += 1

    append_signals(pending_signals, output_path)
    save_state(state, state_path)

    bullish = sum(
        1 for signal in pending_signals if signal["signal"] == "bullish_divergence"
    )
    bearish = sum(
        1 for signal in pending_signals if signal["signal"] == "bearish_divergence"
    )
    return processed, bullish, bearish, pending_signals
