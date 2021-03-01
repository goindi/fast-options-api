import sys
from datetime import datetime, timedelta, date
import trading_calendars as tc
import pandas_market_calendars as mcal
import pandas as pd
import ast
import redis
import time
from calc_module import range_data_from_symbol, best_call_trades, best_put_trades, stock_volume
from calc_module import prob_move_pct, prob_move_sigma, implied_forward, amt_to_invest, div_details
nyse = mcal.get_calendar('NYSE')
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TIMEOUT = 120
SYMBOL_LIST = ['IBM','GME','PLTR','SPY','TSLA','C','AAPL','BBBY','BB','SNDL','APHA']
a = nyse.valid_days(start_date=str(date.today()), end_date=str(date.today()+timedelta(100)))
TRADING_DAYS = [str(i.date()) for i in a]

def check_is_trading():
    curr_date = str(date.today())
    if curr_date in TRADING_DAYS:
        r.hset(curr_date,"trading","yes")
    else:
        r.hset(curr_date,"trading","no")

while True:
    for i in SYMBOL_LIST:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(1)
        best_call_trades(i, 7)
        time.sleep(2)
        prob_move_pct(i,30,5)
        time.sleep(2)
    check_is_trading()
    time.sleep(200)
