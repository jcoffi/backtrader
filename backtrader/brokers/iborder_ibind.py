#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Simple IBOrder and IBOrderState classes for ibind migration
# These replace the ibpy dependencies with pure Python implementations
#
###############################################################################

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class IBOrderState(object):
    """
    Wraps order state information and provides string representation
    
    This replaces the ibpy OrderState object with a pure Python implementation
    """
    _fields = ['status', 'initMargin', 'maintMargin', 'equityWithLoan',
               'commission', 'minCommission', 'maxCommission',
               'commissionCurrency', 'warningText']

    def __init__(self, **kwargs):
        # Initialize all fields to None
        for field in self._fields:
            setattr(self, field, None)
        
        # Set provided values
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __str__(self):
        lines = ['--- ORDERSTATE BEGIN']
        for field in self._fields:
            value = getattr(self, field, None)
            field_name = field.capitalize()
            lines.append(f'{field_name}: {value}')
        lines.append('--- ORDERSTATE END')
        return '\n'.join(lines)


class IBOrder(object):
    """
    Interactive Brokers Order class that replaces ib.ext.Order.Order
    
    This class provides a pure Python implementation of IB order functionality
    that works with ibind APIs.
    """
    
    # Order type constants (matching backtrader's Order class)
    Buy = 1
    Sell = 2

    def __init__(self, action=None, **kwargs):
        """
        Initialize the order with IB-specific parameters
        
        Args:
            action: Order action ('BUY' or 'SELL')
            **kwargs: Additional order parameters
        """
        # Set basic order attributes
        self.ordtype = self.Buy if action == 'BUY' else self.Sell
        self.size = kwargs.get('m_totalQuantity', 100)
        
        # IB-specific order fields (replacing ib.ext.Order.Order fields)
        self.m_orderId = kwargs.get('m_orderId', kwargs.get('orderId', 0))
        self.m_clientId = kwargs.get('m_clientId', kwargs.get('clientId', 0))
        self.m_permId = kwargs.get('m_permId', kwargs.get('permId', 0))
        
        # Order details
        self.m_action = action or kwargs.get('m_action', 'BUY')
        self.m_totalQuantity = kwargs.get('m_totalQuantity', 0)
        self.m_orderType = kwargs.get('m_orderType', 'MKT')
        self.m_lmtPrice = kwargs.get('m_lmtPrice', 0.0)
        self.m_auxPrice = kwargs.get('m_auxPrice', 0.0)
        self.m_tif = kwargs.get('m_tif', 'DAY')
        self.m_ocaGroup = kwargs.get('m_ocaGroup', '')
        self.m_account = kwargs.get('m_account', '')
        self.m_openClose = kwargs.get('m_openClose', 'O')
        self.m_origin = kwargs.get('m_origin', 0)
        self.m_orderRef = kwargs.get('m_orderRef', '')
        self.m_transmit = kwargs.get('m_transmit', True)
        self.m_parentId = kwargs.get('m_parentId', 0)
        self.m_blockOrder = kwargs.get('m_blockOrder', False)
        self.m_sweepToFill = kwargs.get('m_sweepToFill', False)
        self.m_displaySize = kwargs.get('m_displaySize', 0)
        self.m_triggerMethod = kwargs.get('m_triggerMethod', 0)
        self.m_outsideRth = kwargs.get('m_outsideRth', False)
        self.m_hidden = kwargs.get('m_hidden', False)
        self.m_goodAfterTime = kwargs.get('m_goodAfterTime', '')
        self.m_goodTillDate = kwargs.get('m_goodTillDate', '')
        self.m_overridePercentageConstraints = kwargs.get('m_overridePercentageConstraints', False)
        self.m_rule80A = kwargs.get('m_rule80A', '')
        self.m_allOrNone = kwargs.get('m_allOrNone', False)
        self.m_minQty = kwargs.get('m_minQty', 0)
        self.m_percentOffset = kwargs.get('m_percentOffset', 0.0)
        self.m_trailStopPrice = kwargs.get('m_trailStopPrice', 0.0)
        self.m_trailingPercent = kwargs.get('m_trailingPercent', 0.0)
        
        # Additional fields for compatibility
        self.m_faGroup = kwargs.get('m_faGroup', '')
        self.m_faProfile = kwargs.get('m_faProfile', '')
        self.m_faMethod = kwargs.get('m_faMethod', '')
        self.m_faPercentage = kwargs.get('m_faPercentage', '')
        self.m_designatedLocation = kwargs.get('m_designatedLocation', '')
        self.m_exemptCode = kwargs.get('m_exemptCode', -1)
        self.m_discretionaryAmt = kwargs.get('m_discretionaryAmt', 0.0)
        self.m_eTradeOnly = kwargs.get('m_eTradeOnly', True)
        self.m_firmQuoteOnly = kwargs.get('m_firmQuoteOnly', True)
        self.m_nbboPriceCap = kwargs.get('m_nbboPriceCap', 0.0)
        self.m_optOutSmartRouting = kwargs.get('m_optOutSmartRouting', False)
        self.m_auctionStrategy = kwargs.get('m_auctionStrategy', 0)
        self.m_startingPrice = kwargs.get('m_startingPrice', 0.0)
        self.m_stockRefPrice = kwargs.get('m_stockRefPrice', 0.0)
        self.m_delta = kwargs.get('m_delta', 0.0)
        self.m_stockRangeLower = kwargs.get('m_stockRangeLower', 0.0)
        self.m_stockRangeUpper = kwargs.get('m_stockRangeUpper', 0.0)
        self.m_volatility = kwargs.get('m_volatility', 0.0)
        self.m_volatilityType = kwargs.get('m_volatilityType', 0)
        self.m_deltaNeutralOrderType = kwargs.get('m_deltaNeutralOrderType', '')
        self.m_deltaNeutralAuxPrice = kwargs.get('m_deltaNeutralAuxPrice', 0.0)
        self.m_deltaNeutralConId = kwargs.get('m_deltaNeutralConId', 0)
        self.m_deltaNeutralSettlingFirm = kwargs.get('m_deltaNeutralSettlingFirm', '')
        self.m_deltaNeutralClearingAccount = kwargs.get('m_deltaNeutralClearingAccount', '')
        self.m_deltaNeutralClearingIntent = kwargs.get('m_deltaNeutralClearingIntent', '')
        self.m_continuousUpdate = kwargs.get('m_continuousUpdate', False)
        self.m_referencePriceType = kwargs.get('m_referencePriceType', 0)
        self.m_basisPoints = kwargs.get('m_basisPoints', 0.0)
        self.m_basisPointsType = kwargs.get('m_basisPointsType', 0)
        self.m_scaleInitLevelSize = kwargs.get('m_scaleInitLevelSize', 0)
        self.m_scaleSubsLevelSize = kwargs.get('m_scaleSubsLevelSize', 0)
        self.m_scalePriceIncrement = kwargs.get('m_scalePriceIncrement', 0.0)
        self.m_scalePriceAdjustValue = kwargs.get('m_scalePriceAdjustValue', 0.0)
        self.m_scalePriceAdjustInterval = kwargs.get('m_scalePriceAdjustInterval', 0)
        self.m_scaleProfitOffset = kwargs.get('m_scaleProfitOffset', 0.0)
        self.m_scaleAutoReset = kwargs.get('m_scaleAutoReset', False)
        self.m_scaleInitPosition = kwargs.get('m_scaleInitPosition', 0)
        self.m_scaleInitFillQty = kwargs.get('m_scaleInitFillQty', 0)
        self.m_scaleRandomPercent = kwargs.get('m_scaleRandomPercent', False)
        self.m_hedgeType = kwargs.get('m_hedgeType', '')
        self.m_hedgeParam = kwargs.get('m_hedgeParam', '')
        self.m_clearingAccount = kwargs.get('m_clearingAccount', '')
        self.m_clearingIntent = kwargs.get('m_clearingIntent', '')
        self.m_notHeld = kwargs.get('m_notHeld', False)
        
        # Order state
        self.m_orderState = IBOrderState()

    def isbuy(self):
        """Check if this is a buy order"""
        return self.ordtype == self.Buy

    def issell(self):
        """Check if this is a sell order"""
        return self.ordtype == self.Sell

    def to_ibind_order(self, conid):
        """
        Convert this IBOrder to ibind order format
        
        Args:
            conid: Contract ID for the instrument
            
        Returns:
            dict: Order in ibind format
        """
        order_data = {
            'conid': conid,
            'orderType': self.m_orderType,
            'side': self.m_action,
            'quantity': self.m_totalQuantity,
            'tif': self.m_tif,
        }
        
        # Add price for limit orders
        if self.m_orderType in ['LMT', 'LIMIT']:
            order_data['price'] = self.m_lmtPrice
        
        # Add stop price for stop orders
        if self.m_orderType in ['STP', 'STOP']:
            order_data['auxPrice'] = self.m_auxPrice
        
        # Add additional fields if set
        if self.m_account:
            order_data['account'] = self.m_account
        if self.m_orderRef:
            order_data['customerOrderId'] = self.m_orderRef
        if self.m_outsideRth:
            order_data['outsideRTH'] = self.m_outsideRth
        
        return order_data

    def __str__(self):
        return (f"IBOrder(action={self.m_action}, quantity={self.m_totalQuantity}, "
                f"type={self.m_orderType}, price={self.m_lmtPrice}, "
                f"tif={self.m_tif}, orderId={self.m_orderId})")

    def __repr__(self):
        return self.__str__()


# Backward compatibility aliases
Order = IBOrder
OrderState = IBOrderState