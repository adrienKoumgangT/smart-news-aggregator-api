from time import time

from prometheus_client import Counter, Histogram

# Prometheus metrics
REDIS_REQUESTS = Counter('redis_operations_total', 'Total Redis operations')
REDIS_LATENCY = Histogram('redis_operation_latency_seconds', 'Redis operation latency')

def monitor_redis_operations():
    def decorator(f):
        def wrapper(*args, **kwargs):
            start_time = time()
            REDIS_REQUESTS.inc()
            result = f(*args, **kwargs)
            latency = time() - start_time
            REDIS_LATENCY.observe(latency)
            return result
        return wrapper
    return decorator

