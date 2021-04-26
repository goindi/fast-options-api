from sqlalchemy.orm import Session
from server.db.database import engine, SessionLocal
from server.db.models import User, Rating
from sqlalchemy.sql import func
from wallstreet import Stock

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    r = session.query(Rating).filter(Rating.user_email==user).filter(Rating.symbol==my_symbol).order_by(Rating.time_created.desc()).first()
    if not r:
        r = create_ratings(my_symbol,u.email,user_ratings, curr_px)
    else:
        change = user_ratings - r.ratings
        r = create_ratings(my_symbol,u.email,user_ratings,curr_px, change)
    session.close()


def get_ratings(symbol):
    symbol = symbol.upper()
    session = SessionLocal()
    s = session.execute(f"select avg(ratings) from ratings where symbol='{symbol}'")
    c = s.fetchone()
    session.close()
    if c[0]:
        return {'Rating':float(c[0])}
    else:
        return {'Rating':0}

def get_symbol_ratings_of_user(my_symbol,user_email):
    my_symbol = my_symbol.upper()
    session = SessionLocal()
    #r = session.query(func.avg(Rating.ratings).label('average')).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).scalar()
    r = session.query(Rating).filter(Rating.user_email==user_email).filter(Rating.symbol==my_symbol).order_by(Rating.time_created.desc()).first()
    session.close()
    if r:
        return {'Rating':r.ratings,"Change":r.ratings_change}
    else:
        return {'Rating':0,"Change":"NA"}

def get_all_ratings_of_user(user_email):
    session = SessionLocal()
    r = session.query(Rating).filter(Rating.user_email==user_email).order_by(Rating.symbol,Rating.time_created.desc()).distinct(Rating.symbol)
    if r:
        my_dict = {}
        for i in r:
            my_dict[i.symbol] = i.ratings
        session.close()
        return my_dict
    else:
        session.close()
        return {"error":"no entry"}

def create_user(user_email,pwd="whateves"):
    u = User(email=user_email, hashed_password=pwd)
    session = SessionLocal()
    session.add(u)
    session.commit()
    session.refresh(u)
    session.close()
    return u

def create_ratings(my_symbol,email,user_ratings, curr_px, change=0):
    my_symbol = my_symbol.upper()
    r = Rating(user_email=email, symbol=my_symbol, ratings=user_ratings, curr_value = curr_px, ratings_change = change)
    session = SessionLocal()
    session.add(r)
    session.commit()
    session.refresh(r)
    session.close()
    return r
