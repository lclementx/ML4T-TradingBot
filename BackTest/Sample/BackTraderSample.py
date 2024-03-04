#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 16 14:36:12 2024

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

#%%


# Create a Stratey
class SampleStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

class SampleMoreLogicStrategy(bt.Strategy):
    params = (
       ('exitbars', 5),
       )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
    
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
                self.log('BUY EXECUTED, Size: %.2f, Price: %.2f, Cost: %.2f, Comm: %.2f' % 
                         (order.executed.size,
                          order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                         
            elif order.issell():
                self.log('SELL EXECUTED, Size: %.2f, Price: %.2f, Cost: %.2f, Comm: %.2f' % 
                         (order.executed.size,
                          order.executed.price,
                          order.executed.value,
                          order.executed.comm))
    
            self.bar_executed = len(self)
    
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
    
        # Write down: no pending order
        self.order = None
        
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % 
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])
    
        ### Check whether we are in the market already
        if not self.position:
            if self.dataclose[0] < self.dataclose[-1]:
                # current close less than previous close
        
                if self.dataclose[-1] < self.dataclose[-2]:
                    # previous close less than the previous close
        
                    # BUY, BUY, BUY!!! (with all possible default parameters)
                    self.log('BUY CREATE, %.2f' % self.dataclose[0])
                    self.buy()
                
        else:
            if len(self) >= (self.bar_executed + self.params.exitbars):
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                
                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

class SMAStrategy(bt.Strategy):
    
    params = (
        ('maperiod',15),
        )
    
    def __init__(self):
        self.dataclose = self.datas[0].close

        # Add an Indicator
        self.sma = bt.indicators.MovingAverageSimple(self.datas[0], period=self.params.maperiod)
        
        
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
    
    def next(self):
        ## Log the closing price
        self.log('Close: %.2f' % self.dataclose[0])
        
        # If there is an order pending, we can't do much so return
        if self.order:
            return
        
        # Check if we are in the market
        if self.position:
            if self.dataclose[0] > self.sma[0]:
                ### BUY BUY BUYYY
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
        
        else:
            if self.dataclose[0] < self.sma[0]:
                ### SELL SELL SELL
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()
                
class HODLStrategy(bt.Strategy):
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        self.val_start = self.broker.get_cash() # keep the starting cash
        
    def nextstart(self):
        size = int(self.broker.get_cash()/ self.data)
        print('SIZE:  %.2f' % size)
        self.buy(size=size)
        
    
    def stop(self):
        print('Broker Value: %.2f' % self.broker.get_value())
        self.roi = (self.broker.get_value() / self.val_start) - 1.0
        print('ROI:        {:.2f}%'.format(100.0 * self.roi))
        
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))


class MeanReversionStrategy(bt.Strategy):
    
    params = (
        ('maperiod',15),
        ('pfast',20),
        ('pslow',50),
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
    
    def next(self):
        ## Log the closing price
        self.log('Close: %.2f' % self.dataclose[0])
        
        # If there is an order pending, we can't do much so return
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            if self.crossover > 0:
                ### BUY BUY BUYYY
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.order = self.buy()
            elif self.crossover < 0:
                ### SELL SELL SELL
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                self.order = self.sell()
        
        else:
    		# We are already in the market, look for a signal to CLOSE trades
            if len(self) >= (self.bar_executed + 5):
                self.log(f'CLOSE CREATE {self.dataclose[0]:2f}')
                self.order = self.close()

#%%

cerebro = bt.Cerebro()

### Set Principal
cerebro.broker.setcash(100000.0)

### Set Commission
cerebro.broker.setcommission(commission=0.001)

# Add a FixedSize sizer according to the stake
cerebro.addsizer(bt.sizers.FixedSize, stake=10)

# Add a Strategy
cerebro.addstrategy(MeanReversionStrategy)

## Add Analyzer
cerebro.addanalyzer(bt.analyzers.PyFolio, _name='Pyfolio')

### Add DataFeed
# Create a Data Feed
data = bt.feeds.PandasData(dataname=yf.download('MSFT', '2020-01-01', '2024-01-01', auto_adjust=True))
# Add the Data Feed to Cerebro
cerebro.adddata(data)

#### Run Strategy

print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

results = cerebro.run()
strat = results[0]
pyfoliozer = strat.analyzers.getbyname('Pyfolio')
returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()

print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
#plt.figure(figsize=((200,1000)))
#cerebro.plot(width=200,height=1000)
#plt.draw() #Tries to update the existing plot cause not sure why its not recognizing the cerebro plot

#### Benchmark returns - holding SPX for the period

benchmark_cerebro = bt.Cerebro()
benchmark_cerebro.broker.setcash(100000.0)
benchmark_cerebro.broker.setcommission(commission=0.001)
benchmark_cerebro.addsizer(bt.sizers.FixedSize, stake=10)
benchmark_cerebro.addstrategy(HODLStrategy)
benchmark_data = bt.feeds.PandasData(dataname=yf.download('SPY', '2020-01-01', '2024-01-01', auto_adjust=True))
benchmark_cerebro.addanalyzer(bt.analyzers.PyFolio, _name='Pyfolio')
benchmark_cerebro.adddata(benchmark_data)

benchmark_results = benchmark_cerebro.run()

benchmark_strat = benchmark_results[0]
benchmark_pyfoliozer = benchmark_strat.analyzers.getbyname('Pyfolio')
benchmark_returns = benchmark_pyfoliozer.get_pf_items()[0]


#### Plot pyfolio analysis
pf.create_full_tear_sheet(
    returns,
    positions=positions,
    #transactions=transactions,
    round_trips=True,
    benchmark_rets=benchmark_returns
    )
