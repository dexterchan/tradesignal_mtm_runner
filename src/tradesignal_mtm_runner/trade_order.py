from .exceptions import UnSupportedException
from datetime import datetime

class TradeOrderSimulator:

    def __init__(self, symbol:str, enable_short_position:bool, max_position_per_symbol:int, fixed_principal:bool=True) -> None:
        self.symbol = symbol
        self.enable_short_position = enable_short_position
        self.max_position_per_symbol = max_position_per_symbol
        self.fixed_principal = fixed_principal

        if not self.fixed_principal:
            raise UnSupportedException("Only fixed principal is supported")
        pass

    def handle_buy_signal(self, price:float, unit:float, entry_datetime:datetime) -> None:
        pass