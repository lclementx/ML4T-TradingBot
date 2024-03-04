#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 12:40:59 2024

@author: clemmie
"""
from Data.Interface import ParserInterface
import pandas as pd
from collections import namedtuple, Counter, defaultdict
from pathlib import Path
from Utils import TimeUtils as tu
from time import time as time
from struct import unpack
from collections import namedtuple, Counter, defaultdict

class LOBSTERITCHParser(ParserInterface.ParserInterface):
    types = {1: 'submission',
         2: 'cancellation',
         3: 'deletion',
         4: 'execution_visible',
         5: 'execution_hidden',
         7: 'trading_halt'}
    

    def __init__(self,levels=10):
        self.levels = levels
        
    def parse(self,messages,orders,trading_date):
        ##Add date to time
        messages.time = pd.to_timedelta(messages.time, unit='s')
        messages['trading_date'] = pd.to_datetime(trading_date)
        messages.time = messages.trading_date.add(messages.time)
        messages.drop('trading_date', axis=1, inplace=True)
        
        ##Merge the dataset
        data = pd.concat([messages, orders], axis=1)
        return data

    