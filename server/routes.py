from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from server.calc_module import get_range_data_from_symbol, get_best_call_trades, get_best_put_trades
from server.calc_module import get_probability_move, get_normalized_probability_move, get_forward, get_amt_invest

router = APIRouter()

@router.get("/")
async def get_notes() -> dict:
    return get_range_data_from_symbol('SPY',7)

@router.get("/range/{symbol}")
async def get_range_data(symbol: str, days:int = 7) -> dict:
    return get_range_data_from_symbol(symbol,days)

@router.get("/yolo/{my_list}")
async def get_my_yolo(my_list: str, days:int = 7, sigma:float = 0.5) -> dict:
    symbol_list = my_list.split(",")
    return_dict = get_best_trade(symbol_list,days,sigma)
    return return_dict
    #return yolo_dict

def get_best_trade(symbol_list: list, days:int, sigma:float ) -> dict:
    yolo_dict = {}
    max_up_prob = 0
    max_up_symbol = ""
    max_down_prob = 0
    max_down_symbol = ""
    up_expiry = ""
    down_expiry = ""

    for i in symbol_list:
        print(i)
        yolo_dict[i] = get_normalized_probability_move(i, days, sigma)
        if yolo_dict[i]["norm_prob_up"] > max_up_prob:
            max_up_prob = yolo_dict[i]["norm_prob_up"]
            max_up_symbol = i
            up_expiry = yolo_dict[i]["expiry"]
        if yolo_dict[i]["norm_prob_down"] > max_down_prob:
            max_down_prob = yolo_dict[i]["norm_prob_down"]
            max_down_symbol = i
            down_expiry = yolo_dict[i]["expiry"]
    up_kelly = get_amt_invest(max_up_symbol,days)
    down_kelly = get_amt_invest(max_down_symbol,days)
    return {"bullish_stock_symbol":max_up_symbol, "bullish_kelly":up_kelly["kelly"], "bearish_stock_symbol":max_down_symbol,"bearish_kelly":down_kelly["kelly"],"bullish_stock_details":yolo_dict[max_up_symbol], "bearish_stock":yolo_dict[max_down_symbol]}

@router.get("/tradeoftheday/{my_list}")
async def get_my_trade_of_day(my_list: str, days:int = 7, sigma:float = 0.5) -> str:
    symbol_list = my_list.split(",")
    yolo_trade_dict = get_best_trade(symbol_list,days,sigma)
    call_trade =  get_best_call_trades(yolo_trade_dict['bullish_stock_symbol'], days)
    call_trade = call_trade['best_call']
    bullet_1 = ""
    symbol = yolo_trade_dict["bullish_stock_symbol"]
    if yolo_trade_dict["bullish_kelly"] > 0:
        kelly_to_use = min(yolo_trade_dict["bullish_kelly"],0.1)*100
        bullet_1 = f'Planning $100 YOLO? Buy ${kelly_to_use:.2f} of {symbol}'
    expiry = call_trade['expiry']
    exp = datetime.strptime(expiry,'%d-%m-%Y').strftime('%b %d')
    #bullets_of_day = bullets_of_day + "&#13;&#10;"
    bullet_2=f"Have 100+ Shares of {symbol}? Sell {exp}, Covered Call @ ${call_trade['strike']} for {symbol}"
    return f'{bullet_1}           {bullet_2}'

@router.get("/call_trades/{symbol}")
async def get_my_call_trades(symbol: str, days:int = 7) -> dict:
    return get_best_call_trades(symbol, days)

@router.get("/put_trades/{symbol}")
async def get_my_put_trades(symbol: str, days:int = 7) -> dict:
    return get_best_put_trades(symbol, days)

@router.get("/prob/{symbol}")
async def get_my_probabilities(symbol: str, days:int = 7, percent:float = 5) -> dict:
    return get_probability_move(symbol, days, percent)

@router.get("/normalized_prob/{symbol}")
async def get_my_normalized_probability_move(symbol: str, days:int = 7, sigma:float = 0.5) -> dict:
    return get_normalized_probability_move(symbol, days, sigma)

@router.get("/forward/{symbol}")
async def get_option_implied_forward(symbol: str, days:int = 7) -> dict:
    return get_forward(symbol, days)

@router.get("/kelly/{symbol}")
async def get_amt_to_invest(symbol: str, days:int = 7) -> dict:
    return get_amt_invest(symbol, days)
