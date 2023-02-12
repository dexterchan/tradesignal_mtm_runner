from __future__ import annotations
from .interfaces import ITradeSignalRunner
from .config import PnlCalcConfig
from .helper import ROI_Helper

from .trade_reward import TradeBookKeeperAgent
from .models import Mtm_Result, Buy_Sell_Action_Enum

import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Trade_Mtm_Runner(ITradeSignalRunner):
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
        self.trade_order_simulator_map: dict[str, TradeBookKeeperAgent] = {}
        pass

    
    def calculate(
        self,
        symbol: str,
        buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame,
    ) -> Mtm_Result:
        """[summary]

        Args:
            symbol (str): [description]
            buy_signal_dataframe (pd.DataFrame): [description]
            sell_signal_dataframe (pd.DataFrame): [description]

        Returns:
            Mtm_Result: [description]
        """
        _signal_dataframe: pd.DataFrame = self._prepare_df_for_analysis(
            buy_signal_dataframe=buy_signal_dataframe,
            sell_signal_dataframe=sell_signal_dataframe
        )
        
        return self._iterate_each_timeframe(
            symbol=symbol, signal_dataframe=_signal_dataframe
        )

    def _prepare_df_for_analysis(self,buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame, ) -> pd.DataFrame:
        """
        Prepare the dataframe for analysis
    

        Args:
            buy_signal_dataframe (pd.DataFrame): buy data frame "close price", "buy" column
            sell_signal_dataframe (pd.DataFrame): sell data frame  "close price" "sell column

        Returns:
            pd.DataFrame: _description_
        """
        _signal_dataframe: pd.DataFrame = buy_signal_dataframe
        _signal_dataframe["sell"] = sell_signal_dataframe["sell"]
        _signal_dataframe["price_movement"] = _signal_dataframe["close"].diff(1)

        return _signal_dataframe

    def _iterate_each_timeframe(self, symbol:str, signal_dataframe:pd.DataFrame) -> Mtm_Result:
        """_summary_

        Args:
            symbol (str): _description_
            signal_dataframe (pd.DataFrame): _description_

        Returns:
            Mtm_Result: _description_
        """
        close_price = signal_dataframe["close"].to_numpy(dtype=float)
        buy_signal = signal_dataframe["buy"].to_numpy(dtype=int)
        sell_signal = signal_dataframe["sell"].to_numpy(dtype=int)
        time_line = signal_dataframe.index.to_numpy(dtype="datetime64")
        price_move = signal_dataframe["price_movement"].to_numpy(dtype=float)

        pnl_ts_data: dict[str, list] = {
            "timestamp": time_line.tolist(),
            "pnl_ratio": [0] * len(signal_dataframe),
            "buy_signal": buy_signal.tolist(),
            "sell_signal": sell_signal.tolist(),
            "close_price": close_price.tolist(),
        }

        
        max_pnl: float = 0
        max_drawdown: float = 0

        _trade_order_agent:TradeBookKeeperAgent = TradeBookKeeperAgent(
            symbol=symbol, pnl_config=self.pnl_config, fixed_unit=True
        )
        
        self.trade_order_simulator_map[symbol] = _trade_order_agent

        for i in range(len(signal_dataframe)):

            buy_sell_signal:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.NEUTRAL

            if buy_signal[i] == 1:
                buy_sell_signal = Buy_Sell_Action_Enum.BUY
            elif sell_signal[i] == 1:
                buy_sell_signal = Buy_Sell_Action_Enum.SELL

            _trade_order_agent.run_at_timestamp(
                dt=time_line[i],
                price=close_price[i],
                price_diff=price_move[i],
                buy_sell_action=buy_sell_signal,
            )

            pnl_cum_at_this_moment:float = _trade_order_agent.calculate_pnl_from_mtm_history()
            max_pnl = max(max_pnl, pnl_cum_at_this_moment)
            max_drawdown = max(max_drawdown, max_pnl - pnl_cum_at_this_moment)
            pnl_ts_data["pnl_ratio"][i] = pnl_cum_at_this_moment

        # Summarize the pnl result
        pnl_ts_data["mtm_ratio"] = _trade_order_agent.mtm_history
        _trade_order_agent.mtm_history
        _df = pd.DataFrame.from_dict(data=pnl_ts_data)
        _df.set_index("timestamp", drop=True, inplace=True)
        sharpe_ratio, _df_daily = self._calculate_sharpe_ratio(df=_df)
        _df["timestamp"] = (pd.to_numeric(_df.index) / 1000000).astype("int64")
        
        return None

        pass

    