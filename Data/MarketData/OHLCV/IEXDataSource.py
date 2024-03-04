#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime
import pandas as pd
import pandas_datareader.data as web
from Data.Interface import StaticDataSourceInterface as StaticDataSourceInterface

"""
Created on Wed Jan 24 12:59:17 2024

@author: clemmie
"""

class IEXDataSource(StaticDataSourceInterface.StaticDataSourceInterface):
    
    def __init__(self,stock,start,end):
        self.stock = stock
        self.start = start
        self.end = end
        self.api_key = os.getenv('IEX_API_KEY')
    
    def getData(self):
        iex = web.IEXDailyReader(self.stock,self.start,api_key=self.api_key)
        iex_df = iex.read()
        return iex_df