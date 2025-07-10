import os

env_var = {
    "prod": False,

    "debug": True,

    "mongodb.uri": "mongodb://localhost:27017/",
    "mongodb.database": "smart-news-aggregator",
    "mongodb.collection.user": "users",
    "mongodb.collection.article": "articles",
    "mongodb.collection.interaction": "user-article-interactions",
    "mongodb.collection.comment": "comments",
    "mongodb.collection.log_request": "log-requests",
    "mongodb.collection.server_error_log": "server-error-log",
    "mongodb.collection.auth_event_log": "auth-event-log",

    "redis.uri": "redis://localhost:6379",

    "externapi.mediastack.enable": True,
    "externapi.mediastack.access_key": "",
    "externapi.mediastack.max_request": 10,

    "externapi.currentsapi.enable": True,
    "externapi.currentsapi.api_key": "",
    "externapi.currentsapi.max_request": 10,

    "externapi.gnews.enable": False,
    "externapi.gnews.api_key": "",
    "externapi.gnews.max_request": 10,

    "externapi.marketaux.enable": True,
    "externapi.marketaux.api_key": "",
    "externapi.marketaux.max_request": 10,

    "externapi.nytimes.enable": True,
    "externapi.nytimes.api_key": "",
    "externapi.nytimes.max_request": 10,

    "externapi.newsapi.enable": True,
    "externapi.newsapi.api_key": "",
    "externapi.newsapi.max_request": 100,

    "externapi.newsdata.enable": True,
    "externapi.newsdata.api_key": "",
    "externapi.newsdata.max_request": 100,

    "externapi.spaceflightnewsapi.enable": True,
    "externapi.spaceflightnewsapi.api_key": "",
    "externapi.spaceflightnewsapi.max_request": 100,

    "externapi.theguardian.enable": True,
    "externapi.theguardian.api_key": "",
    "externapi.theguardian.max_request": 100,

}

# eu-central-1


def is_prod() -> bool:
    try:
        return bool(os.environ.get("prod", env_var["prod"]))
    except KeyError as e:
        print(e)
        return False
    except Exception as e:
        print(e)
        raise e


def is_debug() -> bool:
    try:
        return bool(os.environ.get("debug", env_var["debug"]))
    except KeyError as e:
        print(e)
        return True
    except Exception as e:
        print(e)
        raise e


def get_configuration(key):
    key_conf = key
    if is_prod():
        key_conf += ".prod"
    try:
        return os.environ.get(key_conf, env_var[key_conf])
    except KeyError as e:
        print(e)
        try:
            if is_prod():
                return os.environ.get(key, env_var[key])
            return None
        except KeyError as e2:
            print(e2)
            return None

