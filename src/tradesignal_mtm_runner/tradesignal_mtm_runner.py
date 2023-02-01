"""Main module."""
from __future__ import annotations
from .interfaces import ITradeSignalRunner
import pandas as pd
from models import ( 
    ProxyTrade, 
    PnlCalcConfig, 
    LongShort_Enum, 
    Proxy_Trade_Actions,
    MIN_NUMERIC_VALUE
)
from .trade_order import TradeOrderSimulator
from .exceptions import MaxPositionPerSymbolExceededException, NoShortPositionAllowedException
from helper import ROI_Helper

import logging
from datetime import datetime
import numpy as np
logger = logging.getLogger(__name__)

# Copy from Trade_Pnl_Runner_Fully_Filled
class Mtm_Runner(ITradeSignalRunner):
    """Accept buy/sell signal from Strategy
    buy/sell signal should be coupled with market data from panda dataframe
    stop loss/profit checker also initialized into the runner.
    Note: it will merage buy + sell signal into one dataframe when processing

    to reduce complexity, we assume trade is fully filled each time

    mtm runner will generate pnl time series
    for each time record, up to t,  do the following:
    1) calculate the mtm based on the position 
    2) apply buy/sell signals -> update the trade position
    3) check if stop loss/profit required -> if yes, close the trade and update trade position
    Finally, we can conclude the Pnl by adding up all the mtm

    reference: MTM calculation - https://ibkr.info/node/56
    price diff[t] = price(t) - price(t-1)
    For each position[p] in each candlestick[t]:
        mtm[p][t] = price diff[t] / (entry price[p]) * 100 (normalized mtm value)
        #cum_mtm[p][t] is the cumulation of mtm number up to t
        cum_mtm[p][t] += mtm[p][t]
    mtm[t] = [mtm[p] for all p]
    cum_mtm[t] = [ cum_mtm[p][t] for all p]
    max_pnl = max(max_pnl, cum_mtm[t])
    max_drawdown = max(max_drawdown, max_pnl - cum_mtm[t])
    
    
    calculate the SHARPE ratio based on the mtm time series
    """

    def __init__(
        self,
        pnl_config: PnlCalcConfig,
    ) -> None:
        """
        Args:
            enable_short_position (bool): enable short position
            fixed_unit_amount (float): stake amount
            no_duplicate_trade (bool, optional): no duplication for the same symbol. Defaults to True.
        """

        self._take_profit: float = pnl_config.roi[0]  # (take_profit_pct/100.0)
        self._roi: dict[int, float] = pnl_config.roi
        self._stop_loss: float = pnl_config.stoploss  # (- stop_loss_pct/100.0)
        self.enable_short_position = pnl_config.enable_short_position
        self.fix_unit_amount = pnl_config.fixed_stake_unit_amount
        self.pnl_config = pnl_config
        self.PROFIT_SLIPPAGE: float = 0.00005

        self._roi_helper = ROI_Helper(roi_dict=self._roi)
        logger.debug(
            f"Take profit at {self._take_profit} ; Stop Loss at {self._stop_loss}"
        )
        # Potential to support multiple symbols in the pnl run.
        self.trade_order_keeper_map: dict[str, TradeOrderSimulator] = {}
        pass

    def _check_if_close_position(
        self, trade: ProxyTrade, pnl: float, price_date: datetime
    ) -> tuple[bool, Proxy_Trade_Actions]:
        """helper function to determine if we should close the position

        Args:
            trade (ProxyTrade): trade to close position
            pnl (float): pnl at the time
            price_date (datetime): datetime of the price

        Returns:
            Tuple[bool, Proxy_Trade_Actions]: close position (True -> close; False -> keep), Reason to close the position
        """

        if pnl < self._stop_loss:
            return True, Proxy_Trade_Actions.STOP_LOSS

        # is_close_position: bool = pnl > self._take_profit
        is_close_position: bool = self._roi_helper.can_take_profit(
            entry_date=trade.entry_datetime, current_date=price_date, normalized_pnl=pnl
        )
        action_source: Proxy_Trade_Actions = (
            Proxy_Trade_Actions.TAKE_PROFIT if is_close_position else None
        )

        return (is_close_position, action_source)

    def _check_take_profit_stop_loss(
        self,
        direction: LongShort_Enum,
        trade_order_keeper: TradeOrderSimulator,
        price: float,
        ts: datetime,
    ) -> float:
        """Helper function to check take profit and stop loss at long position

        Args:
            direction (LongShort_Enum): trade direction
            trade_order_keeper (TradeOrderKeeper): [description]
            price (float): [description]
            ts(datetime): datetime of the price
        Retuns:
            pnl(float) : normalized pnl
        """

        trade: ProxyTrade = (
            trade_order_keeper.get_highest_price_buy_position()
            if direction == LongShort_Enum.LONG
            else trade_order_keeper.get_lowest_price_sell_position()
        )
        if trade is None:
            return 0
        pnl = trade.calculate_pnl_normalized(price=price)
        
        is_close_position, action_source = self._check_if_close_position(
            trade=trade, pnl=pnl, price_date=ts
        )
        if is_close_position:
            old_trade: ProxyTrade = None

            new_trade, old_trade = (
                trade_order_keeper.handle_sell_signal(
                    close_price=price,
                    ts=ts,
                    unit=trade.unit,
                    action_source=action_source,
                )
                if direction == LongShort_Enum.LONG
                else trade_order_keeper.handle_buy_signal(
                    close_price=price,
                    ts=ts,
                    unit=trade.unit,
                    action_source=action_source,
                )
            )
            logger.debug(
                f"Long trade to close position: entry_price:{old_trade.entry_price} close_price:{old_trade.exit_price}"
            )
            if old_trade is None:
                raise Exception(f"Trade {trade} failed to close")
            assert old_trade == trade, "we should refer to the same trade"
            return old_trade.pnl_normalized
        else:
            return 0

    def _handle_buy_signal(
        self,
        trade_order_keeper: TradeOrderSimulator,
        price: float,
        timestamp: datetime,
        unit_amount: float,
        local_pnl: float,
    ) -> float:
        """handle a buy signal"""
        # buy signal is here
        try:
            new_long_trade, old_short_trade = trade_order_keeper.handle_buy_signal(
                close_price=price,
                ts=timestamp,
                unit=unit_amount,
                action_source=Proxy_Trade_Actions.SIGNAL,
            )
            # logger.debug(
            #     f":{timestamp}:new trade entry datetime{new_long_trade.entry_datetime} - price {new_long_trade.entry_price}"
            # )
            if old_short_trade is not None:
                # logger.debug("old trade entry datetime{old_short_trade.entry_datetime}")
                # logger.debug(
                #     f"{timestamp} Pnl generated by buy signal {old_short_trade.pnl_normalized}, entry_price:{old_short_trade.entry_price}, exit_price:{old_short_trade.exit_price}"
                # )
                local_pnl += old_short_trade.pnl_normalized
            assert len(trade_order_keeper.outstanding_long_position_list) > 0
        except MaxPositionPerSymbolExceededException as me:
            logger.warning(f"Max Position exceeded at time {timestamp} price {price}")
            pass

        return local_pnl

    def _handle_sell_signal(
        self,
        trade_order_keeper: TradeOrderSimulator,
        price: float,
        timestamp: datetime,
        unit_amount: float,
        local_pnl: float,
    ) -> float:
        # sell signal is here
        # logger.debug(f"{inx}:{timestamp} Get sell signal")
        try:
            new_short_trade, old_long_trade = trade_order_keeper.handle_sell_signal(
                close_price=price,
                ts=timestamp,
                unit=unit_amount,
                action_source=Proxy_Trade_Actions.SIGNAL,
            )
            # logger.debug(
            #     f"{timestamp}:new trade entry datetime{new_short_trade.entry_datetime} - price {new_short_trade.entry_price}"
            # )
            if old_long_trade is not None:
                # logger.debug(
                #     f"{timestamp} pnl generated by sell signal {old_long_trade.pnl_normalized}, entry_price:{old_long_trade.entry_price}, exit_price:{old_long_trade.exit_price}"
                # )
                local_pnl += old_long_trade.pnl_normalized
        except NoShortPositionAllowedException as se:
            logger.warning(f"No short sell enabled at time {timestamp} price {price}")
            pass
        except MaxPositionPerSymbolExceededException as me:
            logger.warning(f"Max Position exceeded at time {timestamp} price {price}")
            pass
        return local_pnl

    def _calculate_sharpe_ratio(self, df: pd.DataFrame) -> tuple[float, pd.DataFrame]:
        """Calculate sharpe ratio
        Args:
            pnl_ts_data (pd.Dataframe): index: timestamp, column: pnl_ratio

        Returns:
            Tuple[float, pd.Dataframe ]: sharpe ratio, Dataframe: column, pnl daily
        """

        df["pnl_ratio_s"] = df["pnl_ratio"] - self.PROFIT_SLIPPAGE
        pnl_ts_data_daily: pd.DataFrame = df.resample("1D").sum()
        period = pnl_ts_data_daily.index[-1] - pnl_ts_data_daily.index[0]
        days_period: int = period.days

        total_profit = pnl_ts_data_daily["pnl_ratio_s"]
        expected_yearly_return = total_profit.sum() / days_period
        std_profit = np.std(total_profit)
        sharpe_ratio: float = (
            expected_yearly_return / std_profit * np.sqrt(365)
            if std_profit != 0
            else MIN_NUMERIC_VALUE  # float("-inf")
        )

        return sharpe_ratio, pnl_ts_data_daily

    def _iterate_each_timeframe(
        self,
        symbol: str,
        signal_dataframe: pd.DataFrame,
    ) -> PnlCalcConfig:
        """iterate each time frame to calculate pnl and drawdown
            for each time record, up to t,  do
            1) check if stop loss/profit required -> if yes, close the trade and generate pnl
            2) apply buy signal -> check if pnl generated
            3) apply sell signal -> check if pnl generated

            pnl_ratio = pnl diff / (entry price) * 100
            pnl_cum is the cumulation of pnl number up to t
            pnl_cum += pnl_ratio
            max_pnl = max(max_pnl, pnl_cum)
            max_drawdown = max(max_drawdown, max_pnl - pnl_cum)
        Args:
            symbol (str): symbol of asset
            signal_dataframe (pd.DataFrame): [index must be datetime, must include column: close, buy , sell ]

        Returns:
            PnlResult: [description]
        """
        close_price = signal_dataframe["close"].to_numpy(dtype=float)
        buy_signal = signal_dataframe["buy"].to_numpy(dtype=int)
        sell_signal = signal_dataframe["sell"].to_numpy(dtype=int)
        time_line = signal_dataframe.index.to_numpy(dtype="datetime64")
        pnl_ts_data: dict[str, list] = {
            "timestamp": signal_dataframe.index,
            "pnl_ratio": [0] * len(signal_dataframe),
            "buy_signal": buy_signal.tolist(),
            "sell_signal": sell_signal.tolist(),
            "close_price": close_price.tolist(),
        }

        pnl_cum: float = 0
        max_pnl: float = 0
        max_drawdown: float = 0
        _trade_order_keeper = TradeOrderSimulator(
            symbol=symbol, pnl_config=self.pnl_config, fixed_unit=True
        )
        self.trade_order_keeper_map[symbol] = _trade_order_keeper
        unit_amount = self.fix_unit_amount

        def _calculate_stop_loss(_price: float, _timestamp: datetime) -> float:
            local_pnl_ratio: float = 0
            local_pnl_ratio += self._check_take_profit_stop_loss(
                direction=LongShort_Enum.LONG,
                trade_order_keeper=_trade_order_keeper,
                price=_price,
                ts=_timestamp,
            )
            # Check take profit stop loss of Short position
            if self.enable_short_position:
                local_pnl_ratio += self._check_take_profit_stop_loss(
                    direction=LongShort_Enum.SHORT,
                    trade_order_keeper=_trade_order_keeper,
                    price=_price,
                    ts=_timestamp,
                )
            return local_pnl_ratio

        for inx in range(len(time_line)):
            price = close_price[inx]
            timestamp: datetime = pd.Timestamp(time_line[inx]).to_pydatetime()
            # Check take profit stop loss of Long position
            _local_pnl_ratio = _calculate_stop_loss(_price=price, _timestamp=timestamp)

            # Process the buy signal
            if buy_signal[inx] == 1:
                _local_pnl_ratio = self._handle_buy_signal(
                    trade_order_keeper=_trade_order_keeper,
                    price=price,
                    timestamp=timestamp,
                    unit_amount=unit_amount,
                    local_pnl=_local_pnl_ratio,
                )
            # Process the sell signal
            if sell_signal[inx] == 1:
                _local_pnl_ratio = self._handle_sell_signal(
                    trade_order_keeper=_trade_order_keeper,
                    price=price,
                    timestamp=timestamp,
                    unit_amount=unit_amount,
                    local_pnl=_local_pnl_ratio,
                )
            # Calculate the pnl_cum, max_pnl
            pnl_ts_data["pnl_ratio"][inx] = _local_pnl_ratio
            pnl_cum += _local_pnl_ratio
            max_pnl = max(max_pnl, pnl_cum)
            max_drawdown = max(max_drawdown, max_pnl - pnl_cum)

        # Summarize the pnl result
        _df = pd.DataFrame.from_dict(data=pnl_ts_data)
        _df.set_index("timestamp", drop=True, inplace=True)
        sharpe_ratio, _df_daily = self._calculate_sharpe_ratio(df=_df)
        _df["timestamp"] = (pd.to_numeric(_df.index) / 1000000).astype("int64")
        _df_daily["timestamp"] = (pd.to_numeric(_df_daily.index) / 1000000).astype(
            "int64"
        )
        data_in_dict: dict = _df.to_dict(orient="list")

        pnlresult: PnlCalcConfig = PnlCalcConfig(
            pnl=pnl_cum,
            max_drawdown=max_drawdown,
            pnl_timeline=data_in_dict,
            sharpe_ratio=sharpe_ratio,
            pnl_daily=_df_daily.to_dict(orient="list"),
        )
        pnlresult.long_trades_archive.extend(_trade_order_keeper.long_trades_archives)

        pnlresult.long_trades_outstanding.extend(
            _trade_order_keeper.long_trades_outstanding
        )

        pnlresult.short_trades_archive.extend(_trade_order_keeper.short_trades_archives)
        pnlresult.short_trades_oustanding.extend(
            _trade_order_keeper.short_trades_outstanding
        )
        return pnlresult

    def calculate(
        self,
        symbol: str,
        buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame,
    ) -> PnlCalcConfig:
        """[summary]

        Args:
            symbol (str): [description]
            buy_signal_dataframe (pd.DataFrame): [description]
            sell_signal_dataframe (pd.DataFrame): [description]

        Returns:
            PnlResult: [description]
        """
        _signal_dataframe: pd.DataFrame = buy_signal_dataframe
        _signal_dataframe["sell"] = sell_signal_dataframe["sell"]

        return self._iterate_each_timeframe(
            symbol=symbol, signal_dataframe=_signal_dataframe
        )

    pass
