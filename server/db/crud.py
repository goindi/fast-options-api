from sqlalchemy.orm import Session
from server.db.database import engine, SessionLocal
from server.db.models import User, Rating
from sqlalchemy.sql import func
from wallstreet import Stock
from server.calc_module import is_cache_good
from datetime import datetime
import redis
import ast

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def post_submit_user_rating(my_dict):
    print(my_dict)
    return update_ratings(my_dict['symbol'],my_dict['user_email'],my_dict['ratings'])


def update_ratings(my_symbol,user,user_ratings):
    my_symbol = my_symbol.upper()
    session = SessionLocal()
    u = session.query(User).filter(User.email==user)
    curr_px = 0
    if u.count() == 0:
        u = create_user(user)
    else:
        u = u.first()
    try:
        t = Stock(my_symbol)
        curr_px = t.price
    except:
        curr_px = 0
    qry_set = session.query(Rating).filter(Rating.user_email==user).filter(Rating.symbol==my_symbol).order_by(Rating.time_created.desc()).first()
    if not qry_set:
        qry_set = create_ratings(my_symbol,u.email,user_ratings, curr_px)
    else:
        change = user_ratings - qry_set.ratings
        qry_set = create_ratings(my_symbol,u.email,user_ratings,curr_px, change)
    session.close()
    return {"result":"success"}


def get_ratings(symbol):
    symbol = symbol.upper()
    session = SessionLocal()
    s = session.execute(f"select avg(ratings) from ratings where symbol='{symbol}'")
    c = s.fetchone()
    session.close()
    if c[0]:
        return {'rating':float(c[0])}
    else:
        return {'rating':0}

def get_symbol_ratings_of_user(my_symbol,user_email):
    my_symbol = my_symbol.upper()
    session = SessionLocal()
    #r = session.query(func.avg(Rating.ratings).label('average')).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).scalar()
    qry_set = session.query(Rating).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).order_by(Rating.time_created.desc()).first()
    session.close()
    if qry_set:
        return {'rating':qry_set.ratings,"change":qry_set.ratings_change,"saved_value":qry_set.curr_value}
    else:
        return {'rating':0,"change":"NA", "saved_value":0}

def get_avatar(user_email):
    session = SessionLocal()
    #r = session.query(func.avg(Rating.ratings).label('average')).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).scalar()
    user = session.query(User).filter(User.email==user_email).first()
    session.close()
    if user:
        return {'avatar':user.avatar}
    else:
        return {'avatar':"{'skinColor';'Tanned','hairColor':'Brown','facialHairType':'Blank','topType':'ShortHairShortFlat'}"}

def update_avatar(user_email,avatar_dict):
    session = SessionLocal()
    #r = session.query(func.avg(Rating.ratings).label('average')).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).scalar()
    user = session.query(User).filter(User.email==user_email).first()
    if not user:
        user = create_user(user_email)
    user.avatar = avatar_dict
    session.commit()
    session.close()
    return {'avatar':"successfully updated"}

def get_all_ratings_of_user(user_email):
    session = SessionLocal()
    qry_set = session.query(Rating).filter(Rating.user_email==user_email).order_by(Rating.symbol,Rating.time_created.desc()).distinct(Rating.symbol)
    if qry_set:
        my_arr = []
        for i in qry_set:
            curr_px=0
            if is_cache_good(f'{i.symbol}|crud'):
                curr_px = ast.literal_eval(r.hget(f'{i.symbol}|crud','value'))
            else:
                try:
                    t = Stock(i.symbol)
                    curr_px = t.price
                    r.hset(f'{i.symbol}|crud','time',datetime.utcnow().strftime('%s'))
                    r.hset(f'{i.symbol}|crud','value',curr_px)
                except:
                    pass
            my_arr.append({'symbol':i.symbol,'rating':[i.ratings],'timestamp':i.time_created,'px_at_save':i.curr_value,'px_now':curr_px})
        session.close()
        return {"user_list":my_arr}
    else:
        session.close()
        return {"error":"no entry"}

def get_all_friend_ratings_of_stock(symbol,user_email):
    session = SessionLocal()
    symbol = symbol.upper()
    qry_set = session.query(Rating).filter(Rating.symbol==symbol).order_by(Rating.user_email,Rating.time_created.desc()).distinct(Rating.user_email)
    if qry_set:
        my_arr = []
        for i in qry_set:
            curr_px=0
            if is_cache_good(f'{i.symbol}|crud'):
                curr_px = ast.literal_eval(r.hget(f'{i.symbol}|crud','value'))
            else:
                try:
                    t = Stock(i.symbol)
                    curr_px = t.price
                    r.hset(f'{i.symbol}|crud','time',datetime.utcnow().strftime('%s'))
                    r.hset(f'{i.symbol}|crud','value',curr_px)
                except:
                    pass
            my_arr.append({'symbol':i.symbol,'rating':[i.ratings],'timestamp':i.time_created,'px_at_save':i.curr_value,'px_now':curr_px, "friend":i.user_email, 'avatar':i.owner.avatar})
        session.close()
        return {"user_list":my_arr}
    else:
        session.close()
        return {"error":"no entry"}

def create_user(user_email,pwd="whateves"):
    if not user_email:
        user_email='anon@anon.com'
    default_avatar = "{'skinColor':'Tanned','hairColor':'Brown','facialHairType':'Blank','topType':'ShortHairShortFlat'}"
    u = User(email=user_email, hashed_password=pwd, avatar=default_avatar)
    session = SessionLocal()
    session.add(u)
    session.commit()
    session.refresh(u)
    session.close()
    return u

def create_ratings(my_symbol,email,user_ratings, curr_px, change=0):
    my_symbol = my_symbol.upper()
    qry_set = Rating(user_email=email, symbol=my_symbol, ratings=user_ratings, curr_value = curr_px, ratings_change = change)
    session = SessionLocal()
    session.add(qry_set)
    session.commit()
    session.refresh(qry_set)
    session.close()
    return qry_set
