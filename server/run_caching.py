import sys
from datetime import datetime, timedelta, date
import pandas as pd
import ast
import redis
import time
from datetime import datetime, timedelta
from calc_module import range_data_from_symbol, best_call_trades, best_put_trades, stock_volume
from calc_module import prob_move_pct, prob_move_sigma, implied_forward, amt_to_invest, div_details
from cache_module import check_is_trading
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TIMEOUT = 1800
SYMBOL_LIST = ["AAL","AAPL","ACB","AI","AMC","AMD","AMZN","APHA","ARKK","ATNX","B","BA","BABA","BAC","BB","BIG","BLNK","BNGO","C","CCIV","CCL","CLOV","COST","CRSR","DKNG","DNN","E","EEM","ET","EWZ","F","FB","FSLY","FSR","FUBO","FXI","G","GDX","GE","GLD","GM","GME","GO","GOLD","GSAT","GTT","HUGE","HYG","HYLN","IMO","IPO","IWM","K","KMPH","L","LAZR","LI","LMND","MARA","MSFT","MU","MVIS","NIO","NOK","NVDA","OCGN","PINS","PLTR","PLUG","PSTH","PTON","QQQ","R","RIOT","RKT","RSI","SE","SENS","SI","SKT","SLV","SNAP","SNDL","SOS","SOXL","SPCE","SPY","SQ","SQQQ","T","TD","TGT","TLRY","TLT","TSLA","TSM","TV","TWTR","TXMD","USD","UUUU","UVXY","UWM","UWMC","V","VXX","WKHS","X","XL","XLE","XLF","XPEV","ZM"]


def run_caching():
    for i in SYMBOL_LIST:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(1)
        prob_move_pct(i,30,5)
        time.sleep(1)
        amt_to_invest(i,7)
        time.sleep(1)

while True:
    check_is_trading()
    d1 = datetime.now()
    curr_date = str(date.today())
    open_time = d1.replace(hour=9)
    open_time = open_time.replace(minute=30)
    close_time = d1.replace(hour=16)
    close_time = close_time.replace(minute=30)
    if r.hget(curr_date,"trading_date") == "yes":
        run_caching()
        r.hset(curr_date,"cache_exists","yes")
    elif not r.hget(curr_date,"cache_exists"):
        run_caching()
        r.hset(curr_date,"cache_exists","yes")
    time.sleep(CACHE_TIMEOUT)
