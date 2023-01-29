

class TradeNotYetClosedForPnlError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidTradeStateError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)