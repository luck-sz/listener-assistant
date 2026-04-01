import csv
from pathlib import Path
from typing import Any, cast

from pytdx.hq import TdxHq_API


HOSTS = [
    ("180.153.18.170", 7709),
    ("180.153.18.171", 7709),
    ("202.108.253.130", 7709),
]
BAR_CATEGORY_1MIN = 8
BAR_CATEGORY_5MIN = 0
MARKET_SH = 1
PAGE_SIZE = 800
PERIOD_CATEGORY_MAP = {
    "1分钟": BAR_CATEGORY_1MIN,
    "5分钟": BAR_CATEGORY_5MIN,
}


def fetch_quote(symbol: str, market: int) -> dict:
    last_error = None

    for host, port in HOSTS:
        api = TdxHq_API()
        try:
            if not api.connect(host, port):
                raise RuntimeError(f"connect failed for {host}:{port}")

            result = api.get_security_quotes([(market, symbol)])
            if not result:
                raise RuntimeError(f"empty quote for {symbol}")
            quote = result[0]
            return dict(quote) if isinstance(quote, dict) else dict(cast(Any, quote))
        except Exception as exc:
            last_error = exc
        finally:
            try:
                api.disconnect()
            except Exception:
                pass

    raise RuntimeError(f"Unable to fetch TDX quote: {last_error}")


def fetch_security_name(symbol: str, market: int) -> str | None:
    last_error = None

    for host, port in HOSTS:
        api = TdxHq_API()
        try:
            if not api.connect(host, port):
                raise RuntimeError(f"connect failed for {host}:{port}")

            count = int(api.get_security_count(market) or 0)
            start = 0
            while start < count:
                batch = cast(Any, api.get_security_list(market, start))
                if not batch:
                    break
                for item in batch:
                    item = (
                        dict(item) if isinstance(item, dict) else dict(cast(Any, item))
                    )
                    if item.get("code") == symbol:
                        name = f"{item.get('name', '')}".strip()
                        return name or None
                start += len(batch)
        except Exception as exc:
            last_error = exc
        finally:
            try:
                api.disconnect()
            except Exception:
                pass

    if last_error:
        raise RuntimeError(f"Unable to fetch security name: {last_error}")
    return None


def fetch_bars(
    symbol: str, market: int, days: int, period: str = "1分钟"
) -> list[dict]:
    last_error = None
    category = PERIOD_CATEGORY_MAP.get(period, BAR_CATEGORY_1MIN)

    for host, port in HOSTS:
        api = TdxHq_API()
        try:
            if not api.connect(host, port):
                raise RuntimeError(f"connect failed for {host}:{port}")

            all_rows = []
            seen_datetimes = set()
            start = 0

            while True:
                batch = cast(
                    Any,
                    api.get_security_bars(category, market, symbol, start, PAGE_SIZE),
                )
                if not batch:
                    break

                for item in batch:
                    item = (
                        dict(item) if isinstance(item, dict) else dict(cast(Any, item))
                    )
                    dt = item["datetime"]
                    if dt in seen_datetimes:
                        continue
                    seen_datetimes.add(dt)
                    all_rows.append(
                        {
                            "datetime": dt,
                            "open": item["open"],
                            "close": item["close"],
                            "high": item["high"],
                            "low": item["low"],
                            "volume": int(item["vol"]),
                            "amount": float(item["amount"]),
                        }
                    )

                unique_days = {row["datetime"].split(" ")[0] for row in all_rows}
                if len(unique_days) >= days:
                    break

                if len(batch) < PAGE_SIZE:
                    break

                start += PAGE_SIZE

            all_rows.sort(key=lambda row: row["datetime"])
            available_days = sorted({row["datetime"].split(" ")[0] for row in all_rows})
            if len(available_days) > days:
                keep_days = set(available_days[-days:])
                all_rows = [
                    row
                    for row in all_rows
                    if row["datetime"].split(" ")[0] in keep_days
                ]

            return all_rows
        except Exception as exc:
            last_error = exc
        finally:
            try:
                api.disconnect()
            except Exception:
                pass

    raise RuntimeError(f"Unable to fetch TDX minute bars: {last_error}")


def save_csv(rows: list[dict], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["datetime", "open", "close", "high", "low", "volume", "amount"],
        )
        writer.writeheader()
        writer.writerows(rows)
