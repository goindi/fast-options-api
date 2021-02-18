from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
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
    return {"bullish_stock_symbol":max_up_symbol, "bullish_kelly":up_kelly["kelly"], "bullish_stock_details":yolo_dict[max_up_symbol], "bearish_stock_symbol":max_down_symbol,"bearish_kelly":down_kelly["kelly"], "bearish_stock":yolo_dict[max_down_symbol]}
    #return yolo_dict

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
