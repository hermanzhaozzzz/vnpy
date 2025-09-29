"""TuShare 数据抓取封装（mytest 定制版本）。

提供功能：
- 指数成分获取（index_weight），并可扩展为日度映射。
- 股票日线、分钟线 K 线抓取，并转换为 vn.py BarData。

注意事项：
- 需设置 TuShare Token（优先从环境变量 TS_TOKEN 读取），或在初始化时显式传入 token。
- TuShare 返回的成交量、成交额单位可能与本地定义存在差异，必要时在下游做换算。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import os
from typing import Iterable

import pandas as pd

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.alpha import logger


def _to_yyyymmdd(dt: datetime | str) -> str:
    """将 datetime/字符串转换为 TuShare 需要的 YYYYMMDD。"""
    if isinstance(dt, str):
        value = dt.replace("-", "")
        if len(value) == 8:
            return value
        msg = f"无法解析日期字符串: {dt}"
        raise ValueError(msg)
    return dt.strftime("%Y%m%d")


def ts_to_vt_symbol(ts_code: str) -> str:
    """TuShare ts_code → vt_symbol（例：000001.SZ → 000001.SZSE）。"""
    symbol, suffix = ts_code.split(".")
    if suffix == "SZ":
        exchange = "SZSE"
    elif suffix == "SH":
        exchange = "SSE"
    else:
        exchange = suffix
    return f"{symbol}.{exchange}"


def vt_to_ts_code(vt_symbol: str) -> str:
    """vt_symbol → TuShare ts_code（例：000001.SZSE → 000001.SZ）。"""
    symbol, exchange = vt_symbol.split(".")
    if exchange == "SZSE":
        suffix = "SZ"
    elif exchange == "SSE":
        suffix = "SH"
    else:
        suffix = exchange
    return f"{symbol}.{suffix}"


def vt_to_exchange(vt_symbol: str) -> Exchange:
    """提取 vt_symbol 的交易所枚举。"""
    _, exchange = vt_symbol.split(".")
    if exchange == "SSE":
        return Exchange.SSE
    if exchange == "SZSE":
        return Exchange.SZSE
    try:
        return Exchange(exchange)
    except Exception:  # noqa: BLE001
        return Exchange.GLOBAL


@dataclass
class TushareClient:
    token: str | None = None

    def __post_init__(self) -> None:
        try:
            import tushare as ts  # noqa: WPS433
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "未安装 tushare，请先通过 poetry 添加依赖并安装。"
            ) from exc

        ts_token = self.token or os.getenv("TS_TOKEN")
        if not ts_token:
            raise RuntimeError("未找到 TuShare Token，请设置环境变量 TS_TOKEN 或在初始化时传入 token")

        ts.set_token(ts_token)
        self._pro = ts.pro_api(ts_token)
        self._ts = ts

    # --------------------------- 指数成分 ---------------------------
    def fetch_index_components(
        self,
        index_vt_symbol: str,
        start: datetime | str,
        end: datetime | str,
        expand_daily: bool = True,
    ) -> dict[datetime, list[str]]:
        """获取指数成分映射，必要时展开为日度。"""
        index_code = vt_to_ts_code(index_vt_symbol)
        start_s = _to_yyyymmdd(start)
        end_s = _to_yyyymmdd(end)

        df = self._pro.index_weight(index_code=index_code, start_date=start_s, end_date=end_s)
        if df is None or df.empty:
            logger.warning(f"TuShare index_weight 空结果: {index_vt_symbol} {start_s}~{end_s}")
            return {}

        df = df[["trade_date", "con_code"]].dropna().copy()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df["vt_symbol"] = df["con_code"].map(ts_to_vt_symbol)

        grouped = df.groupby("trade_date")["vt_symbol"].apply(lambda series: sorted(set(series.tolist())))

        if not expand_daily:
            return {dt.to_pydatetime(): symbols for dt, symbols in grouped.items()}

        dates = sorted(grouped.index.to_list())
        if not dates:
            return {}

        start_dt = pd.to_datetime(start_s)
        end_dt = pd.to_datetime(end_s)
        current_symbols: list[str] = grouped.loc[dates[0]]

        result: dict[datetime, list[str]] = {}
        cursor = start_dt
        idx = 0
        while cursor <= end_dt:
            while idx + 1 < len(dates) and cursor >= dates[idx + 1]:
                idx += 1
                current_symbols = grouped.loc[dates[idx]]
            result[cursor.to_pydatetime()] = current_symbols
            cursor += timedelta(days=1)
        return result

    # --------------------------- K 线数据 ---------------------------
    def fetch_equity_daily(
        self,
        vt_symbol: str,
        start: datetime | str,
        end: datetime | str,
    ) -> list[BarData]:
        """获取股票日线数据并转换为 BarData 列表。"""
        ts_code = vt_to_ts_code(vt_symbol)
        start_s = _to_yyyymmdd(start)
        end_s = _to_yyyymmdd(end)

        df = self._pro.daily(ts_code=ts_code, start_date=start_s, end_date=end_s)
        if df is None or df.empty:
            logger.warning(f"TuShare daily 空结果: {vt_symbol} {start_s}~{end_s}")
            return []

        df = df.sort_values("trade_date")
        exchange = vt_to_exchange(vt_symbol)
        symbol = vt_symbol.split(".")[0]

        bars: list[BarData] = []
        for _, row in df.iterrows():
            dt = datetime.strptime(str(row["trade_date"]), "%Y%m%d")
            bars.append(
                BarData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt,
                    interval=Interval.DAILY,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=float(row.get("vol", 0.0)),
                    turnover=float(row.get("amount", 0.0)),
                    open_interest=0.0,
                    gateway_name="TuShare",
                )
            )
        return bars

    def fetch_equity_minute(
        self,
        vt_symbol: str,
        start: datetime | str,
        end: datetime | str,
        freq: str = "1min",
        adj: str | None = None,
    ) -> list[BarData]:
        """获取股票分钟线（依赖 TuShare pro_bar）。"""
        ts_code = vt_to_ts_code(vt_symbol)
        start_s = _to_yyyymmdd(start)
        end_s = _to_yyyymmdd(end)

        try:
            df = self._ts.pro_bar(
                ts_code=ts_code,
                start_date=start_s,
                end_date=end_s,
                freq=freq,
                adj=adj,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"TuShare pro_bar 调用失败: {vt_symbol} {start_s}~{end_s} {freq} {adj}: {exc}"
            )
            return []

        if df is None or df.empty:
            logger.warning(f"TuShare pro_bar 空结果: {vt_symbol} {start_s}~{end_s} {freq}")
            return []

        time_col = "trade_time" if "trade_time" in df.columns else "datetime"
        df = df.sort_values(time_col)
        exchange = vt_to_exchange(vt_symbol)
        symbol = vt_symbol.split(".")[0]

        bars: list[BarData] = []
        for _, row in df.iterrows():
            dt = pd.to_datetime(row[time_col]).to_pydatetime()
            bars.append(
                BarData(
                    symbol=symbol,
                    exchange=exchange,
                    datetime=dt,
                    interval=Interval.MINUTE,
                    open_price=float(row["open"]),
                    high_price=float(row["high"]),
                    low_price=float(row["low"]),
                    close_price=float(row["close"]),
                    volume=float(row.get("vol", 0.0)),
                    turnover=float(row.get("amount", 0.0)),
                    open_interest=0.0,
                    gateway_name="TuShare",
                )
            )
        return bars

    # --------------------------- 批量工具 ---------------------------
    def fetch_equity_daily_bulk(
        self,
        vt_symbols: Iterable[str],
        start: datetime | str,
        end: datetime | str,
    ) -> dict[str, list[BarData]]:
        """批量抓取多个股票的日线数据。"""
        result: dict[str, list[BarData]] = {}
        for vt_symbol in vt_symbols:
            result[vt_symbol] = self.fetch_equity_daily(vt_symbol, start, end)
        return result
