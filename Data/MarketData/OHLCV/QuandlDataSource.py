#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 13:58:48 2024

@author: clemmie
"""

import os
from datetime import datetime
import pandas as pd
import quandl
from Data.Interface import StaticDataSourceInterface as StaticDataSourceInterface

class QuandlDataSource(StaticDataSourceInterface.StaticDataSourceInterface):
    
    def __init__(self,ticker):
        self.ticker = ticker
        self.api_key = os.getenv('QUANDL_API_KEY')
    
    def getData(self):
        data = quandl.get(self.ticker)
        return data