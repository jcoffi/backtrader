from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .indicator import Indicator


class OnBalanceVolume(Indicator):
    """
    On-Balance Volume (OBV) Indicator

    Formula:
      OBV[0] = 0 (on the very first bar)
      If Close[0] > Close[-1] => OBV = OBV[-1] + Volume[0]
      If Close[0] < Close[-1] => OBV = OBV[-1] - Volume[0]
      If Close[0] = Close[-1] => OBV = OBV[-1]

    This indicator can be used on daily, weekly, monthly or any other timeframe
    supported by Backtrader. The "close" price is whatever the data feed (or
    resampler) provides as the close of that period (e.g., last trading day of
    the week for weekly data, last trading day of the month for monthly, etc.).
    """
    lines = ('obv',)

    def __init__(self):
        # We want at least 1 previous bar to compare closes
        self.addminperiod(1)

    def next(self):
        # Initialize OBV to 0 on the very first bar
        if len(self) == 1:
            self.lines.obv[0] = 0
        else:
            prev_obv = self.lines.obv[-1]
            if self.data.close[0] > self.data.close[-1]:
                self.lines.obv[0] = prev_obv + self.data.volume[0]
            elif self.data.close[0] < self.data.close[-1]:
                self.lines.obv[0] = prev_obv - self.data.volume[0]
            else:
                # close == close[-1]
                self.lines.obv[0] = prev_obv
