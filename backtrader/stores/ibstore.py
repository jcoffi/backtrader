#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015-2023 Daniel Rodriguez
# Migrated from ibpy to ibind for better maintainability and modern Python support
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

# Import the new ibind-based implementation
from .ibstore_ibind import IBStoreIbind as IBStore
from .ibstore_ibind import RTVolume, MetaSingleton, Contract

# Re-export commonly used utilities for backward compatibility
from backtrader import TimeFrame, Position
from backtrader.metabase import MetaParams
from backtrader.utils.py3 import bytes, bstr, queue, with_metaclass, long
from backtrader.utils import AutoDict, UTC

__all__ = ['IBStore', 'RTVolume', 'MetaSingleton', 'Contract']