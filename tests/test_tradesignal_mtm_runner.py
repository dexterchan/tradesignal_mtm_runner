from tradesignal_mtm_runner.runner_mtm import Trade_Mtm_Runner
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.interfaces import ITradeSignalRunner
from tradesignal_mtm_runner.models import Mtm_Result

import pytest
import pandas as pd
import numpy as np
from functools import reduce

test_exchange = "kraken"
test_symbol = "ETHUSD"
test_cases: list = [
    "ascending",
    "descending",
    "take_profit",
    "stop_loss",
    "init",
    "pnl_config_test",
    "ascending_buy_3_signals_sell_1_signal",
]
DATA_DIM = 200
DATA_MOVEMENT = 100
COMPARE_ERROR = 0.1

import logging
logger = logging.getLogger(__name__)


@pytest.fixture
def get_pnl_calculator():
    def __get_pnl_calculator(exchange: str,
        is_hyperopt: bool = False,
        enable_short_position: bool = False,
        pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()) -> ITradeSignalRunner:

        calculator: ITradeSignalRunner = Trade_Mtm_Runner(
            pnl_config=pnl_config
        )

        return calculator
    return __get_pnl_calculator


@pytest.mark.skipif("ascending" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_ascending_data(get_test_ascending_mkt_data,get_pnl_calculator) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM, step=DATA_MOVEMENT)
    # Buy at row 2 and sell at row 80
    buy_signal = test_mktdata.copy()
    buy_signal["buy"] = np.where(test_mktdata["inx"] == 2, 1, np.nan)
    sell_signal = test_mktdata.copy()
    sell_signal["sell"] = np.where(test_mktdata["inx"] == 80, 1, np.nan)
    pnl = (
        test_mktdata.iloc[80]["close"] - test_mktdata.iloc[2]["close"]
    ) / test_mktdata.iloc[2]["close"]

    pnl_calculator: Trade_Mtm_Runner = get_pnl_calculator(
        exchange=test_exchange,
        is_hyperopt=False,
        enable_short_position=False,
    )

    _price_movement = pnl_calculator._prepare_df_for_analysis(
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )
    
    for i, p in enumerate(_price_movement["price_movement"][1:]):
        assert p == DATA_MOVEMENT

    print(buy_signal)
    mtm_result:Mtm_Result = pnl_calculator.calculate(
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
        symbol=test_symbol,
    )

    assert abs(mtm_result.pnl - pnl) < COMPARE_ERROR
    assert mtm_result.pnl != 0
    mtm_reward_history = mtm_result.pnl_timeline["mtm_ratio"]
    assert len(mtm_reward_history) > 0
    mtm_reward_sum = reduce(lambda x, y: x + y, mtm_reward_history)
    assert abs(mtm_reward_sum - mtm_result.pnl) < COMPARE_ERROR

    


