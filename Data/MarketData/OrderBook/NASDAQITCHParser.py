#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 12 16:01:42 2024

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

class NASDAQITCHParser(ParserInterface.ParserInterface):
    
    event_codes = {'O': 'Start of Messages',
               'S': 'Start of System Hours',
               'Q': 'Start of Market Hours',
               'M': 'End of Market Hours',
               'E': 'End of System Hours',
               'C': 'End of Messages'}
    
    encoding = {'primary_market_maker': {'Y': 1, 'N': 0},
                'printable'           : {'Y': 1, 'N': 0},
                'buy_sell_indicator'  : {'B': 1, 'S': -1},
                'cross_type'          : {'O': 0, 'C': 1, 'H': 2},
                'imbalance_direction' : {'B': 0, 'S': 1, 'N': 0, 'O': -1}}
    formats = {
        ('integer', 2): 'H', # int of length 2 => format string 'H'
        ('integer', 4): 'I',
        ('integer', 6): '6s', # int of length 6 => parse as string, convert later
    
        ('integer', 8): 'Q',
        ('alpha', 1)  : 's',
        ('alpha', 2)  : '2s',
        ('alpha', 4)  : '4s',
        ('alpha', 8)  : '8s',
        ('price_4', 4): 'I',
        ('price_8', 8): 'Q',
    }
    
    message_types = None
    message_fields = None
    fstring = None
    alpha_formats = None
    alpha_lengths = None
    
    def __init__(self,store_path=None):
        if store_path == None:
            store_path = Path('/Users/clemmie/Documents/Python/TradingBot/Data/MarketData/Resources')
        self.store_path=store_path
    
    def clean_message_types(self,df):
        df.columns = [c.lower().strip() for c in df.columns]
        df.value = df.value.str.strip()
        df.name = (df.name
                   .str.strip() # remove whitespace
                   .str.lower()
                   .str.replace(' ', '_')
                   .str.replace('-', '_')
                   .str.replace('/', '_'))
        df.notes = df.notes.str.strip()
        df['message_type'] = df.loc[df.name == 'message_type', 'value']
        return df
    
    
    def get_alpha_formats(self, message_types):
        if self.alpha_formats is not None and self.alpha_length is not None:
            return self.alpha_formats, self.alpha_length
        
        alpha_fields = message_types[message_types.value == 'alpha'].set_index('name')
        alpha_msgs = alpha_fields.groupby('message_type')
        alpha_formats = {k: v.to_dict() for k, v in alpha_msgs.formats}
        alpha_length = {k: v.add(5).to_dict() for k, v in alpha_msgs.length}
        
        self.alpha_formats = alpha_formats
        self.alpha_length = alpha_length
        
        return alpha_formats, alpha_length
    
    def format_alpha(self, mtype, data, alpha_formats):
        """Process byte strings of type alpha"""
    
        for col in alpha_formats.get(mtype).keys():
            if mtype != 'R' and col == 'stock':
                data = data.drop(col, axis=1)
                continue
            data.loc[:, col] = data.loc[:, col].str.decode("utf-8").str.strip()
            if self.encoding.get(col):
                data.loc[:, col] = data.loc[:, col].map(self.encoding.get(col))
                data[col] = data[col].astype(int)
        return data
    
    def get_message_types(self):
        if self.message_types is not None and self.message_fields is not None and self.fstring is not None:
            return self.message_types, self.message_fields, self.fstring
        
        
        #Read raw specs from message_types and process the message types
        message_data = (pd.read_excel('/Users/clemmie/Documents/Python/TradingBot/Data/MarketData/Resources/message_types.xlsx',
                                  sheet_name='messages')
                    .sort_values('id')
                    .drop('id', axis=1))
        message_types = self.clean_message_types(message_data)
        message_types.message_type = message_types.message_type.ffill()
        message_types = message_types[message_types.name != 'message_type']
        message_types.value = (message_types.value
                           .str.lower()
                           .str.replace(' ', '_')
                           .str.replace('(', '')
                           .str.replace(')', ''))
        
        ## create (type, length) formatting tuples from ITCH specs:
        message_types.loc[:, 'formats'] = (message_types[['value', 'length']]
                            .apply(tuple, axis=1).map(self.formats))
    
        
        #generate message fields and format string
        message_fields, fstring = {}, {}
        for t, message in message_types.groupby('message_type'):
            message_fields[t] = namedtuple(typename=t, field_names=message.name.tolist())
            fstring[t] = '>' + ''.join(message.formats.tolist())
    
    
        self.message_types = message_types
        self.message_fields = message_fields
        self.fstring = fstring
        
        return message_types, message_fields, fstring
    
    def store_messages(self,m,file_path=None,file_name='nasdaq_itch.h5'):
        """Handle occasional storing of all messages"""
        path = file_path / file_name
        itch_store = str(path)
        message_types, message_fields, fstring = self.get_message_types()
        
        ##Extract alphanumeric fields
        alpha_formats, alpha_length = self.get_alpha_formats(message_types)
        
        with pd.HDFStore(itch_store) as store:
            for mtype, data in m.items():
                # convert to DataFrame
                data = pd.DataFrame(data)
    
                # parse timestamp info
                data.timestamp = data.timestamp.apply(int.from_bytes, byteorder='big')
                data.timestamp = pd.to_timedelta(data.timestamp)
    
                # apply alpha formatting
                if mtype in alpha_formats.keys():
                    data = self.format_alpha(mtype, data, alpha_formats)
    
                s = alpha_length.get(mtype)
                if s:
                    s = {c: s.get(c) for c in data.columns}
                dc = ['stock_locate']
                if m == 'R':
                    dc.append('stock')
                try:
                    store.append(mtype,
                              data,
                              format='t',
                              min_itemsize=s,
                              data_columns=dc)
                except Exception as e:
                    print(e)
                    print(mtype)
                    print(data.info())
                    print(pd.Series(list(m.keys())).value_counts())
                    data.to_csv('data.csv', index=False)
                    return 1
        return 0

    def parse(self, file_name):
        messages = defaultdict(list)
        message_count = 0
        message_type_counter = Counter()
        message_types, message_fields, fstring = self.get_message_types()

        start = time()
        with file_name.open('rb') as data:
            while True:
        
                # determine message size in bytes
                message_size = int.from_bytes(data.read(2), byteorder='big', signed=False)
                
                # get message type by reading first byte
                message_type = data.read(1).decode('ascii')        
                message_type_counter.update([message_type])
        
                # read & store message
                record = data.read(message_size - 1)
                message = message_fields[message_type]._make(unpack(fstring[message_type], record))
                messages[message_type].append(message)
                
                # deal with system events
                if message_type == 'S':
                    seconds = int.from_bytes(message.timestamp, byteorder='big') * 1e-9
                    print('\n', self.event_codes.get(message.event_code.decode('ascii'), 'Error'))
                    print(f'\t{tu.format_time(seconds)}\t{message_count:12,.0f}')
                    if message.event_code.decode('ascii') == 'C':
                        self.store_messages(messages,file_path=self.store_path)
                        break
                message_count += 1
        
                if message_count % 2.5e7 == 0:
                    seconds = int.from_bytes(message.timestamp, byteorder='big') * 1e-9
                    d = tu.format_time(time() - start)
                    print(f'\t{tu.format_time(seconds)}\t{message_count:12,.0f}\t{d}')
                    res = self.store_messages(messages,file_path=self.store_path)
                    if res == 1:
                        print(pd.Series(dict(message_type_counter)).sort_values())
                        break
                    messages.clear()
        
        print('Duration:', tu.format_time(time() - start))
    