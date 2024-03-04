#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 12 13:32:38 2024

Static Data Interface for various data files. 
Stream/Live data is different in nature

@author: clemmie
"""
from typing import TypeVar, Generic

T = TypeVar('T')

class StaticDataSourceInterface(Generic[T]):

    def getData(self) -> T:
        pass