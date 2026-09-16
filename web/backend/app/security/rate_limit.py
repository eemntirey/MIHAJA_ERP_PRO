import os
import threading
import time
import logging
from collections import deque
from functools import wraps
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger(__name__)

try:
    import redis
    _redis_client = None
    _redis_available = True
except Exception:
    _redis_client = None
    _redis_available = False

# Compteur de secours en mémoire (dev uniquement) : utilisé quand Redis est
# indisponible afin que les endpoints protégés (ex: /auth/login) restent
# fonctionnels. En production on échoue fermé (fail-closed) comme avant.
_memory_lock = threading.Lock()
_memory_counters = {}


def _memory_limit(key, max_requests, window_seconds):
    """Fenêtre glissante en mémoire. Retourne True si la requête est permise."""
    now = time.time()
    with _memory_lock:
        bucket = _memory_counters.setdefault(key, deque())
        while bucket and bucket[0] <= now - window_seconds:
            bucket.popleft()
        if len(bucket) >= max_requests:
            return False
        bucket.append(now)
        return True


# Client Redis mis en cache ; en cas d'echec, on evite de re-ping a chaque
# requete (le timeout de connexion penalise chaque appel de ~1-2s).
_redis_down_until = 0.0
_REDIS_RETRY_DELAY = 30.0  # secondes


def _get_redis_client():
    global _redis_client, _redis_down_until
    if not _redis_available:
        return None
    if time.time() < _redis_down_until:
        return None
    try:
        url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        _redis_client.ping()
    except Exception:
        _redis_client = None
        # Redis indisponible : suspend les tentatives pendant un court delai
        # pour ne pas ralentir chaque requete d'un timeout de connexion.
        _redis_down_until = time.time() + _REDIS_RETRY_DELAY
        return None
    return _redis_client


def _is_production():
    """True si l'app tourne en production (fail-closed sur Redis)."""
    return (
        current_app.config.get('FLASK_ENV') == 'production'
        or os.getenv('FLASK_ENV', '').lower() == 'production'
    )


def rate_limit(max_requests, window_seconds, key_func=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            client = _get_redis_client()
            if client is None:
                # En production, le rate-limit est indispensable : on refuse
                # la requête plutôt que de la laisser passer silencieusement.
                # En test, on log et on laisse passer. En développement, on
                # bascule sur un compteur en mémoire pour ne pas bloquer la
                # connexion quand Redis n'est pas lancé.
                logger.warning(
                    'Rate limiting Redis unavailable for %s (fallback: %s)',
                    getattr(fn, '__name__', fn.__class__.__name__),
                    'memory' if not _is_production() else 'rejected',
                )
                if current_app.config.get('TESTING') or current_app.config.get('DEBUG'):
                    return fn(*args, **kwargs)
                if _is_production():
                    # Dict brut (PAS jsonify) : flask-restx sérialise lui-même
                    # la réponse ; un objet Response ici lèverait
                    # "TypeError: Object of type Response is not JSON
                    # serializable" -> HTTP 500 (bug d'origine sur /auth/login).
                    return {
                        'message': 'Service temporairement indisponible (rate-limit).'
                    }, 503
                # Fallback mémoire (dev)
                ip = request.remote_addr or 'unknown'
                key = f"rate_limit:memory:{getattr(fn, '__name__', '')}:{ip}"
                if not _memory_limit(key, max_requests, window_seconds):
                    logger.warning(
                        "Rate limit (mémoire) dépassé pour %s: %s requêtes en %ss",
                        key, max_requests, window_seconds
                    )
                    # Dict brut (voir note flask-restx ci-dessus)
                    return {
                        'message': 'Trop de requêtes. Veuillez réessayer plus tard.'
                    }, 429
                return fn(*args, **kwargs)

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
                    # Dict brut (voir note flask-restx ci-dessus)
                    return {'message': 'Trop de requêtes. Veuillez réessayer plus tard.'}, 429
            except Exception:
                logger.exception('Rate limiting error for %s', getattr(fn, '__name__', fn.__class__.__name__))
                # Fail-closed en production : on refuse la requête plutôt que de
                # laisser passer un flot non rate-limité en cas d'erreur Redis.
                # Sinon (test/dev) : bascule mémoire ou passage direct.
                if current_app.config.get('TESTING') or current_app.config.get('DEBUG'):
                    return fn(*args, **kwargs)
                if _is_production():
                    # Dict brut (voir note flask-restx ci-dessus)
                    return {
                        'message': 'Service temporairement indisponible (rate-limit).'
                    }, 503
                ip = request.remote_addr or 'unknown'
                key = f"rate_limit:memory:{getattr(fn, '__name__', '')}:{ip}"
                if not _memory_limit(key, max_requests, window_seconds):
                    # Dict brut (voir note flask-restx ci-dessus)
                    return {
                        'message': 'Trop de requêtes. Veuillez réessayer plus tard.'
                    }, 429

            return fn(*args, **kwargs)
        return wrapper
    return decorator
