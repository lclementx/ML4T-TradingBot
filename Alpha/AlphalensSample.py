#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 19 16:24:44 2024

@author: clemmie
"""

import re
from alphalens.utils import get_clean_factor_and_forward_returns
from alphalens.performance import *
from alphalens.plotting import *
from alphalens.tears import *

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from tqdm import tqdm as tqdm
import talib as tl

sns.set_style('whitegrid')


### Not gonna use Quantopian to build alphas cause it depends on zipline

#%%

### Create mean reversion factor - the z-score for the last monthly return relative to the monthly returns over the last year: (monthly_return - mean ) / std <-- z-score

start_date = '2014-01-01'
end_date = '2024-01-01'

'''1. GET S&P 500 Equities data into Resources/data/assets'''
sp_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
sp500_constituents = pd.read_html(sp_url, header=0)[0]
equities = sp500_constituents['Symbol'].values
df = yf.download(' '.join(equities),start_date, end_date, auto_adjust=True)

#%%

prices_df = df.dropna(axis=1)
# Calculate daily returns
#prices_df.pivot(columns='Ticker',values='Close')
idx = pd.IndexSlice
close_prices_df = prices_df.loc[:,idx['Close',:]]
close_prices_df = close_prices_df.droplevel(level=0,axis=1)
volume_prices_df = prices_df.loc[:,idx['Volume',:]]
volume_prices_df

monthly_returns = close_prices_df.pct_change(periods=21)
yearly_returns = close_prices_df.pct_change(periods=252)
yearly_returns_mean = yearly_returns.rolling(window=252).mean()
yearly_returns_std = yearly_returns.rolling(window=252).std()
factors = (monthly_returns - yearly_returns_mean) / yearly_returns_std
factors = factors.dropna()
factors = factors.reset_index()
factors = factors.rename({'Ticker':'asset'},axis=1)
factors = factors.melt(id_vars='Date',var_name='asset')
factors = factors.set_index('Date')
factors = factors.groupby(['Date','asset'])['value'].mean() #mean is just a dummy function here cause it doesn't make any sense since all values are unique

start_date = factors.index.values[0][0]
prices = close_prices_df[close_prices_df.index >= start_date]

HOLDING_PERIODS = (5, 10, 21, 42)
QUANTILES = 5
alphalens_data = get_clean_factor_and_forward_returns(factor=factors,
                                                      prices=prices,
                                                      periods=HOLDING_PERIODS,
                                                      quantiles=QUANTILES)

#%%
alphalens_data.head()

### Summary Tear Sheet
create_summary_tear_sheet(alphalens_data)

#%%

### Returns Analysis
mean_return_by_q, std_err = mean_return_by_quantile(alphalens_data)
mean_return_by_q_norm = mean_return_by_q.apply(lambda x: x.add(1).pow(1/int(x.name[:-1])).sub(1))
plot_quantile_returns_bar(mean_return_by_q)
plt.tight_layout()
sns.despine()

### Cumulative Returns
mean_return_by_q_daily, std_err = mean_return_by_quantile(alphalens_data, by_date=True)
plot_cumulative_returns_by_quantile(mean_return_by_q_daily['5D'], period='5D', freq=None)
plt.tight_layout()
sns.despine()

### Violin plot - Return Distribution by Holding Period and Quintile
plot_quantile_returns_violin(mean_return_by_q_daily)
plt.tight_layout()
sns.despine();

### KEYYYY - INFORMATION COEFFICIENT
ic = factor_information_coefficient(alphalens_data)
plot_ic_ts(ic[['5D']])
plt.tight_layout()
sns.despine();

###INFORMATION COEFFICIENT BY HOLDING PERIOD
ic = factor_information_coefficient(alphalens_data)
ic_by_year = ic.resample('YE').mean()
ic_by_year.index = ic_by_year.index.year
ic_by_year.plot.bar(figsize=(14, 6))
plt.tight_layout();

#### QUINTILE TEARSHEET
create_turnover_tear_sheet(alphalens_data);


#%%

if False:
    print("still True")
