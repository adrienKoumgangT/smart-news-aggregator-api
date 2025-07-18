from prometheus_client import Summary

MONGO_QUERY_TIME = Summary('mongo_query_duration_seconds', 'Time spent processing MongoDB queries')
