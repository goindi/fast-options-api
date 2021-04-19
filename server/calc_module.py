import sys
import math
from datetime import datetime, timedelta, date
from wallstreet import Call, Put, Stock
from scipy import stats
import yfinance as yf
#import trading_calendars as tc
import pandas_market_calendars as mcal
import pandas as pd
import numpy as np
from scipy.stats import norm
import ast
import redis
from random import randint
#from cache_module import is_cache_good
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TIMEOUT = 1200
FASTER_TIMEOUT = 900

nyse = mcal.get_calendar('NYSE')
a = nyse.valid_days(start_date=str(date.today()), end_date=str(date.today()+timedelta(100)))
TRADING_DAYS = [str(i.date()) for i in a]

def get_expiries_bracket(symbol, num_of_days):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|getexpiries|{num_of_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|getexpiries|{num_of_days}','value'))
    c = Call(symbol)
    expiries = c.expirations
    curr_date = str(datetime.date(datetime.now()))
    longer_expiry = expiries[-1]
    shorter_expiry = expiries[0]
    shorter_day_bound = (datetime.strptime(shorter_expiry,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
    longer_day_bound = (datetime.strptime(longer_expiry,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        if days_to_exp < num_of_days and days_to_exp > shorter_day_bound  :
            shorter_day_bound = days_to_exp
            shorter_expiry = i
            longer_day_bound = days_to_exp
            longer_expiry = i
        elif days_to_exp >= num_of_days:
            longer_day_bound = days_to_exp
            longer_expiry = i
            break
    shorter_weight = 1;
    if longer_day_bound != shorter_day_bound:
        shorter_weight = (longer_day_bound - num_of_days) / (longer_day_bound - shorter_day_bound)
    return_dict =  {'shorter_expiry':shorter_expiry,'longer_expiry':longer_expiry,'shorter_day_bound':shorter_day_bound,'longer_day_bound':longer_day_bound, 'shorter_weight':shorter_weight}
    r.hset(f'{symbol}|getexpiries|{num_of_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|getexpiries|{num_of_days}','value',str(return_dict))
    return return_dict

def get_strike_bracket(strikes, price_target):
    #strikes = call_object.strikes
    higher_strike = strikes[0]
    lower_strike = strikes[0]
    if price_target < strikes[0]:
        return (-1,-1)
    if price_target > strikes[-1]:
        return (-10,-10)
    for i in strikes:
        if i < price_target and i > lower_strike:
            lower_strike = i
            higher_strike = i
        elif i >= price_target:
            higher_strike = i
            break;
    lower_weight = 1
    if higher_strike != lower_strike:
        lower_weight = (higher_strike - price_target)/(higher_strike - lower_strike)
    return  {'lower_strike':lower_strike,'higher_strike':higher_strike, 'lower_weight':lower_weight}


def get_delta(symbol:str, percent_move:float, expiry:str):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|getdelta|{percent_move:.2f}|{expiry}'):
        return ast.literal_eval(r.hget(f'{symbol}|getdelta|{percent_move:.2f}|{expiry}','value'))
    s = Stock(symbol)
    up_px = s.price*(1+percent_move/100)
    down_px = s.price*(1-percent_move/100)
    call = Call(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    up_delta_dict = get_strike_bracket(call.strikes, up_px)
    call.set_strike(up_delta_dict['lower_strike'])
    delta1 = call.delta()*up_delta_dict['lower_weight']
    call.set_strike(up_delta_dict['higher_strike'])
    delta2 = call.delta()*(1-up_delta_dict['lower_weight'])
    delta_up_move = delta1 + delta2

    put = Put(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    down_delta_dict = get_strike_bracket(put.strikes, down_px)
    put.set_strike(down_delta_dict['lower_strike'])
    delta1 = -put.delta()*down_delta_dict['lower_weight']
    put.set_strike(down_delta_dict['higher_strike'])
    delta2 = -put.delta()*(1-down_delta_dict['lower_weight'])
    delta_down_move = delta1 + delta2
    return_dict =  {'delta_up':delta_up_move,'delta_down':delta_down_move}
    r.hset(f'{symbol}|getdelta|{percent_move:.2f}|{expiry}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|getdelta|{percent_move:.2f}|{expiry}','value',str(return_dict))
    return return_dict

def get_nd2(symbol:str, percent_move:float, expiry:str):
    y = yf.Ticker(symbol)
    info = y.info
    price = (info['bid']+info['ask'])/2
    up_px = price*(1+percent_move/100)
    down_px = price*(1-percent_move/100)
    expiry = f'{expiry[6:10]}-{expiry[3:5]}-{expiry[0:2]}'
    o = y.option_chain(date='2021-03-12')
    up_delta_dict = get_strike_bracket(o.calls.strike.tolist(), up_px)
    x = o.calls
    x['q'] = info['dividendYield']
    x['r']=0.001
    x['t'] = 8/365
    x['s'] = price
    x['d1']= (np.log(x.s/x.strike)+x.t*(x.r-x.q+x.impliedVolatility*x.impliedVolatility/2))/(x.impliedVolatility*np.sqrt(x.t))
    #x['nd1'] = norm.cdf(x.d1)
    x['d2'] = x.d1-x.impliedVolatility*np.sqrt(x.t)
    x['nd2'] = norm.cdf(x.d2)



    #call.set_strike(up_delta_dict['lower_strike'])
    delta1 = (x.loc[x['strike'] == up_delta_dict['lower_strike']]['nd2'])*up_delta_dict['lower_weight']
    #call.set_strike(up_delta_dict['higher_strike'])
    delta2 = (x.loc[x['strike'] == up_delta_dict['higher_strike']]['nd2'])*(1-up_delta_dict['lower_weight'])
    #delta2 = call.delta()*(1-up_delta_dict['lower_weight'])
    delta_up_move = delta1 + delta2

    #put = Put(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    down_delta_dict = get_strike_bracket(o.puts.strike.tolist(), down_px)

    y = o.puts
    y['q'] = info['dividendYield']
    y['r']=0.001
    y['t'] = 8/365
    y['s'] = price
    y['d1']= (np.log(y.s/y.strike)+y.t*(y.r-y.q+y.impliedVolatility*y.impliedVolatility/2))/(y.impliedVolatility*np.sqrt(y.t))
    #x['nd1'] = norm.cdf(x.d1)
    y['d2'] = y.d1-y.impliedVolatility*np.sqrt(y.t)
    y['nd2'] = norm.cdf(y.d2)
    #put.set_strike(down_delta_dict['lower_strike'])
    #delta1 = -put.delta()*down_delta_dict['lower_weight']
    delta1 = (y.loc[y['strike'] == down_delta_dict['lower_strike']]['nd2'])*down_delta_dict['lower_weight']

    #put.set_strike(down_delta_dict['higher_strike'])
    #delta2 = -put.delta()*(1-down_delta_dict['lower_weight'])
    delta2 = (y.loc[y['strike'] == down_delta_dict['higher_strike']]['nd2'])*(1-down_delta_dict['lower_weight'])
    delta_down_move = delta1 + delta2
    return {'delta_up':delta_up_move,'delta_down':delta_down_move}

def get_atm_ivol(s, ndays=30):
    #Need to fix for divs, borrow etc to find atm
    symbol = s.ticker
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|getatmivol|{ndays}'):
        return ast.literal_eval(r.hget(f'{symbol}|getatmivol|{ndays}','value'))
    expiry_dict = get_expiries_bracket(symbol, ndays)
    #First Shorter One
    x = expiry_dict['shorter_expiry']
    shorter_call = Call(symbol,d=int(x[0:2]),m=int(x[3:5]),y=int(x[6:10]))
    strike_dict = get_strike_bracket(shorter_call.strikes, s.price)
    shorter_call.set_strike(strike_dict['lower_strike'])
    lower_vol = shorter_call.implied_volatility()
    shorter_call.set_strike(strike_dict['higher_strike'])
    higher_vol = shorter_call.implied_volatility()
    shorter_ivol = lower_vol*strike_dict['lower_weight'] + higher_vol*(1-strike_dict['lower_weight'])
    #Now longer One
    x = expiry_dict['longer_expiry']
    longer_call = Call(symbol,d=int(x[0:2]),m=int(x[3:5]),y=int(x[6:10]))
    strike_dict = get_strike_bracket(longer_call.strikes, s.price)
    longer_call.set_strike(strike_dict['lower_strike'])
    lower_vol = longer_call.implied_volatility()
    longer_call.set_strike(strike_dict['higher_strike'])
    higher_vol = longer_call.implied_volatility()
    longer_ivol = lower_vol*strike_dict['lower_weight'] + higher_vol*(1-strike_dict['lower_weight'])
    implied_ivol = shorter_ivol*expiry_dict['shorter_weight'] + longer_ivol*(1-expiry_dict['shorter_weight'])
    one_sigma_move_ndays_day = implied_ivol*math.sqrt(ndays/365)

    return_dict =  (implied_ivol, one_sigma_move_ndays_day)
    r.hset(f'{symbol}|getatmivol|{ndays}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|getatmivol|{ndays}','value',str(return_dict))
    return return_dict

def range_data_from_symbol(symbol, ndays=7, sigma=1.15):
    symbol = symbol.upper()
    try:
        if is_cache_good(f'{symbol}|range|{ndays}|{sigma}'):
            return ast.literal_eval(r.hget(f'{symbol}|range|{ndays}|{sigma}','value'))
        r.hset(f'{symbol}|range|{ndays}|{sigma}','time',datetime.utcnow().strftime('%s'))
        s = Stock(symbol)
        prob = prob_move_pct(symbol, ndays,0)
        if "error" in prob:
            return {"error":"No options were found"}
        my_tuple = get_atm_ivol(s, ndays)
        volume = stock_volume(symbol, ndays)
        return_dict = {}
        return_dict["symbol"] = symbol
        return_dict["desc"] = s.name
        return_dict["price"] = s.price
        return_dict["ivol"] = my_tuple[0]
        return_dict["low_range"] = s.price - s.price*my_tuple[1]*sigma
        return_dict["high_range"] = s.price + s.price*my_tuple[1]*sigma
        return_dict["volume_pct"] = volume["percentile"]
        return_dict["today_volume"] = volume["volume"]
        return_dict["avg_10d_volume"] = volume["avg_10d_volume"]
        return_dict["prob_up"] = prob["prob_up"]
        r.hset(f'{symbol}|range|{ndays}|{sigma}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|range|{ndays}|{sigma}','value',str(return_dict))
        return return_dict
    except:
        return {"symbol": "Error", "error": "No Data found for %s"%symbol}

def calculate_bollingers(s, ndays = 20, sigma = 2):
    #Need to update it intraday. Pushing the problem out for later
    #tp is Typical Price. A way to capture high and low (volatility)
    days_back=(ndays*2+10)/0.7 #need trading  days so 0.7
    df = s.historical(days_back=days_back, frequency='d')
    df['typical_price'] = (x['High']+x['Low']+x['Close'])/3
    df['SMA_close'] =  x['Adj Close'].rolling(window=ndays).mean()
    df['SMA_tp'] =  x['typical_price'].rolling(window=ndays).mean()
    df['std_close'] = x['Adj Close'].rolling(window=ndays).std()
    df['std_tp'] = x['typical_price'].rolling(window=ndays).std()
    df['bol_up_close'] = df['SMA_close'] + sigma*df['std_close']
    df['bol_down_close'] = df['SMA_close'] - sigma*df['std_close']
    df['bol_up_tp'] = df['SMA_tp'] + sigma*df['std_tp']
    df['bol_down_tp'] = df['SMA_tp'] - sigma*df['std_tp']

def kelly_fraction(win_prob : float, win_loss_ratio:float)->float:
    return win_prob - (1-win_prob)/win_loss_ratio

def best_call_trades(symbol, num_of_days):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|calltrade|{num_of_days}',3600):
        return ast.literal_eval(r.hget(f'{symbol}|calltrade|{num_of_days}','value'))
    try:
        c = Call(symbol)
        range_dict = range_data_from_symbol(symbol, num_of_days)
        curr_date = str(datetime.date(datetime.now()))
        expiries = c.expirations
        expiry_to_use = expiries[0]
        min_day_diff=1000
        for i in expiries:
            days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
            my_day_diff = abs(days_to_exp - num_of_days)
            if my_day_diff<min_day_diff:
                expiry_to_use = i
                min_day_diff = my_day_diff
        c = Call(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
        counter = 0
        spread_list = []
        strikes = c.strikes
        for i in strikes:
            if i >= range_dict["high_range"] and counter < 10:
                counter = counter+1
                c.set_strike(i)
                spread_list.append({'strike':i,'bid':c.bid,'ask':c.ask,'last':c.price,'using_last':'false','delta':c.delta()})

        max_amt = 0
        max_call_amt = 0
        best_spread = {}
        best_call_written = {}
        for i in spread_list:
            #for call
            prob_winning_call = 1 - i['delta'] # Not expiring in the money
            i['using_last']='false'
            if i['bid'] == 0 or i['ask'] == 0:
                i['bid'] = i['last']
                i['ask'] = i['last']
                i['using_last']='true'
            premium_call = i['bid']
            call_win_amt = premium_call*prob_winning_call
            if call_win_amt > max_call_amt:
                max_call_amt = call_win_amt
                best_call_written = i

            for j in spread_list:
                if i['strike'] < j['strike']:
                    #for spread

                    premium_per_dollar = (i['bid']-j['ask'])/(j['strike']-i['strike'])
                    spread_using_last = 'false'
                    if i['using_last'] == 'true' or  j['using_last'] == 'true': #If any leg uses last mark spread as last
                        spread_using_last = 'true'
                    prob_winning_spread = 1 - j['delta']
                    win_amt = premium_per_dollar*prob_winning_spread

                    if win_amt > max_amt:
                        max_amt = win_amt
                        if spread_using_last == 'true':
                            best_spread = {'strike_to_sell':i['strike'],'strike_to_buy':j['strike'], 'premium_received':i['last'], 'premium_paid':j['last'], 'expiry':expiry_to_use,'spread_using_last':spread_using_last}
                        else:
                            best_spread = {'strike_to_sell':i['strike'],'strike_to_buy':j['strike'], 'premium_received':i['bid'],'premium_paid':j['ask'], 'expiry':expiry_to_use,'spread_using_last':spread_using_last}

        best_call_written['expiry'] = expiry_to_use
        return_dict = {"symbol":symbol,'best_spread':best_spread,'best_call':best_call_written}
        if best_call_written:
            r.hset(f'{symbol}|calltrade|{num_of_days}','time',datetime.utcnow().strftime('%s'))
            r.hset(f'{symbol}|calltrade|{num_of_days}','value',str(return_dict))
        return return_dict
    except Exception as e:
        return {"error":"No options were found"}

def prob_move_pct(symbol:str, n_days:int, percent:float):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|pmovepct|{n_days}|{percent}'):
        return ast.literal_eval(r.hget(f'{symbol}|pmovepct|{n_days}|{percent}','value'))
    try:
        c = Call(symbol)
        curr_date = str(datetime.date(datetime.now()))
        expiries = c.expirations
        expiry_to_use = expiries[0]
        for i in expiries:
            days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
            expiry_to_use = i
            if days_to_exp >= n_days:
                break
        my_delta = get_delta(symbol, percent, expiry_to_use)
        return_dict = {"symbol":symbol,"move_percent":percent, 'expiry':expiry_to_use, "prob_down":my_delta['delta_down'],"prob_up":my_delta['delta_up'] }
        r.hset(f'{symbol}|pmovepct|{n_days}|{percent}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|pmovepct|{n_days}|{percent}','value',str(return_dict))
        return return_dict

    except:
        return {"error":"No options were found"}

def prob_move_sigma(symbol:str, n_days:int, sigma_fraction_to_use:float):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|pmovesigma|{n_days}|{sigma_fraction_to_use}'):
        return ast.literal_eval(r.hget(f'{symbol}|pmovesigma|{n_days}|{sigma_fraction_to_use}','value'))
    try:
        c = Call(symbol)
        expiries = c.expirations
        curr_date = str(datetime.date(datetime.now()))
        expiry_to_use = expiries[0]
        my_n_days = 0
        for i in expiries:
            days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
            expiry_to_use = i
            my_n_days = days_to_exp
            if days_to_exp >= n_days:
                break
        my_tuple = get_atm_ivol(Stock(symbol), my_n_days)
        my_percent = my_tuple[1]*100*sigma_fraction_to_use
        my_delta = get_delta(symbol, my_percent, expiry_to_use)
        prob_down = my_delta['delta_down']
        prob_up = my_delta['delta_up']
        norm_prob_down = 0
        norm_prob_up = 0
        if prob_up > prob_down:
            norm_prob_down = 0.5
            norm_prob_up = prob_up*0.5/prob_down
        else:
            norm_prob_up = 0.5
            norm_prob_down = prob_down*0.5/prob_up
        return_dict = {"symbol":symbol, "move_percent":my_percent, 'expiry':expiry_to_use, "prob_down":prob_down,"norm_prob_down":norm_prob_down,"prob_up":prob_up, "norm_prob_up":norm_prob_up}
        r.hset(f'{symbol}|pmovesigma|{n_days}|{sigma_fraction_to_use}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|pmovesigma|{n_days}|{sigma_fraction_to_use}','value',str(return_dict))
        return return_dict
    except:
        return {"error":"No options were found"}

def implied_forward(symbol, n_days):
    s = Stock(symbol)
    c = Call(symbol)
    curr_date = str(datetime.date(datetime.now()))
    expiries = c.expirations
    expiry_to_use = expiries[0]
    my_n_days = 0
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        my_n_days = days_to_exp
        if days_to_exp >= n_days:
            break
    call = Call(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    put = Put(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    bracket_dict = get_strike_bracket(call.strikes, s.price)
    forward = s.price
    if bracket_dict['lower_weight'] > 0.5:
        call.set_strike(bracket_dict['lower_strike'])
        put.set_strike(bracket_dict['lower_strike'])
        forward = bracket_dict['lower_strike'] - put.price + call.price
    else:
        call.set_strike(bracket_dict['higher_strike'])
        put.set_strike(bracket_dict['higher_strike'])
        forward = bracket_dict['higher_strike'] - put.price + call.price
    return {"symbol":symbol,"forward_price":forward,"current_price":s.price, "expiry":expiry_to_use}

def best_put_trades(symbol, num_of_days):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|puttrade|{num_of_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|puttrade|{num_of_days}','value'))
    try:
        p = Put(symbol)
        range_dict = range_data_from_symbol(symbol, num_of_days)
        curr_date = str(datetime.date(datetime.now()))
        expiries = p.expirations
        expiry_to_use = expiries[0]
        min_day_diff=1000
        for i in expiries:
            days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
            my_day_diff = abs(days_to_exp - num_of_days)
            if my_day_diff<min_day_diff:
                expiry_to_use = i
                min_day_diff = my_day_diff
        p = Put(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
        counter = 0
        spread_list = []
        strikes = p.strikes
        for i in reversed(strikes):
            if i <= range_dict["low_range"] and counter < 10:
                counter = counter+1
                p.set_strike(i)
                spread_list.append({'strike':i,'bid':p.bid,'ask':p.ask,'last':p.price,'using_last':'false','delta':-p.delta()})
        max_amt = 0
        max_put_amt = 0
        best_spread = {}
        best_put_written = {}
        spread_list.reverse()
        for i in spread_list:
            #for put
            prob_winning_put = 1 - i['delta']
            i['using_last']='false'
            if i['bid'] == 0 or i['ask'] == 0:
                i['bid'] = i['last']
                i['ask'] = i['last']
                i['using_last']='true'
            premium_put = i['bid']
            put_win_amt = premium_put*prob_winning_put
            if put_win_amt > max_put_amt:
                max_put_amt = put_win_amt
                best_put_written = i
            for j in spread_list:
                if i['strike'] > j['strike']:
                    #for spread
                    premium_per_dollar = (i['bid']-j['ask'])/abs(j['strike']-i['strike'])
                    spread_using_last = 'false'
                    if i['using_last'] == 'true' or  j['using_last'] == 'true': #If any leg uses last mark spread as last
                        spread_using_last = 'true'
                    prob_winning_spread = 1 - j['delta']
                    win_amt = premium_per_dollar*prob_winning_spread
                    if win_amt > max_amt:
                        max_amt = win_amt
                        if spread_using_last == 'true':
                            best_spread = {'strike_to_sell':i['strike'],'strike_to_buy':j['strike'], 'premium_received':i['last'], 'premium_paid':j['last'], 'expiry':expiry_to_use,'spread_using_last':spread_using_last}
                        else:
                            best_spread = {'strike_to_sell':i['strike'],'strike_to_buy':j['strike'], 'premium_received':i['bid'],'premium_paid':j['ask'], 'expiry':expiry_to_use,'spread_using_last':spread_using_last}

        best_put_written['expiry'] = expiry_to_use
        return_dict = {"symbol":symbol,'best_spread':best_spread,'best_put':best_put_written}
        if best_spread or best_put_written:
            r.hset(f'{symbol}|puttrade|{num_of_days}','time',datetime.utcnow().strftime('%s'))
            r.hset(f'{symbol}|puttrade|{num_of_days}','value',str(return_dict))
            return return_dict
    except:
        return {"error":"No options were found"}

def best_put_protection(symbol, num_of_days):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|putprotection|{num_of_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|putprotection|{num_of_days}','value'))
    try:
        p = Put(symbol)
        s = Stock(symbol)
        curr_date = str(datetime.date(datetime.now()))
        expiries = p.expirations
        expiry_to_use = expiries[0]
        for i in expiries:
            days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
            expiry_to_use = i
            if days_to_exp >= num_of_days:
                break
        p = Put(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
        counter = 0
        spread_list = []
        strikes = p.strikes
        for i in reversed(strikes):
            if i <= s.price and counter < 10:
                counter = counter+1
                p.set_strike(i)
                spread_list.append({'strike':i,'bid':p.bid,'ask':p.ask,'last':p.price,'using_last':'false','delta':-p.delta()})
        min_put_strength = 100000
        best_put = {}
        spread_list.reverse()
        for i in spread_list:
            #for put
            prob_in_the_money_put = i['delta']
            i['using_last']='false'
            if i['bid'] == 0 or i['ask'] == 0:
                i['bid'] = i['last']
                i['ask'] = i['last']
                i['using_last']='true'
            premium_put = i['ask']

            put_cost_per_money = premium_put/prob_in_the_money_put


            if put_cost_per_money < min_put_strength:
                min_put_strength = put_cost_per_money
                best_put = i

        best_put['expiry'] = expiry_to_use
        return_dict = {"symbol":symbol,'best_put':best_put}
        if best_put:
            r.hset(f'{symbol}|putprotection|{num_of_days}','time',datetime.utcnow().strftime('%s'))
            r.hset(f'{symbol}|putprotection|{num_of_days}','value',str(return_dict))
            return return_dict
    except:
        return {"error":"No options were found"}

def amt_to_invest(symbol:str,n_days:int):
    symbol=symbol.upper()
    if is_cache_good(f'{symbol}|kelly|{n_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|kelly|{n_days}','value'))
    try:
        prob_dict = prob_move_pct(symbol, n_days,0)
        if "error" in prob_dict:
            return {"error":"No options were found"}
        curr_date = str(datetime.date(datetime.now()))
        days_to_exp = abs(datetime.strptime(prob_dict['expiry'],'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        prob_dict2 = prob_move_pct(symbol, n_days,10)
        b = prob_dict2['prob_up']*0.1
        a = prob_dict2['prob_down']*0.1
        #Kelly_k is 1/3rd of the kelly = W/a - L/b
        # a is money lost when down and b is money made when up. since we are using 10% move the money made=money_lost = 10% so it cancels out
        #and we normalize a = 1 so b becomes b/a. And we use fractional
        kelly_k = prob_dict['prob_up'] -(1-prob_dict['prob_up'])/(prob_dict2['prob_up']/prob_dict2['prob_down'])
        return_dict = {"symbol":symbol, "kelly":2*prob_dict['prob_up'] - 1, "expiry":prob_dict['expiry'], "prob_up":prob_dict['prob_up'],"prob_down":prob_dict['prob_down'], "kelly2":prob_dict['prob_up']-0.5, "prob_up_n":prob_dict2['prob_up'],"prob_down_n":prob_dict2['prob_down'],"kelly_k":kelly_k/3}
        r.hset(f'{symbol}|kelly|{n_days}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|kelly|{n_days}','value',str(return_dict))
        return return_dict
    except:
        return {"error":"No options were found"}

def div_details(symbol:str):
    symbol = symbol.upper()
    y = yf.Ticker(symbol)
    info = y.info
    price = (info['bid']+info['ask'])/2
    if y.dividends.empty:
        div = "0"
        div_date = ""
        div_yld = "0"
    else:
        div = y.dividends[-1]
        div_date = str(y.dividends.index[-1])[0:10]
        div_yld = y.info['dividendYield']
    return {"symbol":symbol,'div':div, 'div_date':div_date, 'div_yld':div_yld, 'stock_price':price}

def crypto_range_data_from_symbol(symbol:str,n_days:int,sigma:float):
    symbol = symbol.upper()
    return_dict = {}
    if symbol in ['BTC','ETH']:
        symbol = f'{symbol}-USD'
    if is_cache_good(f'{symbol}|cryptorange|{n_days}|{sigma}'):
        return ast.literal_eval(r.hget(f'{symbol}|cryptorange|{n_days}|{sigma}','value'))
    try:
        y = yf.Ticker(symbol)
        info = y.info
        h = y.history()
        my_df = h.Close[-21:]
        curr_px = my_df[-1]
        std_dev = np.std(my_df[-21:-1])
        n_days_sigma = std_dev*math.sqrt(n_days)
        high_slope,high_intercept = np.polyfit(range(1,len(h)+1),h.High*10/h.High.mean(),1)
        low_slope,low_intercept = np.polyfit(range(1,len(h)+1),h.Low*10/h.Low.mean(),1)
        return_dict["symbol"] = symbol
        return_dict["desc"] = info['shortName']
        return_dict["price"] = curr_px
        return_dict["ivol"] = std_dev # realized vol.
        return_dict["low_range"] = curr_px - n_days_sigma*sigma
        return_dict["high_range"] = curr_px + n_days_sigma*sigma
        return_dict["today_volume"] =info['volume24Hr']
        return_dict["avg_10d_volume"] = info["averageVolume10days"]
        return_dict["high_slope"] = high_slope
        return_dict["low_slope"] = low_slope
        r.hset(f'{symbol}|cryptorange|{n_days}|{sigma}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|cryptorange|{n_days}|{sigma}','value',str(return_dict))
        return return_dict
    except:
        return {"symbol": "Error", "error": "No Data found for %s"%symbol}

def get_gamma_squeeze(symbol:str, n_days:int):
    symbol = symbol.upper()
    if is_cache_good(f'{symbol}|gamma|{n_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|gamma|{n_days}','value'))
    try:
        y = yf.Ticker(symbol)
        info = y.info
        price = (info['bid']+info['ask'])/2
        return_dict = {"symbol":symbol}
        return_dict['stock_float'] = info['sharesOutstanding']
        expiry_dict = get_expiries_bracket(symbol, n_days)
        expiry_to_use = expiry_dict['shorter_expiry']
        if expiry_dict['shorter_weight'] < 0.5:
            expiry_to_use = expiry_dict['longer_expiry']

        expiry_to_use = f'{expiry_to_use[6:10]}-{expiry_to_use[3:5]}-{expiry_to_use[0:2]}'
        return_dict["expiry_to_use"] = expiry_to_use
        o = y.option_chain(expiry_to_use)
        df = o.calls.fillna(0)
        df = df.sort_values(by='openInterest',ascending=False)
        df = df.reset_index(drop=True)
        return_dict["gamma_1"] = float(df.openInterest[0]*100)
        return_dict["strike_1"] = float(df.strike[0])
        return_dict["gamma_2"] = float(df.openInterest[1]*100)
        return_dict["strike_2"] = float(df.strike[1])
        return_dict['stock_price'] = price
        r.hset(f'{symbol}|gamma|{n_days}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|gamma|{n_days}','value',str(return_dict))
        return return_dict
    except:
        return {"symbol": "Error", "error": "No Data found for %s"%symbol}



def stock_volume (symbol:str, n_days:int):
    symbol = symbol.upper()
    if is_cache_good(f'{symbol}|volume|{n_days}'):
        return ast.literal_eval(r.hget(f'{symbol}|volume|{n_days}','value'))
    curr_date = str(datetime.now().date())
    details_dict = get_current_stock_details(symbol)
    d1 = datetime.now()
    is_trading = r.hget(curr_date,"trading")
    weight = 1
    price = details_dict["close"]
    if is_trading == "yes":
        d2 = d1.replace(hour=9)
        d2 = d2.replace(minute=30)
        if d1 > d2:
            delta = d1 - d2
            if delta.total_seconds() >= 390*60:
                weight = 1
            else:
                weight = (390*60)/delta.total_seconds()
                price = details_dict["mid"]
    today_volume = details_dict['curr_volume']*weight
    print(weight)
    print(today_volume)
    s = yf.Ticker(symbol)
    p = stats.percentileofscore(s.history()[-n_days:].Volume,today_volume)
    return_dict =  {'symbol':symbol, 'percentile':p, 'volume':today_volume, 'avg_10d_volume':details_dict['avg_10d_volume'],'stock_price':price}
    r.hset(f'{symbol}|volume|{n_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|volume|{n_days}','value',str(return_dict))
    return return_dict

def stock_returns(symbol:str, n_days:int):
    symbol = symbol.upper()
    if is_cache_good(f'{symbol}|price|{n_days}', CACHE_TIMEOUT*3):
        return ast.literal_eval(r.hget(f'{symbol}|price|{n_days}','value'))
    x = yf.Ticker(symbol)
    df = x.history(period='1y', interval='1d')
    df = df.dropna()
    df['ndays']=df['Close'].shift(n_days)
    df = df.dropna()
    df['returns']= (df.Close-df.ndays)/df.ndays
    today_return = df.returns[-1]
    p = stats.percentileofscore(df.returns,today_return)
    return_dict =  {'symbol':symbol, 'percentile':p}
    r.hset(f'{symbol}|price|{n_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|price|{n_days}','value',str(return_dict))
    return return_dict

def update_stock_likes(symbol,vote_val):
    symbol = symbol.upper()
    if r.exists(f"{symbol}|votes"):
        if vote_val>0:
            up = 0
            if r.hget(f"{symbol}|votes","up"):
                up = int(r.hget(f"{symbol}|votes","up"))
            r.hset(f"{symbol}|votes","up", up + vote_val)
        else:
            down = 0
            if r.hget(f"{symbol}|votes","down"):
                down = int(r.hget(f"{symbol}|votes","down"))
            r.hset(f"{symbol}|votes","down", down + vote_val)
    else:
        if vote_val>0:
            r.hset(f"{symbol}|votes","up", vote_val)
        else:
            r.hset(f"{symbol}|votes","down", vote_val)

def get_stock_likes(symbol):

    symbol = symbol.upper()
    return_dict =  {"up":0, "down":0}  
    if r.exists(f"{symbol}|votes"):
        return_dict = {"up":r.hget(f"{symbol}|votes","up"), "down":r.hget(f"{symbol}|votes","down")}  
    return return_dict
        
    
    
def is_cache_good(cache_key, cache_timeout = CACHE_TIMEOUT ):
    cache_timeout = CACHE_TIMEOUT + randint(1,400)
    d1 = datetime.now()
    curr_date = str(date.today())
    open_time = d1.replace(hour=9)
    open_time = open_time.replace(minute=30)
    close_time = d1.replace(hour=16)
    close_time = close_time.replace(minute=00)
    now_in_sec = int(datetime.utcnow().strftime('%s'))
    print(f'************{cache_key}*****')
    if r.hget(cache_key,'time'):
        if r.hget(curr_date,"trading_date") == "yes" :
            if d1 >= open_time and d1 <= close_time:
                if (now_in_sec - int(r.hget(cache_key,'time'))) < cache_timeout:
                    return True
            elif d1 > close_time and int(r.hget(cache_key,'time')) > int(close_time.strftime('%s')):
                return True
            elif d1 < open_time and (now_in_sec - int(r.hget(cache_key,'time'))) < 3600*4: #4 hours
                return True

        elif r.hget(curr_date,"trading_date") == "no":
            if (now_in_sec - int(r.hget(cache_key,'time'))) < 3600*10: #update every 10 hours on holidays
                return True
        else:
            check_is_trading()
    return False

def check_is_trading():
    curr_date = str(date.today())
    if curr_date in TRADING_DAYS:
        r.hset(curr_date,"trading_date","yes")
    else:
        r.hset(curr_date,"trading_date","no")

def get_current_stock_details(symbol:str):
    symbol = symbol.upper()
    return_dict = {}
    if is_cache_good(symbol,FASTER_TIMEOUT):
        return ast.literal_eval(r.hget(symbol,'value'))
    y = yf.Ticker(symbol)
    info = y.info
    return_dict["close"] = y.history().Close[-1]
    return_dict["mid"] = (info['bid']+info['ask'])/2
    return_dict["avg_10d_volume"] = info['averageVolume10days']
    return_dict["curr_volume"] = info['volume']
    return_dict["last_div"] = info['lastDividendValue']
    return_dict["last_ex_div"] = info['exDividendDate']
    return_dict["div_rate"] = info['dividendRate']
    return_dict["div_yld"] = info['dividendYield']
    r.hset(symbol,'time',datetime.utcnow().strftime('%s'))
    r.hset(symbol,'value',str(return_dict))
    return return_dict

def brad_calls():
    BRAD_LIST = ["ABBV","GILD","GME","IBM", "MO", "T", "XOM"]
    return_dict = {}
    for i in BRAD_LIST:
        return_dict[i] = [ast.literal_eval(r.hget(f"{i}|calltrade|7","value"))['best_call']]
        return_dict[i].append(ast.literal_eval(r.hget(f"{i}|calltrade|14","value"))['best_call'])
        return_dict[i].append(ast.literal_eval(r.hget(f"{i}|calltrade|28","value"))['best_call'])
    return return_dict
