
class UnSupportedException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class NoShortPositionAllowedException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class TradeNotYetClosedForPnlError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidTradeStateError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class MaxPositionPerSymbolExceededException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)