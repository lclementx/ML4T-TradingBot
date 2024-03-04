#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 16:03:36 2024

@author: clemmie
"""

#%%
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import backtrader as bt
import yfinance as yf
import matplotlib.pyplot as plt
import pyfolio as pf
import pandas as pd
import numpy as np
from backtrader.feeds import PandasData


#%%
class MeanReversionWithTradeStrategy(bt.Strategy):
    
    params = (
        ('maperiod',15),
        ('pfast',20),
        ('pslow',50),
        ('n_positions', 10),
        ('min_positions', 5),
        ('verbose', False),
        )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # Instantiate moving averages
        self.slow_sma = bt.indicators.MovingAverageSimple(self.datas[0], 
                        period=self.params.pslow)
        self.fast_sma = bt.indicators.MovingAverageSimple(self.datas[0], 
                        period=self.params.pfast)

        # Add an Indicator
        self.crossover = bt.indicators.CrossOver(self.fast_sma,self.slow_sma)
        
        
        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        ### Graphs
        bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        bt.indicators.WeightedMovingAverage(self.datas[0], period=25).subplot = True
        bt.indicators.StochasticSlow(self.datas[0])
        bt.indicators.MACDHisto(self.datas[0])
        rsi = bt.indicators.RSI(self.datas[0])
        bt.indicators.SmoothedMovingAverage(rsi, period=10)
        bt.indicators.ATR(self.datas[0]).plot = True

        
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
    
        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
    
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
    
            self.bar_executed = len(self)
    
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
    
        self.order = None
        
   # bt calls prenext instead of next unless
    # all datafeeds have current values
    # => call next to avoid duplicating logic
    def prenext(self):
        self.next()

    
    def next(self):
        today = self.datas[0].datetime.date()

        positions = [d._name for d, pos in self.getpositions().items() if pos]
        up, down = {}, {}
        missing = not_missing = 0
        for data in self.datas:
            if data.datetime.date() == today:
                if data.Predicted[0] > 0:
                    up[data._name] = data.Predicted[0]
                elif data.Predicted[0] < 0:
                    down[data._name] = data.Predicted[0]

        # sort dictionaries ascending/descending by value
        # returns list of tuples
        shorts = sorted(down, key=down.get)[:self.p.n_positions]
        longs = sorted(up, key=up.get, reverse=True)[:self.p.n_positions]
        n_shorts, n_longs = len(shorts), len(longs)
        self.log(n_shorts,n_longs)
        
        # only take positions if at least min_n longs and shorts
        if n_shorts < self.p.min_positions or n_longs < self.p.min_positions:
            longs, shorts = [], []
        for ticker in positions:
            if ticker not in longs + shorts:
                self.order_target_percent(data=ticker, target=0)
                self.log(f'{ticker},CLOSING ORDER CREATED')
        
        short_target = -1 / max(self.p.n_positions, n_shorts)
        long_target = 1 / max(self.p.n_positions, n_longs)
        for ticker in shorts:
            self.order_target_percent(data=ticker, target=short_target)
            self.log('{ticker},SHORT ORDER CREATED')
        for ticker in longs:
            self.order_target_percent(data=ticker, target=long_target)
            self.log('{ticker},LONG ORDER CREATED')
                
class SignalData(PandasData):
    OHLCV = ['Open', 'High', 'Low', 'Close', 'Volume']
    """
    Define pandas DataFrame structure
    """
    cols = OHLCV + ['Predicted']

    # create lines
    lines = tuple(cols)

    # define parameters
    params = {c: -1 for c in cols}
    params.update({'datetime': None})
    params = tuple(params.items())
    
#%%

#What we need to do to replicate the order placement strategy is calcualte average dollar volume for the dataset and use that as rank

start_date = '2023-01-01'
end_date = '2024-01-01'

'''1. GET S&P 500 Equities data into Resources/data/assets'''
sp_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
sp500_constituents = pd.read_html(sp_url, header=0)[0]
equities = sp500_constituents['Symbol'].values
df = yf.download(' '.join(equities),start_date, end_date, auto_adjust=True)

#%%

N_LONGS = 5
N_SHORTS = 5

prices_df = df.dropna(axis=1)
rank_df = (prices_df['Close'] * prices_df['Volume']).rank()
rank_df.columns =  pd.MultiIndex.from_product([['Predicted'],rank_df.columns])
prices_df = pd.concat([prices_df,rank_df],axis=1)

price_by_ticker_df = prices_df.swaplevel(i=0,j=1,axis=1)
price_by_ticker_df.columns

unique_tickers = np.unique([ x[0] for x in price_by_ticker_df.columns.values ])


#%%
cerebro = bt.Cerebro()

### Set Principal
cerebro.broker.setcash(100000.0)

### Set Commission
cerebro.broker.setcommission(commission=0.001)

# Add a FixedSize sizer according to the stake
cerebro.addsizer(bt.sizers.FixedSize, stake=10)

for ticker in unique_tickers:
    ticker_df = price_by_ticker_df[ticker]
    ticker_data = SignalData(dataname=ticker_df)
    cerebro.adddata(ticker_data, name=ticker)

# Add a Strategy
cerebro.addstrategy(MeanReversionWithTradeStrategy)

## Add Analyzer
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='Pyfolio')

results = cerebro.run()
strat = results[0]
pyfoliozer = strat.analyzers.getbyname('Pyfolio')
returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()


#### Plot pyfolio analysis
pf.create_full_tear_sheet(
    returns,
    positions=positions,
    transactions=transactions,
    round_trips=True,
    )
