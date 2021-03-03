import sys
from datetime import datetime, timedelta, date
import trading_calendars as tc
import pandas_market_calendars as mcal
import pandas as pd
import ast
import redis
import time
from datetime import datetime, timedelta
from calc_module import range_data_from_symbol, best_call_trades, best_put_trades, stock_volume
from calc_module import prob_move_pct, prob_move_sigma, implied_forward, amt_to_invest, div_details
nyse = mcal.get_calendar('NYSE')
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TIMEOUT = 1800
SYMBOL_LIST = ["AAL","AAPL","ACB","AI","AMC","AMD","AMZN","APHA","ARKK","ATNX","B","BA","BABA","BAC","BB","BIG","BLNK","BNGO","C","CCIV","CCL","CLOV","COST","CRSR","DKNG","DNN","E","EEM","ET","EWZ","F","FB","FSLY","FSR","FUBO","FXI","G","GDX","GE","GLD","GM","GME","GO","GOLD","GSAT","GTT","HUGE","HYG","HYLN","IMO","IPO","IWM","K","KMPH","L","LAZR","LI","LMND","MARA","MSFT","MU","MVIS","NIO","NOK","NVDA","PINS","PLTR","PLUG","PSTH","PTON","QQQ","R","RIOT","RKT","RSI","SE","SENS","SI","SKT","SLV","SNAP","SNDL","SOS","SOXL","SPCE","SPY","SQ","SQQQ","T","TD","TGT","TLRY","TLT","TSLA","TSM","TV","TWTR","TXMD","USD","UUUU","UVXY","UWM","UWMC","V","VXX","WKHS","X","XL","XLE","XLF","XPEV","ZM"]

a = nyse.valid_days(start_date=str(date.today()), end_date=str(date.today()+timedelta(100)))
TRADING_DAYS = [str(i.date()) for i in a]

def check_is_trading():
    curr_date = str(date.today())
    if curr_date in TRADING_DAYS:
        r.hset(curr_date,"trading_date","yes")
    else:
        r.hset(curr_date,"trading_date","no")

def run_caching():
    for i in SYMBOL_LIST:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(1)
        prob_move_pct(i,30,5)
        time.sleep(1)
        amt_to_invest(i,7)
        time.sleep(1)


while True:
    d1 = datetime.now()
    curr_date = str(date.today())
    open_time = d1.replace(hour=9)
    open_time = open_time.replace(minute=30)
    close_time = d1.replace(hour=16)
    close_time = close_time.replace(minute=30)
    if r.hget(curr_date,"trading_date") == "yes":
        r.hset(curr_date,"cache_exists","yes")
        run_caching()
    elif not r.hget(curr_date,"cache_exists"):
        r.hset(curr_date,"cache_exists","yes")
        run_caching()
    check_is_trading()
    time.sleep(CACHE_TIMEOUT)
