# 文件：combo_strategies.py
# 含两个策略类：
# 1) RZQLeaderAnomaly —— 弱转强 + 龙头反抽 + 卡异动 + 尾盘低吸 + ATR追踪 + 大盘/板块风控
# 2) IceLeaderDTB      —— 冰点日总龙头 抢跌停→地天板（T+1：竞价低开排跌停/开盘清仓；高开格局，破昨收清仓）
from __future__ import annotations

import csv
import math
from datetime import time as ptime
from pathlib import Path

import numpy as np
from vnpy_ctastrategy import ArrayManager, CtaTemplate
from vnpy.trader.object import BarData


# ------------------ 公共工具 ------------------
def _round_lots(shares: int) -> int:
    lots = max(1, shares // 100)
    return lots * 100


def _load_daily_csv(path: str):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            ds = row["date"].strip()[:10]
            close = float(row.get("close", 0) or 0)
            vol = float(row.get("volume", 0) or 0)
            dct = {"date": ds, "close": close, "volume": vol}
            # 情绪CSV兼容
            for k in ("lim_up", "lim_dn", "adv", "dec"):
                if k in row:
                    dct[k] = float(row.get(k) or 0)
            out.append(dct)
    return out


def _rolling_ma(arr, n):
    if n <= 0 or len(arr) < n:
        return None
    return float(np.mean(arr[-n:]))


def _rolling_max(arr, n):
    if n <= 0 or len(arr) < n:
        return None
    return float(np.max(arr[-n:]))


def _calc_limit_prices(prev_close: float, limit_pct: float, price_tick: float):
    if prev_close <= 0:
        return 0.0, 0.0
    up = math.floor(prev_close * (1 + limit_pct) / price_tick) * price_tick
    dn = math.ceil(prev_close * (1 - limit_pct) / price_tick) * price_tick
    return round(up, 2), round(dn, 2)


def _parse_time(s: str) -> ptime:
    h, m, sec = [int(x) for x in s.split(":")]
    return ptime(hour=h, minute=m, second=sec)


# ------------------ 策略 1：RZQLeaderAnomaly ------------------
class RZQLeaderAnomaly(CtaTemplate):
    author = "Huanan"

    # ===== 数据/窗口 =====
    fast = 10
    slow = 30
    vol_n = 60
    rs_n = 20
    ret_n = 5
    limit_pct = 0.10
    price_tick = 0.01

    # ===== 交易与风控 =====
    base_lots = 3
    add_lots = 2
    min_turnover = 1.5e8
    max_spread_tick = 3
    open_cutoff = 1.03
    avoid_near_up_tick = 2

    allow_open_start = ptime(9, 35)
    allow_open_end = ptime(14, 50)

    # ===== 子信号 =====
    use_rzq = True
    use_lead_retest = True
    use_anomaly = True

    # RZQ
    rzq_shrink_days = 2
    rzq_shrink_ratio = 0.75
    rzq_break_ma = True
    rzq_volume_confirm = 1.2

    # 龙头反抽
    lead_min_ret = 0.20
    lead_pull_to_ma = 10
    lead_shrink_ratio = 0.8
    lead_rebound_confirm = 1.01

    # 卡异动
    anom_vol_ratio = 2.0
    anom_close_above_yh = True
    anom_near_uplimit_tick = 10
    anom_probe_ratio = 0.5
    anom_add_trigger = 0.5

    # ===== 大盘/板块风控 =====
    use_market_risk = True
    use_sector_risk = True
    market_csv = "market_proxy.csv"
    sector_csv = "sector_proxy.csv"
    mkt_ma_n = 20
    mkt_dd = 0.06
    mkt_dd_n = 60
    mkt_vol_ratio = 0.8
    sec_ma_n = 10
    sec_mom_n1 = 5
    sec_mom_n2 = 10
    sec_dd = 0.08
    sec_dd_n = 60

    # ===== 尾盘低吸 + ATR波段 =====
    use_dipbuy = True
    dip_start = "14:30:00"
    dip_end = "14:55:00"
    dip_ref = "EMA20"  # EMA20/VWAP
    dip_band = 0.002
    dip_vol_shrink = 0.7
    dip_probe_lots = 2
    dip_add_last5m = True
    dip_add_lots = 1

    atr_n = 14
    hard_sl_atr = 1.8
    trail_atr = 2.5
    t1_sell_start = "09:30:00"
    t1_sell_end = "10:30:00"
    gap_down_cut = 0.02
    gap_up_half = 0.02

    parameters = [
        "fast",
        "slow",
        "vol_n",
        "rs_n",
        "ret_n",
        "limit_pct",
        "price_tick",
        "base_lots",
        "add_lots",
        "min_turnover",
        "max_spread_tick",
        "open_cutoff",
        "avoid_near_up_tick",
        "allow_open_start",
        "allow_open_end",
        "use_rzq",
        "use_lead_retest",
        "use_anomaly",
        "rzq_shrink_days",
        "rzq_shrink_ratio",
        "rzq_break_ma",
        "rzq_volume_confirm",
        "lead_min_ret",
        "lead_pull_to_ma",
        "lead_shrink_ratio",
        "lead_rebound_confirm",
        "anom_vol_ratio",
        "anom_close_above_yh",
        "anom_near_uplimit_tick",
        "anom_probe_ratio",
        "anom_add_trigger",
        "use_market_risk",
        "use_sector_risk",
        "market_csv",
        "sector_csv",
        "mkt_ma_n",
        "mkt_dd",
        "mkt_dd_n",
        "mkt_vol_ratio",
        "sec_ma_n",
        "sec_mom_n1",
        "sec_mom_n2",
        "sec_dd",
        "sec_dd_n",
        "use_dipbuy",
        "dip_start",
        "dip_end",
        "dip_ref",
        "dip_band",
        "dip_vol_shrink",
        "dip_probe_lots",
        "dip_add_last5m",
        "dip_add_lots",
        "atr_n",
        "hard_sl_atr",
        "trail_atr",
        "t1_sell_start",
        "t1_sell_end",
        "gap_down_cut",
        "gap_up_half",
    ]
    variables = [
        "pos",
        "inited",
        "fast_ma",
        "slow_ma",
        "atr",
        "entry_price",
        "entry_date",
        "probe_price",
        "hh_since_entry",
        "mkt_ok",
        "sec_ok",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        win = max(self.slow, self.vol_n, self.rs_n, self.ret_n, 120) + 20
        self.am = ArrayManager(win)

        self.fast_ma = 0.0
        self.slow_ma = 0.0
        self.atr = 0.0

        self.entry_price = 0.0
        self.entry_date: object | None = None
        self.probe_price = 0.0
        self.hh_since_entry = 0.0

        self.mkt_ok = True
        self.sec_ok = True

        self.today_turnover = 0.0
        self.today_date = None

        # 风险 CSV
        self._mkt = _load_daily_csv(self.market_csv)
        self._sec = _load_daily_csv(self.sector_csv)
        self._mkt_dates = [d["date"] for d in self._mkt]
        self._mkt_close = [d["close"] for d in self._mkt]
        self._mkt_vol = [d["volume"] for d in self._mkt]
        self._sec_dates = [d["date"] for d in self._sec]
        self._sec_close = [d["close"] for d in self._sec]
        self._sec_vol = [d["volume"] for d in self._sec]

        self._t1_open = _parse_time(self.t1_sell_start)
        self._t1_close = _parse_time(self.t1_sell_end)
        self._dip_t0 = _parse_time(self.dip_start)
        self._dip_t1 = _parse_time(self.dip_end)

    def on_init(self):
        self.load_bar(400)

    def on_start(self):
        self.write_log("RZQLeaderAnomaly started")

    def on_stop(self):
        self.write_log("stopped")

    def on_bar(self, bar: BarData):
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        dt = bar.datetime
        d = dt.date()
        t = dt.time()
        dstr = dt.strftime("%Y-%m-%d")

        # 粗估成交额
        if self.today_date != d:
            self.today_date = d
            self.today_turnover = 0.0
        self.today_turnover += float(bar.close_price) * float(bar.volume)

        # 风险刷新
        self._update_risk(dstr)

        # 指标
        self.fast_ma = am.sma(self.fast, array=False)
        self.slow_ma = am.sma(self.slow, array=False)
        self.atr = am.atr(self.atr_n, array=False) or 0.0
        ema20 = self._ema(am.close, 20)
        vwap = self._vwap(am, 120)
        ref = ema20 if (self.dip_ref.upper() == "EMA20") else vwap

        prev_close = am.close[-2]
        up_lim, dn_lim = _calc_limit_prices(prev_close, self.limit_pct, self.price_tick)
        yh = am.high[-2]

        # 过滤
        allow_open = self.allow_open_start <= t <= self.allow_open_end
        risk_open_ok = ((not self.use_market_risk) or self.mkt_ok) and (
            (not self.use_sector_risk) or self.sec_ok
        )
        if bar.close_price >= up_lim - self.avoid_near_up_tick * self.price_tick:
            return
        if bar.close_price <= dn_lim + self.avoid_near_up_tick * self.price_tick:
            return
        if (bar.high_price - bar.low_price) / max(
            self.price_tick, bar.close_price
        ) > self.max_spread_tick:
            return

        open_ratio = bar.open_price / prev_close if prev_close > 0 else 1.0
        if open_ratio > self.open_cutoff and self.pos == 0:
            return

        can_sell_today = (self.entry_date is not None) and (d > self.entry_date)

        # --- 波段化风控 ---
        if self.pos > 0:
            self.hh_since_entry = max(self.hh_since_entry, bar.close_price)
            atr = max(self.atr, self.price_tick)
            hard_sl = self.entry_price - self.hard_sl_atr * atr
            if bar.close_price <= hard_sl and can_sell_today:
                self.sell(bar.close_price, self.pos)
                return
            trail_line = self.hh_since_entry - self.trail_atr * atr
            if bar.close_price <= trail_line and can_sell_today:
                self.sell(bar.close_price, self.pos)
                return

        # --- 次日早盘分批兑现 ---
        if self.pos > 0 and can_sell_today and (self._t1_open <= t <= self._t1_close):
            prev_close2 = am.close[-2]
            open_ratio2 = bar.open_price / prev_close2 if prev_close2 > 0 else 1.0
            half_qty = max(100, self.pos // 2)
            if open_ratio2 <= (1 - self.gap_down_cut):
                self.sell(bar.close_price, half_qty)
            elif open_ratio2 >= (1 + self.gap_up_half):
                self.sell(bar.close_price, half_qty)
            else:
                cond_spike = (bar.high_price >= yh) or (
                    bar.close_price >= self.hh_since_entry * 1.01
                )
                if cond_spike:
                    self.sell(bar.close_price, half_qty)

        # --- 入场 1：RZQ ---
        if self.use_rzq and self.pos == 0 and allow_open and risk_open_ok:
            if self._sig_rzq(am, bar, yh):
                qty = _round_lots(self.base_lots * 100)
                self.buy(bar.close_price, qty)
                self.entry_price = bar.close_price
                self.entry_date = d
                self.probe_price = 0.0
                self.hh_since_entry = bar.close_price
                return

        # --- 入场 2：龙头反抽 ---
        if self.use_lead_retest:
            if self.pos == 0 and allow_open and risk_open_ok:
                if self._sig_lead_retest(am, bar):
                    qty = _round_lots(self.base_lots * 100)
                    self.buy(bar.close_price, qty)
                    self.entry_price = bar.close_price
                    self.entry_date = d
                    self.probe_price = 0.0
                    self.hh_since_entry = bar.close_price
                    return
            elif (
                self.pos > 0
                and bar.close_price > self.fast_ma
                and bar.volume >= np.mean(am.volume[-self.vol_n :]) * 1.2
            ):
                add_qty = _round_lots(self.add_lots * 100)
                self.buy(bar.close_price, add_qty)
                return

        # --- 入场 3：卡异动 ---
        if self.use_anomaly and allow_open and risk_open_ok:
            if self.pos == 0:
                if self._sig_anomaly_probe(am, bar, yh, up_lim):
                    probe_qty = _round_lots(
                        int(self.base_lots * 100 * self.anom_probe_ratio)
                    )
                    probe_qty = max(100, probe_qty)
                    self.buy(bar.close_price, probe_qty)
                    self.entry_price = bar.close_price
                    self.entry_date = d
                    self.probe_price = bar.close_price
                    self.hh_since_entry = bar.close_price
                    return
            else:
                if (
                    self.probe_price > 0
                    and (bar.close_price / self.probe_price - 1.0)
                    >= self.anom_add_trigger / 100.0
                    and bar.volume >= np.mean(am.volume[-self.vol_n :]) * 1.2
                ):
                    add_qty = _round_lots(self.add_lots * 100)
                    self.buy(bar.close_price, add_qty)
                    self.probe_price = 0.0
                    return

        # --- 入场 4：尾盘低吸 ---
        if (
            self.use_dipbuy
            and self.pos == 0
            and (self._dip_t0 <= t <= self._dip_t1)
            and risk_open_ok
            and ref
        ):
            near_ref = bar.close_price <= ref * (1 + self.dip_band)
            vol_ma20 = float(np.mean(am.volume[-20:])) if am.count >= 20 else bar.volume
            vol_ok = bar.volume <= vol_ma20 * self.dip_vol_shrink
            body = abs(bar.close_price - bar.open_price)
            lower_shadow = min(bar.open_price, bar.close_price) - bar.low_price
            hammer_like = (bar.close_price > bar.open_price) and (
                lower_shadow >= 0.5 * max(body, self.price_tick)
            )
            if near_ref and vol_ok and hammer_like:
                qty = _round_lots(self.dip_probe_lots * 100)
                self.buy(bar.close_price, qty)
                self.entry_price = bar.close_price
                self.entry_date = d
                self.probe_price = 0.0
                self.hh_since_entry = bar.close_price
                return

        # 尾盘最后5分钟加一笔
        if (
            self.use_dipbuy
            and self.pos > 0
            and t >= ptime(14, 55)
            and self.dip_add_last5m
            and ref
        ):
            vol_ma20 = float(np.mean(am.volume[-20:])) if am.count >= 20 else bar.volume
            if vol_ma20 > 0 and bar.volume >= vol_ma20 * 1.2 and bar.close_price > ref:
                add_qty = _round_lots(self.dip_add_lots * 100)
                self.buy(bar.close_price, add_qty)
                return

        # 均线反转兜底
        if self.pos > 0 and can_sell_today and (self.fast_ma < self.slow_ma):
            self.sell(bar.close_price, self.pos)
            return

    # --- 子信号细节 ---
    def _sig_rzq(self, am: ArrayManager, bar: BarData, yh: float) -> bool:
        vol_avg = float(np.mean(am.volume[-self.vol_n :]))
        if not (
            am.volume[-1] <= vol_avg * self.rzq_shrink_ratio
            and am.volume[-2] <= vol_avg * self.rzq_shrink_ratio
        ):
            return False
        base_ref = yh
        two_mean = (am.close[-1] + am.close[-2]) / 2
        if two_mean < base_ref * 0.97:
            return False
        cross_up = am.sma(self.fast, array=False) > am.sma(self.slow, array=False)
        if self.rzq_break_ma and (not cross_up):
            return False
        if bar.volume < vol_avg * self.rzq_volume_confirm:
            return False
        if bar.close_price <= self.slow_ma:
            return False
        return True

    def _sig_lead_retest(self, am: ArrayManager, bar: BarData) -> bool:
        if am.count <= self.ret_n:
            return False
        base = am.close[-self.ret_n]
        if base <= 0:
            return False
        max_ret = float(np.max(am.close[-self.ret_n :])) / base - 1.0
        if max_ret < self.lead_min_ret:
            return False
        ma5 = am.sma(5, array=False)
        ma10 = am.sma(10, array=False)
        target_ma = ma10 if self.lead_pull_to_ma >= 10 else ma5
        if not (am.close[-2] <= target_ma * 1.003):
            return False
        vol_avg = float(np.mean(am.volume[-self.vol_n :]))
        if am.volume[-2] > vol_avg * self.lead_shrink_ratio:
            return False
        rebound1 = bar.close_price >= am.high[-2] * self.lead_rebound_confirm
        rebound2 = (bar.close_price > ma5) and (bar.close_price > ma10)
        return bool(rebound1 or rebound2)

    def _sig_anomaly_probe(
        self, am: ArrayManager, bar: BarData, yh: float, up_lim: float
    ) -> bool:
        vol_avg = float(np.mean(am.volume[-self.vol_n :]))
        vol_ok = bar.volume >= vol_avg * self.anom_vol_ratio
        near_uplimit = (
            up_lim - bar.close_price
        ) <= self.anom_near_uplimit_tick * self.price_tick
        not_too_near = (
            up_lim - bar.close_price
        ) > self.avoid_near_up_tick * self.price_tick
        cond_price = bar.close_price > yh if self.anom_close_above_yh else True
        return cond_price and vol_ok and near_uplimit and not_too_near

    # --- 风险计算 ---
    def _idx(self, dstr, dates):
        idx = None
        for i, ds in enumerate(dates):
            if ds <= dstr:
                idx = i
            else:
                break
        return idx

    def _update_risk(self, dstr: str):
        # 大盘
        i = self._idx(dstr, self._mkt_dates)
        self.mkt_ok = True
        if i is not None:
            cl = self._mkt_close[: i + 1]
            vl = self._mkt_vol[: i + 1]
            last = cl[-1]
            ma = _rolling_ma(cl, self.mkt_ma_n)
            vmax = _rolling_max(cl, self.mkt_dd_n)
            vma = _rolling_ma(vl, 20)
            cond_ma = (ma is None) or (last >= ma)
            cond_dd = (vmax is None) or (last >= vmax * (1 - self.mkt_dd))
            cond_vol = (vma is None) or (vl[-1] >= vma * self.mkt_vol_ratio)
            self.mkt_ok = bool(cond_ma and cond_dd and cond_vol)
        # 板块
        j = self._idx(dstr, self._sec_dates)
        self.sec_ok = True
        if j is not None:
            cl = self._sec_close[: j + 1]
            last = cl[-1]
            ma = _rolling_ma(cl, self.sec_ma_n)
            mom1 = (last - cl[-self.sec_mom_n1]) if len(cl) > self.sec_mom_n1 else 0.0
            mom2 = (last - cl[-self.sec_mom_n2]) if len(cl) > self.sec_mom_n2 else 0.0
            cond_ma = (ma is None) or (last >= ma)
            cond_mo = (mom1 >= 0) and (mom2 >= 0)
            self.sec_ok = bool(cond_ma and cond_mo)

    # --- 指标 ---
    def _ema(self, arr, n=20):
        if len(arr) < n:
            return None
        k = 2.0 / (n + 1)
        ema = float(arr[-n])
        for v in arr[-n + 1 :]:
            ema = k * float(v) + (1 - k) * ema
        return ema

    def _vwap(self, am: ArrayManager, win=120):
        if am.count < 5:
            return None
        w = min(win, am.count)
        pv = float(np.sum(am.close[-w:] * am.volume[-w:]))
        vv = float(np.sum(am.volume[-w:]))
        if vv <= 0:
            return None
        return pv / vv


# ------------------ 策略 2：IceLeaderDTB ------------------
class IceLeaderDTB(CtaTemplate):
    author = "Huanan"

    # 市场参数
    limit_pct = 0.10
    price_tick = 0.01

    # 冰点CSV
    market_csv = "market_proxy.csv"
    sector_csv = "sector_proxy.csv"
    sentiment_csv = "sentiment_proxy.csv"

    # 阈值
    mkt_ma_n = 20
    mkt_dd_n = 60
    mkt_dd = 0.06
    mkt_vol_ratio = 0.8
    sec_ma_n = 10
    lim_up_max = 10
    lim_dn_min = 5
    adv_dec_max = 0.5

    # 入场
    near_dn_ticks = 2
    rebound_ticks = 5
    vol_ratio = 2.0
    vol_n = 20
    confirm_ref = "EMA5"
    base_lots = 3
    add_on_uplift = False

    # 地天判定 & T+1 卖出
    dtb_by_close = True
    near_up_ticks = 2
    lowopen_sell_mode = "queue_downlimit"  # "queue_downlimit" or "sell_open"
    t1_watch_end = "10:30:00"

    # 保护
    avoid_chasing_upper = True
    late_reduce_if_uprun = True

    parameters = [
        "limit_pct",
        "price_tick",
        "market_csv",
        "sector_csv",
        "sentiment_csv",
        "mkt_ma_n",
        "mkt_dd_n",
        "mkt_dd",
        "mkt_vol_ratio",
        "sec_ma_n",
        "lim_up_max",
        "lim_dn_min",
        "adv_dec_max",
        "near_dn_ticks",
        "rebound_ticks",
        "vol_ratio",
        "vol_n",
        "confirm_ref",
        "base_lots",
        "add_on_uplift",
        "dtb_by_close",
        "near_up_ticks",
        "lowopen_sell_mode",
        "t1_watch_end",
        "avoid_chasing_upper",
        "late_reduce_if_uprun",
    ]
    variables = [
        "pos",
        "inited",
        "entry_price",
        "entry_date",
        "hit_dn_today",
        "dtb_success_today",
        "yesterday_close",
        "t1_watch_close",
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager(240)

        self.entry_price = 0.0
        self.entry_date: object | None = None
        self.hit_dn_today = False
        self.dtb_success_today = False
        self.yesterday_close = 0.0
        self.t1_watch_close = None

        self._mkt = _load_daily_csv(self.market_csv)
        self._sec = _load_daily_csv(self.sector_csv)
        self._sen = _load_daily_csv(self.sentiment_csv)

        self._mkt_dates = [d["date"] for d in self._mkt]
        self._mkt_close = [d["close"] for d in self._mkt]
        self._mkt_vol = [d["volume"] for d in self._mkt]
        self._sec_dates = [d["date"] for d in self._sec]
        self._sec_close = [d["close"] for d in self._sec]
        self._sen_dates = [d["date"] for d in self._sen]
        self._sen_up = [d.get("lim_up", 0.0) for d in self._sen]
        self._sen_dn = [d.get("lim_dn", 0.0) for d in self._sen]
        self._sen_adv = [d.get("adv", 0.0) for d in self._sen]
        self._sen_dec = [d.get("dec", 0.0) for d in self._sen]

        self._t1_watch_end = _parse_time(self.t1_watch_end)

    def on_init(self):
        self.load_bar(300)

    def on_start(self):
        self.write_log("IceLeaderDTB started")

    def on_stop(self):
        self.write_log("stopped")

    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        dt = bar.datetime
        dstr = dt.strftime("%Y-%m-%d")
        t = dt.time()

        # 新日重置
        if getattr(self, "_last_date", None) != dstr:
            self.hit_dn_today = False
            self.dtb_success_today = False
            if self.am.count >= 2:
                self.yesterday_close = float(self.am.close[-2])
            self._last_date = dstr

        # T+1 卖出流程（若昨日地天成功）
        if (
            self.pos > 0
            and self.entry_date is not None
            and (dt.date() > self.entry_date)
        ):
            self._handle_t1_exit(bar)
            self.put_event()
            return

        # 冰点过滤不过直接返回
        if not self._is_ice_day(dstr):
            self.put_event()
            return

        # 空仓入场
        if self.pos == 0:
            prev_close = float(self.am.close[-2])
            up_lim, dn_lim = _calc_limit_prices(
                prev_close, self.limit_pct, self.price_tick
            )

            if bar.low_price <= dn_lim + self.near_dn_ticks * self.price_tick:
                self.hit_dn_today = True

            if self.hit_dn_today:
                vol_ma = (
                    _rolling_ma(
                        list(self.am.volume[-self.vol_n :]),
                        min(self.vol_n, self.am.count),
                    )
                    or bar.volume
                )
                vol_ok = bar.volume >= (vol_ma * self.vol_ratio)
                ref_ok = True
                if self.confirm_ref.upper() == "EMA5":
                    ema5 = self._ema(self.am.close, 5)
                    ref_ok = (ema5 is not None) and (bar.close_price >= ema5)
                elif self.confirm_ref.upper() == "VWAP":
                    vwap = self._vwap(self.am, 120)
                    ref_ok = (vwap is not None) and (bar.close_price >= vwap)
                price_ok = bar.close_price >= (
                    dn_lim + self.rebound_ticks * self.price_tick
                )

                if price_ok and vol_ok and ref_ok:
                    if (
                        self.avoid_chasing_upper
                        and (up_lim - bar.close_price)
                        <= self.near_up_ticks * self.price_tick
                    ):
                        self.put_event()
                        return
                    qty = max(100, self.base_lots * 100)
                    self.buy(bar.close_price, qty)
                    self.entry_price = bar.close_price
                    self.entry_date = dt.date()
                    self.dtb_success_today = self._check_dtb_success(up_lim, bar)
                    self.put_event()
                    return

        # 建仓日保护/可选操作
        if self.pos > 0 and dt.date() == self.entry_date:
            prev_close = float(self.am.close[-2])
            up_lim, _ = _calc_limit_prices(prev_close, self.limit_pct, self.price_tick)
            self.dtb_success_today = self.dtb_success_today or self._check_dtb_success(
                up_lim, bar
            )
            if self.late_reduce_if_uprun and ptime(14, 56) <= t <= ptime(14, 59):
                if (up_lim - bar.close_price) <= self.near_up_ticks * self.price_tick:
                    self.sell(bar.close_price, max(100, self.pos // 2))

        self.put_event()

    # ------- T+1 卖出 -------
    def _handle_t1_exit(self, bar: BarData):
        if self.pos <= 0:
            return
        prev_close = self.yesterday_close or float(self.am.close[-2])

        if self.dtb_success_today or self._was_dtb_yesterday():
            is_first_bar = self.t1_watch_close is None
            if is_first_bar:
                open_px = bar.open_price
                # 低开
                if open_px < prev_close:
                    if self.lowopen_sell_mode == "sell_open":
                        self.sell(bar.close_price, self.pos)
                    else:
                        dn_lim_next = round(prev_close * (1 - self.limit_pct), 2)
                        self.sell(dn_lim_next, self.pos)  # 注意：是否成交视盘口而定
                    self.t1_watch_close = prev_close
                    return
                else:
                    # 高开：进入观察，守“昨收线”
                    self.t1_watch_close = prev_close
                    return

            # 观察期：破昨收或超过观察截止时间即清仓
            if self.t1_watch_close is not None:
                if (bar.close_price < self.t1_watch_close) or (
                    bar.datetime.time() >= _parse_time(self.t1_watch_end)
                ):
                    self.sell(bar.close_price, self.pos)
                    return
        else:
            # 非地天成功的常规 T+1 简化：9:35~10:15 卖
            t = bar.datetime.time()
            if ptime(9, 35) <= t <= ptime(10, 15):
                self.sell(bar.close_price, self.pos)

    def _was_dtb_yesterday(self) -> bool:
        # 简化：运行期内由 self.dtb_success_today 记录；断点恢复请外部持久化标志
        return False

    # ------- 判定/指标 -------
    def _check_dtb_success(self, up_lim: float, bar: BarData) -> bool:
        if self.dtb_by_close:
            return (up_lim - bar.close_price) <= self.near_up_ticks * self.price_tick
        else:
            return (up_lim - bar.high_price) <= self.near_up_ticks * self.price_tick

    def _is_ice_day(self, dstr: str) -> bool:
        i = self._loc(dstr, self._get_mkt_dates())
        j = self._loc(dstr, self._get_sec_dates())
        k = self._loc(dstr, self._get_sen_dates())
        if i is None or j is None or k is None:
            return False
        # 大盘
        mcl = self._mkt_close[: i + 1]
        mvl = self._mkt_vol[: i + 1]
        m_last = mcl[-1]
        m_ma = _rolling_ma(mcl, self.mkt_ma_n)
        m_max = max(mcl[-self.mkt_dd_n :]) if len(mcl) >= self.mkt_dd_n else max(mcl)
        m_vma = _rolling_ma(mvl, 20)
        m_cond = (
            (m_ma is not None and m_last < m_ma)
            or (m_last < m_max * (1 - self.mkt_dd))
            or (m_vma is not None and mvl[-1] < m_vma * self.mkt_vol_ratio)
        )
        # 板块
        scl = self._sec_close[: j + 1]
        s_last = scl[-1]
        s_ma = _rolling_ma(scl, self.sec_ma_n)
        s_cond = s_ma is not None and s_last < s_ma
        # 情绪
        u = self._sen_up[k]
        d = self._sen_dn[k]
        a = self._sen_adv[k]
        c = self._sen_dec[k]
        adv_dec = (a / max(c, 1e-9)) if c > 0 else 0.0
        e_cond = (
            (u <= self.lim_up_max)
            and (d >= self.lim_dn_min)
            and (adv_dec <= self.adv_dec_max)
        )
        return bool(m_cond and s_cond and e_cond)

    def _get_mkt_dates(self):
        return [d["date"] for d in self._mkt]

    def _get_sec_dates(self):
        return [d["date"] for d in self._sec]

    def _get_sen_dates(self):
        return [d["date"] for d in self._sen]

    def _loc(self, dstr, dates):
        idx = None
        for i, ds in enumerate(dates):
            if ds <= dstr:
                idx = i
            else:
                break
        return idx

    def _ema(self, arr, n=5):
        if len(arr) < n:
            return None
        k = 2.0 / (n + 1)
        ema = float(arr[-n])
        for v in arr[-n + 1 :]:
            ema = k * float(v) + (1 - k) * ema
        return ema

    def _vwap(self, am: ArrayManager, win=120):
        if am.count < 5:
            return None
        w = min(win, am.count)
        pv = float(np.sum(am.close[-w:] * am.volume[-w:]))
        vv = float(np.sum(am.volume[-w:]))
        if vv <= 0:
            return None
        return pv / vv
