import time
import logging
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_client = None
    _redis_available = True
except Exception:
    _redis_client = None
    _redis_available = False


def _get_redis_client():
    global _redis_client
    if not _redis_available:
        return None
    try:
        url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        _redis_client.ping()
    except Exception:
        _redis_client = None
        return None
    return _redis_client


def rate_limit(max_requests, window_seconds, key_func=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            client = _get_redis_client()
            if client is None:
                # En production, le rate-limit est indispensable : on refuse
                # la requête plutôt que de la laisser passer silencieusement.
                # En test/d, on log et on laisse passer.
                logger.warning(
                    'Rate limiting skipped for %s: Redis unavailable',
                    getattr(fn, '__name__', fn.__class__.__name__),
                )
                if current_app.config.get('TESTING') or current_app.config.get('DEBUG'):
                    return fn(*args, **kwargs)
                return jsonify({
                    'message': 'Service temporairement indisponible (rate-limit).'
                }), 503

            try:
                if key_func:
                    key = key_func()
                else:
                    ip = request.remote_addr or 'unknown'
                    key = f"rate_limit:{fn.__name__}:{ip}"

                now = time.time()
                pipe = client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, count, _ = pipe.execute()

                if count > max_requests:
                    logger.warning(
                        "Rate limit exceeded for %s: %s requests in %ss window",
                        key, count, window_seconds
                    )
                    return jsonify({'message': 'Trop de requêtes. Veuillez réessayer plus tard.'}), 429
            except Exception:
                logger.exception('Rate limiting error for %s', getattr(fn, '__name__', fn.__class__.__name__))
                # Fail-closed: refuse la requête plutôt que de laisser passer
                # un flot non rate-limite en cas d'erreur Redis (sauf en test).
                if current_app.config.get('TESTING'):
                    return fn(*args, **kwargs)
                return jsonify({
                    'message': 'Service temporairement indisponible (rate-limit).'
                }), 503

            return fn(*args, **kwargs)
        return wrapper
    return decorator
