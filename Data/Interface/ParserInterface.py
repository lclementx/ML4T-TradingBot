#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 12 15:55:37 2024

Parser Interface

@author: clemmie
"""
from typing import TypeVar, Generic

T = TypeVar('T')

class ParserInterface(Generic[T]):

    def parse(self) -> T:
        pass