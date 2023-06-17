from __future__ import annotations
from .config import PnlCalcConfig
from .models import (
    ProxyTrade,
    Buy_Sell_Action_Enum,
    Proxy_Trade_Actions,
    LongShort_Enum,
    Inventory_Mode,
    MIN_NUMERIC_VALUE,
)
from .helper import ROI_Helper
from datetime import datetime, timedelta
from .utility import convert_datetime_to_ms
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TradeBookKeeperAgent:
    """The Book Keeper keeps all outstanding trades and archive historical trades
    It will contains two lists:
    - long trade position list
    - short trade position list

    Given a timestamp - t , price - p(t), trade signal - s(t), it works out
    - instant mtm(t) at timestamp t with p(t) with all outstanding trades
    - For each outstanding trade, run through ROI at t with p(t) to see if we close the trade
    - For each outstanding trade, run through stop/loss at t with p(t) to see of we close the trade
    - handle buy/sell position at t with p(t) and s(t)
    - adjust mtm(t) from the fee rate charged by the trades's action at t

    at any time t, we would work out Sharpe ratio with mtm(t)
    """

    def __init__(
        self, symbol: str, pnl_config: PnlCalcConfig, fixed_unit: bool = True
    ) -> None:
        self.outstanding_long_position_list: list[ProxyTrade] = []
        self.outstanding_short_position_list: list[ProxyTrade] = []

        self.archive_long_positions_list: list[ProxyTrade] = []
        self.archive_short_positions_list: list[ProxyTrade] = []

        self.symbol = symbol
        self.enable_short_position = pnl_config.enable_short_position
        self.fixed_unit = fixed_unit
        self.max_position_per_symbol = pnl_config.max_position_per_symbol

        self.stop_loss: float = pnl_config.stoploss

        self._mtm_history = {"timestamp_ms": [], "mtm": []}  # Integer in ms  # float

        self.roi_helper = ROI_Helper(pnl_config.roi)
        self.inventory_mode = Inventory_Mode.FIFO
        self.PROFIT_SLIPPAGE: float = 0.000001
        self.fee_rate_from_pnl_config: float = pnl_config.fee_rate
        pass

    @property
    def mtm_history_value(self) -> list[float]:
        return self._mtm_history["mtm"]

    @property
    def mtm_history_timestamp_ms(self) -> list[int]:
        return self._mtm_history["timestamp_ms"]

    @property
    def mtm_history_panda_df(self) -> pd.DataFrame:
        df: pd.DataFrame = pd.DataFrame(
            data={
                "timestamp_ms": self.mtm_history_timestamp_ms,
                "mtm": self.mtm_history_value,
            }
        )
        df["timestamp_ms"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
        return df

    def run_at_timestamp(
        self,
        dt: datetime,
        price: float,
        price_diff: float,
        buy_sell_action: Buy_Sell_Action_Enum,
    ) -> None:
        """Run the book keeper at a given timestamp

        Args:
            dt (datetime): time stamp
            price (float): price at the timestamp
            price_diff(float): price diff = price(t) - price(t-1
            buy_sell_action (Buy_Sell_Action_Enum): Buy/Sell/Hold
        """
        accumulated_fee: float = 0
        # 1. Calculate MTM
        mtm_at_time_t = 0
        for trade in (
            self.outstanding_long_position_list + self.outstanding_short_position_list
        ):
            if dt <= trade.entry_datetime or (
                trade.exit_datetime is not None and trade.exit_datetime < dt
            ):
                logger.debug(f"exclude {trade.entry_datetime} <= {dt}")
                continue
            normalized_mtm = trade.calculate_mtm_normalized(price_diff=price_diff)
            mtm_at_time_t += normalized_mtm
        self._mtm_history["timestamp_ms"].append(convert_datetime_to_ms(dt))

        # 2. Check if we need to close any position with ROI in each trade
        # a. Long position
        accumulated_fee += self._check_if_roi_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_long_position_list,
            archive_positions=self.archive_long_positions_list,
        )
        # b. Short position
        accumulated_fee += self._check_if_roi_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_short_position_list,
            archive_positions=self.archive_short_positions_list,
        )

        # 3. Check if we need to close any position with stop/loss in each trade
        # a. Long position
        accumulated_fee += self._check_if_stop_loss_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_long_position_list,
            archive_positions=self.archive_long_positions_list,
        )
        # b. Short position
        accumulated_fee += self._check_if_stop_loss_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_short_position_list,
            archive_positions=self.archive_short_positions_list,
        )

        # 4. Check if we need to open any position with s(t) and p(t) with buy signal
        if buy_sell_action == Buy_Sell_Action_Enum.BUY:
            accumulated_fee += self._check_if_open_buy_position(
                price=price,
                dt=dt,
                live_long_positions=self.outstanding_long_position_list,
                live_short_positions=self.outstanding_short_position_list,
                archive_short_positions=self.archive_short_positions_list,
            )
        elif buy_sell_action == Buy_Sell_Action_Enum.SELL:
            accumulated_fee += self._check_if_open_sell_position(
                price=price,
                dt=dt,
                live_short_positions=self.outstanding_short_position_list,
                live_long_positions=self.outstanding_long_position_list,
                archive_long_positions=self.archive_long_positions_list,
            )

        # 5. Adjust MTM with fee rate
        # Store the final mtm values
        self._mtm_history["mtm"].append(mtm_at_time_t - accumulated_fee)

        pass

    def _check_if_roi_close_position(
        self,
        price: float,
        dt: datetime,
        live_positions: list[ProxyTrade],
        archive_positions: list[ProxyTrade],
    ) -> float:
        """Check if we can close the position with ROI

        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_positions (list[ProxyTrade]): Live position list
            archive_positions (list[ProxyTrade]): archive position list

        Returns:
            fee_rate (float): adjusted fee
        """
        accum_fee: float = 0
        for trade in live_positions:
            cur_pnl: float = trade.calculate_pnl_normalized(price=price)
            if self.roi_helper.can_take_profit(
                entry_date=trade.entry_datetime, current_date=dt, normalized_pnl=cur_pnl
            ):
                # Close the trade
                self._close_trade_position_helper(
                    trade=trade,
                    price=price,
                    dt=dt,
                    archive_positions=archive_positions,
                    live_positions=live_positions,
                    close_reason=Proxy_Trade_Actions.ROI,
                )
                accum_fee += trade.fee_normalized
                logger.debug(f"Close trade with ROI:{trade}")

        return accum_fee

    def _check_if_stop_loss_close_position(
        self,
        price: float,
        dt: datetime,
        live_positions: list[ProxyTrade],
        archive_positions: list[ProxyTrade],
    ) -> float:
        """Check if we can close the position with stop/loss

        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_positions (list[ProxyTrade]): Live position list
            archive_positions (list[ProxyTrade]): archive position list

        Returns:
            fee_rate (float): adjusted fee
        """
        accum_fee: float = 0
        for trade in live_positions:
            cur_pnl: float = trade.calculate_pnl_normalized(price=price)

            if cur_pnl < -(abs(self.stop_loss)):
                # Close the trade
                logger.debug(
                    f"Close trade with stop loss:{trade}  at price {price} pnl:{cur_pnl} - {self.stop_loss}"
                )

                self._close_trade_position_helper(
                    trade=trade,
                    price=price,
                    dt=dt,
                    archive_positions=archive_positions,
                    live_positions=live_positions,
                    close_reason=Proxy_Trade_Actions.STOP_LOSS,
                )
                accum_fee += trade.fee_normalized

        return accum_fee

    def _check_if_open_buy_position(
        self,
        price: float,
        dt: datetime,
        live_long_positions: list[ProxyTrade],
        live_short_positions: list[ProxyTrade],
        archive_short_positions: list[ProxyTrade],
    ) -> float:
        """Check if we can open a long position
        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_long_positions (list[ProxyTrade]): Live long position list
            live_short_positions (list[ProxyTrade]): Live short position list
            archive_short_positions (list[ProxyTrade]): archive short position list
        Returns:
            fee_rate (float): adjusted fee
        """

        # 1. Check if we reach max position
        if len(live_long_positions) >= self.max_position_per_symbol:
            logger.debug(f"Reach max position {self.max_position_per_symbol}")
            return 0

        # 2. Credit line checking: Check if we have enough cash to open a position
        # ignored right now

        # 3. Check if we have any short position to close
        if (
            len(live_short_positions) > 0
            and (trade := self._get_trade_to_close(LongShort_Enum.SHORT)) is not None
        ):
            # Close the trade
            logger.debug(f"close {trade} with long signal")
            self._close_trade_position_helper(
                trade=trade,
                price=price,
                dt=dt,
                archive_positions=archive_short_positions,
                live_positions=live_short_positions,
                close_reason=Proxy_Trade_Actions.SIGNAL,
            )
            return trade.fee_normalized

        # 4. Open a new position
        trade = ProxyTrade(
            symbol=self.symbol,
            entry_datetime=dt,
            entry_price=price,
            inventory_mode=self.inventory_mode,
            direction=LongShort_Enum.LONG,
            unit=self.fixed_unit,
            fee_rate=self.fee_rate_from_pnl_config,
        )
        live_long_positions.append(trade)

        return trade.fee_normalized

    def _check_if_open_sell_position(
        self,
        price: float,
        dt: datetime,
        live_short_positions: list[ProxyTrade],
        live_long_positions: list[ProxyTrade],
        archive_long_positions: list[ProxyTrade],
    ) -> float:
        """Check if we can open a short position
        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_short_positions (list[ProxyTrade]): Live short position list
            live_long_positions (list[ProxyTrade]): Live long position list
            archive_long_positions (list[ProxyTrade]): archive long position list
        Returns:
            fee_rate (float): adjusted fee
        """

        # 1. Check if we reach max position
        if len(live_short_positions) >= self.max_position_per_symbol:
            logger.debug(f"Reach max position {self.max_position_per_symbol}")
            return 0

        # 2. Credit line checking: Check if we have enough cash to open a position
        # ignored right now

        # 3. Check if we have any long position to close
        if (
            len(live_long_positions) > 0
            and (trade := self._get_trade_to_close(LongShort_Enum.LONG)) is not None
        ):
            # Close the trade
            logger.debug(f"close {trade} with short signal")

            self._close_trade_position_helper(
                trade=trade,
                price=price,
                dt=dt,
                archive_positions=archive_long_positions,
                live_positions=live_long_positions,
                close_reason=Proxy_Trade_Actions.SIGNAL,
            )

            return trade.fee_normalized

        # 4. Open a new position
        if not self.enable_short_position:
            logger.info("Not enable short position here")
            return 0

        logger.debug(f"Open a new short position")
        trade = ProxyTrade(
            symbol=self.symbol,
            entry_datetime=dt,
            entry_price=price,
            inventory_mode=self.inventory_mode,
            direction=LongShort_Enum.SHORT,
            unit=self.fixed_unit,
            fee_rate=self.fee_rate_from_pnl_config,
        )
        live_short_positions.append(trade)

        return trade.fee_normalized

    def _get_trade_to_close(self, long_short: LongShort_Enum) -> ProxyTrade:
        """Get the trade to close
        Args:
            long_short (LongShort_Enum): long or short
        Returns:
            ProxyTrade: trade to close
        """
        if (
            long_short == LongShort_Enum.LONG
            and len(self.outstanding_long_position_list) > 0
        ):
            self.outstanding_long_position_list = sorted(
                self.outstanding_long_position_list
            )
            logger.debug(
                f"get trade to close outstanding_long_position_list:{self.outstanding_long_position_list}"
            )
            return self.outstanding_long_position_list.pop(0)
        elif (
            long_short == LongShort_Enum.SHORT
            and len(self.outstanding_short_position_list) > 0
        ):
            # heapq.heapify(self.outstanding_short_position_list)
            self.outstanding_short_position_list = sorted(
                self.outstanding_short_position_list
            )
            logger.debug(
                f"get trade to close outstanding_short_position_list:{self.outstanding_short_position_list}"
            )
            return self.outstanding_short_position_list.pop(0)
        else:
            return None

    def calculate_pnl_from_mtm_history(self) -> float:
        """calculate pnl recorded in the mtm history

        Returns:
            float: total pnl
        """

        mtm_array = np.array(self.mtm_history_value)
        return mtm_array.sum()

    def _calculate_sharpe_ratio(self) -> tuple[float]:
        """Calculate sharpe ratio
        Args:
            pnl_ts_data (pd.Dataframe): index: timestamp, column: pnl_ratio

        Returns:
            Tuple[float, pd.Dataframe ]: sharpe ratio, Dataframe: column, pnl daily
        """
        df: pd.DataFrame = pd.DataFrame(data=self._mtm_history)
        df.set_index("timestamp_ms", inplace=True, drop=True)

        # pnl_ts_data_daily: pd.DataFrame = df.resample("1H").sum()
        period_seconds: int = (df.index[-1] - df.index[0]) / 1000
        time_period_hours: int = period_seconds / 3600
        df["mtm_slippage"] = df["mtm"] - self.PROFIT_SLIPPAGE
        total_profit = df["mtm_slippage"]
        expected_yearly_return = total_profit.sum() / time_period_hours
        std_profit = np.std(total_profit)
        sharpe_ratio: float = (
            expected_yearly_return / std_profit * np.sqrt(365 * 24)
            if std_profit != 0
            else MIN_NUMERIC_VALUE  # float("-inf")
        )
        logger.debug(
            f"time_period_hours:{time_period_hours}, mtm: {total_profit.sum()}, expected_yearly_return: {expected_yearly_return}, std_profit: {std_profit}, sharpe_ratio: {sharpe_ratio}"
        )

        return sharpe_ratio

    def _close_trade_position_helper(
        self,
        trade: ProxyTrade,
        close_reason: Proxy_Trade_Actions,
        price: float,
        dt: datetime,
        live_positions: list[ProxyTrade],
        archive_positions: list[ProxyTrade],
    ):
        """Helper function to close a long position


        Args:
            trade (ProxyTrade): trade to close
            close_reason (Proxy_Trade_Actions): close reason
            price (float): close at price
            dt (datetime): close at time
            live_positions (list[ProxyTrade]): live position list
            archive_positions (list[ProxyTrade]): archive position list
        """
        trade.close_position(
            exit_price=price, exit_datetime=dt, close_reason=close_reason
        )
        logger.debug(f"Add {trade} to archive: {len(archive_positions)}")
        archive_positions.append(trade)

        live_positions.remove(trade)
        logger.debug(f"Removed {trade} from live positions {len(live_positions)}")
        pass
