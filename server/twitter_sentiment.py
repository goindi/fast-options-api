import requests
import pandas as pd
import flair
import re

whitespace = re.compile(r"\s+")
web_address = re.compile(r"(?i)http(s):\/\/[a-z0-9.~_\-\/]+")
user = re.compile(r"(?i)@[a-z0-9_]+")

api_url = 'https://api.twitter.com/1.1/search/tweets.json'
bearer_token = 'AAAAAAAAAAAAAAAAAAAAACOFNQEAAAAA%2Fo7YJMJtqrtW2HQNu%2B%2F7vAsXYVg%3DuGHJTPDmhhbaPTysO8jRW9SNETvZ9h2RKFCN3Y3It65v7onDEd'
api_key = 'nh5zRop2FJaK1QHfVOPvMzNhS'
api_secret_key = 'Bg2i5z2T7Dgb8RxpJ0hsOoJd4TM00Uw0lVasG1wqg9tZTuXRWc'

def get_data(tweet):
    data = {
        'id': tweet['id_str'],
        'created_at': tweet['created_at'],
        'text': tweet['full_text']
    }
    return data

def clean(tweet):
    #sym = re.compile(rf"(?i)@{symbol}(?=\b)")
    #tweet = sym.sub(symbol, tweet)
    tweet = whitespace.sub(' ', tweet)
    tweet = web_address.sub('', tweet)
    tweet = user.sub('', tweet)
    return tweet

def find_twitter_sentiment(symbol:str, num_of_tweets:int = 10):
    symbol = symbol.upper()

    params = {
    'q': symbol,
    'tweet_mode': 'extended',
    'lang': 'en',
    'count': num_of_tweets
    }
    response = requests.get(
        api_url,
        params=params,
        headers={'authorization': 'Bearer '+bearer_token})

    df = pd.DataFrame()
    for tweet in response.json()['statuses']:
        row = get_data(tweet)
        df = df.append(row, ignore_index=True)

    df['text']=df['text'].apply(clean)
    sym = re.compile(rf"(?i)@{symbol}(?=\b)")
    sentiment_model = flair.models.TextClassifier.load('en-sentiment')
    probs = []
    sentiments = []
    for tweet in df['text'].to_list():
        tweet = sym.sub(symbol, tweet)
        # make prediction
        sentence = flair.data.Sentence(tweet)
        sentiment_model.predict(sentence)
        # extract sentiment prediction
        probs.append(sentence.labels[0].score)  # numerical score 0-1
        if sentence.labels[0].value == "POSITIVE":
            sentiments.append(1)
        else:
            sentiments.append(-1)

    df['probability'] = probs
    df['sentiment'] = sentiments
    print(df)

    sentiment_index = sum(df['probability']*df['sentiment'])*100/df.shape[0]
    return {"symbol":symbol, "twitter_index":sentiment_index}
