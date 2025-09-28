from datetime import datetime
from pathlib import Path

from RZQ_strategy import IceLeaderDTB, RZQLeaderAnomaly
from vnpy_ctastrategy.backtesting import BacktestingEngine

from vnpy.alpha import AlphaLab
from vnpy.trader.constant import Interval
from vnpy.trader.database import get_database

LAB_TASK = "csi300"
LAB_ROOT = Path(__file__).resolve().parent / "lab" / LAB_TASK


def ensure_lab_bars(
    vt_symbol: str,
    interval: Interval,
    start: datetime,
    end: datetime,
) -> int:
    if not LAB_ROOT.exists():
        raise FileNotFoundError(f"未找到 AlphaLab 目录：{LAB_ROOT}")

    lab = AlphaLab(str(LAB_ROOT))
    bars = lab.load_bar_data(vt_symbol, interval, start, end)
    if not bars:
        folder = "minute" if interval == Interval.MINUTE else "daily"
        file_path = LAB_ROOT / folder / f"{vt_symbol}.parquet"
        raise RuntimeError(
            f"AlphaLab 缺少 {vt_symbol} {interval.name} 数据，请先生成：{file_path}"
        )

    database = get_database()
    database.save_bar_data(bars)
    return len(bars)


def backtest_rzq(vt_symbol: str):
    engine = BacktestingEngine()
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2025, 8, 1)
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=Interval.MINUTE,
        start=start_dt,
        end=end_dt,
        rate=0.00025,
        slippage=0.01,
        size=100,
        pricetick=0.01,
        capital=1_000_000,
    )

    inserted = ensure_lab_bars(vt_symbol, Interval.MINUTE, start_dt, end_dt)
    print(f"同步 AlphaLab 数据 {vt_symbol} ({Interval.MINUTE.name})：{inserted} 条")

    engine.load_data()
    setting = dict(
        fast=10,
        slow=30,
        vol_n=60,
        rs_n=20,
        ret_n=5,
        limit_pct=0.10,
        price_tick=0.01,
        base_lots=3,
        add_lots=2,
        min_turnover=1.5e8,
        max_spread_tick=3,
        open_cutoff=1.03,
        avoid_near_up_tick=2,
        use_rzq=True,
        use_lead_retest=True,
        use_anomaly=True,
        rzq_shrink_days=2,
        rzq_shrink_ratio=0.75,
        rzq_break_ma=True,
        rzq_volume_confirm=1.2,
        lead_min_ret=0.20,
        lead_pull_to_ma=10,
        lead_shrink_ratio=0.8,
        lead_rebound_confirm=1.01,
        anom_vol_ratio=2.0,
        anom_close_above_yh=True,
        anom_near_uplimit_tick=10,
        anom_probe_ratio=0.5,
        anom_add_trigger=0.5,
        use_market_risk=True,
        use_sector_risk=True,
        market_csv="market_proxy.csv",
        sector_csv="sector_proxy.csv",
        mkt_ma_n=20,
        mkt_dd=0.06,
        mkt_dd_n=60,
        mkt_vol_ratio=0.8,
        sec_ma_n=10,
        sec_mom_n1=5,
        sec_mom_n2=10,
        sec_dd=0.08,
        sec_dd_n=60,
        use_dipbuy=True,
        dip_start="14:30:00",
        dip_end="14:55:00",
        dip_ref="EMA20",
        dip_band=0.002,
        dip_vol_shrink=0.7,
        dip_probe_lots=2,
        dip_add_last5m=True,
        dip_add_lots=1,
        atr_n=14,
        hard_sl_atr=1.8,
        trail_atr=2.5,
        t1_sell_start="09:30:00",
        t1_sell_end="10:30:00",
        gap_down_cut=0.02,
        gap_up_half=0.02,
    )
    engine.add_strategy(RZQLeaderAnomaly, setting)
    engine.run_backtesting()
    df = engine.calculate_result()
    stats = engine.calculate_statistics()
    if stats:
        print("RZQ stats:", stats)
    else:
        print("RZQ stats: 无有效逐日结果，请检查行情数据")
    engine.show_chart()


def backtest_ice(vt_symbol: str):
    engine = BacktestingEngine()
    start_dt = datetime(2024, 1, 1)
    end_dt = datetime(2025, 8, 1)
    engine.set_parameters(
        vt_symbol=vt_symbol,
        interval=Interval.MINUTE,
        start=start_dt,
        end=end_dt,
        rate=0.00025,
        slippage=0.02,
        size=100,
        pricetick=0.01,
        capital=1_000_000,
    )

    inserted = ensure_lab_bars(vt_symbol, Interval.MINUTE, start_dt, end_dt)
    print(f"同步 AlphaLab 数据 {vt_symbol} ({Interval.MINUTE.name})：{inserted} 条")

    engine.load_data()
    setting = dict(
        limit_pct=0.10,
        price_tick=0.01,
        market_csv="market_proxy.csv",
        sector_csv="sector_proxy.csv",
        sentiment_csv="sentiment_proxy.csv",
        mkt_ma_n=20,
        mkt_dd_n=60,
        mkt_dd=0.06,
        mkt_vol_ratio=0.8,
        sec_ma_n=10,
        lim_up_max=10,
        lim_dn_min=5,
        adv_dec_max=0.5,
        near_dn_ticks=2,
        rebound_ticks=5,
        vol_ratio=2.0,
        vol_n=20,
        confirm_ref="EMA5",
        base_lots=3,
        add_on_uplift=False,
        dtb_by_close=True,
        near_up_ticks=2,
        lowopen_sell_mode="sell_open",
        t1_watch_end="10:30:00",
        avoid_chasing_upper=True,
        late_reduce_if_uprun=True,
    )
    engine.add_strategy(IceLeaderDTB, setting)
    engine.run_backtesting()
    df = engine.calculate_result()
    stats = engine.calculate_statistics()
    if stats:
        print("ICE stats:", stats)
    else:
        print("ICE stats: 无有效逐日结果，请检查行情数据")
    engine.show_chart()


if __name__ == "__main__":
    backtest_rzq("002572.SZSE")
    backtest_ice("002572.SZSE")
