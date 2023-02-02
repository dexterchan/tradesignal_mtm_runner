import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def get_test_ascending_mkt_data() -> pd.DataFrame:
    def _get_data(dim: int = 10):
        n = datetime.now()
        inx = [i for i in range(dim)]
        time_stamp = [n + timedelta(minutes=i) for i in range(dim)]
        data = [time_stamp, inx]
        n_data = np.asarray(data)
        df = pd.DataFrame(data=n_data.transpose(), columns=["timestamp", "inx"])
        df.set_index("timestamp", inplace=True, drop=True)
        df["close"] = df["inx"] * 100.00 + 1000
        return df
        pass

    return _get_data


@pytest.fixture
def get_test_descending_mkt_data() -> pd.DataFrame:
    def _get_data(dim: int = 10):
        n = datetime.now()
        inx = [i for i in range(dim)]
        timestamp = [n + timedelta(minutes=i) for i in range(dim)]
        data = [timestamp, inx]
        n_data = np.asarray(data)
        df = pd.DataFrame(data=n_data.transpose(), columns=["timestamp", "inx"])
        df.set_index("timestamp", inplace=True, drop=True)
        max_inx = df["inx"].max()
        df["close"] = (max_inx - df["inx"]) * 100.00 + 1000

        
        return df

    return _get_data

from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.interfaces import ITradeSignalRunner
from tradesignal_mtm_runner.runner import Trade_Mtm_Runner
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


