from typing import Protocol
from .models import Mtm_Result
import pandas as pd

class ITradeSignalRunner(Protocol):
    """Pnl calculator"""

    def calculate(
        self,
        symbol: str,
        buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame,
    ) -> Mtm_Result:
        """
            calculate Pnl given by the buy and sell signal dataframe

        Args:
            symbol (str): [symbol of the asset]
            buy_signal_dataframe (pd.DataFrame): [Buy signal dataframe]
            sell_signal_dataframe (pd.DataFrame): [Sell signal dataframe]

        Returns:
            Mtm_Result: [MTM result]
        """
        pass