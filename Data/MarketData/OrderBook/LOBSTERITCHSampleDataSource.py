#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 11:53:17 2024

@author: clemmie
"""
from pathlib import Path
from Data.Interface import StaticDataSourceInterface
from itertools import chain
import pandas as pd

class LOBSTERITCHSampleDataSource(StaticDataSourceInterface.StaticDataSourceInterface):
    
    #Not worth scaling for sample data for now - need to subscribe to LOBSTER Data
    def getData(self,file_name:str):
        ##Download the file
        order_file_path = Path("/Users/clemmie/Documents/Python/TradingBot/Data/MarketData/Resources/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_orderbook_10.csv")
        message_file_path = Path("/Users/clemmie/Documents/Python/TradingBot/Data/MarketData/Resources/LOBSTER_SampleFile_AMZN_2012-06-21_10/AMZN_2012-06-21_34200000_57600000_message_10.csv")
        price = list(chain(*[('Ask Price {0},Bid Price {0}'.format(i)).split(',') for i in range(10)]))
        size = list(chain(*[('Ask Size {0},Bid Size {0}'.format(i)).split(',') for i in range(10)]))
        cols = list(chain(*zip(price, size)))
        orders = pd.read_csv(order_file_path, header=None, names=cols).reset_index()
        messages = pd.read_csv(message_file_path,header=None,names=['time', 'type', 'order_id', 'size', 'price', 'direction'])
        
        return orders, messages