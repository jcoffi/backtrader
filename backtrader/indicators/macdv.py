#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from . import Indicator, MovAv, AverageTrueRange

class MACDV(Indicator):
    '''
    MACD-V (Volatility Normalized MACD) uses ATR in its calculation to account for
    volatility, adapting the traditional MACD formula.

    Formula:
      - macdv = ((ema(data, me1_period) - ema(data, me2_period)) / atr(data, atr_period)) * 100
      - signal = ema(macdv, signal_period)

    The ATR period typically matches the period of the slow EMA.
    '''
    lines = ('macdv', 'signal',)
    params = (('period_me1', 9), ('period_me2', 26), ('period_signal', 9),
              ('period_atr', 26),  # ATR period typically matches the slow EMA period
              ('movav', MovAv.Exponential),)

    plotinfo = dict(plothlines=[0.0])
    plotlines = dict(signal=dict(ls='--'))

    def __init__(self):
        super(MACDV, self).__init__()
        me1 = self.p.movav(self.data, period=self.p.period_me1)
        me2 = self.p.movav(self.data, period=self.p.period_me2)
        atr = AverageTrueRange(self.data, period=self.p.period_atr)
        # Calculate MACD-V using ATR for volatility normalization
        self.lines.macdv = ((me1 - me2) / atr) * 100
        self.lines.signal = self.p.movav(self.lines.macdv,
                                         period=self.p.period_signal)

class MACDVHisto(MACDV):
    '''
    Subclass of MACD-V which adds a "histogram" of the difference between the
    macdv and signal lines, representing the MACD-VH (Volatility Normalized Histogram).

    Formula:
      - histo = macdv - signal
    '''
    alias = ('MACDVHistogram',)

    lines = ('histo',)
    plotlines = dict(histo=dict(_method='bar', alpha=0.50, width=1.0))

    def __init__(self):
        super(MACDVHisto, self).__init__()
        self.lines.histo = self.lines.macdv - self.lines.signal
