"""
Feature Store en tiempo real para Escudo Yuma.
Implementación híbrida de alta velocidad basada en Redis con fallback en memoria.
Soporta ventanas deslizantes, conteos de velocidad, conjuntos de dispositivos y grafos de cuentas mula.
"""

import time
import logging
from typing import Dict, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class InMemoryFeatureStore:
    """Implementación de respaldo en memoria ultrarrápida (útil para pruebas unitarias y fallback)."""
    def __init__(self):
        # user_id -> lista de timestamps [(ts, amount, dest_id)]
        self.user_transactions = defaultdict(list)
        # user_id -> profile dict
        self.user_profiles = {}
        # device_id -> set of user_ids
        self.device_users = defaultdict(set)
        # user_id -> set of known device_ids
        self.user_devices = defaultdict(set)
        # dest_account -> list of (ts, sender_user_id)
        self.dest_incoming = defaultdict(list)
        # user_id -> last_sim_change_ts
        self.user_sim_change = {}
        # user_id -> last_pwd_change_ts
        self.user_pwd_change = {}

    def get_user_features(self, user_id: str, current_ts: float) -> Dict[str, Any]:
        txs = self.user_transactions.get(user_id, [])
        # Filtrar ventanas
        w5m = current_ts - 300
        w1h = current_ts - 3600
        w24h = current_ts - 86400

        tx_5m = [t for t in txs if t[0] >= w5m]
        tx_1h = [t for t in txs if t[0] >= w1h]
        tx_24h = [t for t in txs if t[0] >= w24h]

        unique_dests_24h = len(set(t[2] for t in tx_24h if t[2]))
        amount_sum_24h = sum(t[1] for t in tx_24h)

        profile = self.user_profiles.get(user_id, {
            "avg_amount_30d": 120000.0,
            "max_amount_30d": 500000.0,
            "account_age_days": 180.0
        })

        sim_ts = self.user_sim_change.get(user_id, None)
        pwd_ts = self.user_pwd_change.get(user_id, None)

        sim_hours = (current_ts - sim_ts) / 3600.0 if sim_ts else 9999.0
        pwd_hours = (current_ts - pwd_ts) / 3600.0 if pwd_ts else 9999.0

        return {
            "tx_count_5m": len(tx_5m),
            "tx_count_1h": len(tx_1h),
            "tx_count_24h": len(tx_24h),
            "tx_amount_sum_24h": amount_sum_24h,
            "unique_destinations_24h": unique_dests_24h,
            "user_avg_amount_30d": profile.get("avg_amount_30d", 120000.0),
            "user_max_amount_30d": profile.get("max_amount_30d", 500000.0),
            "account_age_days": profile.get("account_age_days", 180.0),
            "hours_since_last_sim_change": sim_hours,
            "hours_since_last_pwd_change": pwd_hours,
        }

    def get_device_features(self, device_id: str, user_id: str) -> Dict[str, Any]:
        known_devices = self.user_devices.get(user_id, set())
        device_is_new = 1.0 if (len(known_devices) > 0 and device_id not in known_devices) else 0.0

        distinct_users = len(self.device_users.get(device_id, set()))
        return {
            "device_is_new": device_is_new,
            "device_distinct_users_7d": max(1.0, float(distinct_users))
        }

    def get_destination_mule_features(self, dest_account: Optional[str], current_ts: float) -> Dict[str, Any]:
        if not dest_account:
            return {"dest_mule_in_degree_24h": 0.0}

        incoming = self.dest_incoming.get(dest_account, [])
        w24h = current_ts - 86400
        recent = [i for i in incoming if i[0] >= w24h]
        unique_senders = len(set(i[1] for i in recent))
        return {
            "dest_mule_in_degree_24h": float(unique_senders)
        }

    def record_transaction(self, user_id: str, amount: float, dest_account: Optional[str], device_id: str, current_ts: float):
        self.user_transactions[user_id].append((current_ts, amount, dest_account))
        self.device_users[device_id].add(user_id)
        self.user_devices[user_id].add(device_id)
        if dest_account:
            self.dest_incoming[dest_account].append((current_ts, user_id))


class RealTimeFeatureStore:
    """Cliente unificado de Feature Store que utiliza Redis con fallback en memoria."""
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.in_memory = InMemoryFeatureStore()

        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, socket_connect_timeout=0.05, socket_timeout=0.05)
                self.redis_client.ping()
                logger.info("Conexión exitosa a Redis Feature Store")
            except Exception as e:
                logger.warning(f"No se pudo conectar a Redis ({e}). Usando InMemoryFeatureStore.")
                self.redis_client = None

    def fetch_real_time_features(self, user_id: str, device_id: str, dest_account: Optional[str], current_ts: float) -> Dict[str, Any]:
        """Recupera el vector completo de variables en < 10 ms."""
        # Si Redis está disponible, se recupera mediante pipeline
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline(transaction=False)
                # Ventanas y contadores en Redis ZSET (sorted sets con timestamp como score)
                pipe.zcount(f"yuma:u:{user_id}:txs", current_ts - 300, current_ts)
                pipe.zcount(f"yuma:u:{user_id}:txs", current_ts - 3600, current_ts)
                pipe.zcount(f"yuma:u:{user_id}:txs", current_ts - 86400, current_ts)
                pipe.hgetall(f"yuma:u:{user_id}:profile")
                pipe.sismember(f"yuma:u:{user_id}:devices", device_id)
                pipe.scard(f"yuma:d:{device_id}:users")
                if dest_account:
                    pipe.scard(f"yuma:dest:{dest_account}:senders_24h")
                results = pipe.execute()

                profile = results[3] or {}
                device_known = results[4]
                device_users_count = results[5] or 1
                dest_in_degree = results[6] if dest_account and len(results) > 6 else 0

                return {
                    "tx_count_5m": float(results[0] or 0),
                    "tx_count_1h": float(results[1] or 0),
                    "tx_count_24h": float(results[2] or 0),
                    "tx_amount_sum_24h": float(profile.get(b"amount_sum_24h", 0.0)),
                    "unique_destinations_24h": float(profile.get(b"unique_dests_24h", 0.0)),
                    "user_avg_amount_30d": float(profile.get(b"avg_amount_30d", 120000.0)),
                    "user_max_amount_30d": float(profile.get(b"max_amount_30d", 500000.0)),
                    "account_age_days": float(profile.get(b"account_age_days", 180.0)),
                    "hours_since_last_sim_change": float(profile.get(b"hours_sim_change", 9999.0)),
                    "hours_since_last_pwd_change": float(profile.get(b"hours_pwd_change", 9999.0)),
                    "device_is_new": 0.0 if device_known else 1.0,
                    "device_distinct_users_7d": float(device_users_count),
                    "dest_mule_in_degree_24h": float(dest_in_degree),
                }
            except Exception as err:
                logger.debug(f"Falla momentánea en Redis ({err}), usando InMemoryFeatureStore")

        # Fallback ultra rápido en memoria
        user_feat = self.in_memory.get_user_features(user_id, current_ts)
        dev_feat = self.in_memory.get_device_features(device_id, user_id)
        mule_feat = self.in_memory.get_destination_mule_features(dest_account, current_ts)

        features = {}
        features.update(user_feat)
        features.update(dev_feat)
        features.update(mule_feat)
        return features

    def commit_transaction_event(self, user_id: str, amount: float, dest_account: Optional[str], device_id: str, current_ts: float):
        """Actualiza el estado del feature store post-decisión de manera asíncrona."""
        if self.redis_client:
            try:
                pipe = self.redis_client.pipeline(transaction=False)
                member_val = f"{current_ts}:{amount}:{dest_account or ''}"
                pipe.zadd(f"yuma:u:{user_id}:txs", {member_val: current_ts})
                pipe.sadd(f"yuma:u:{user_id}:devices", device_id)
                pipe.sadd(f"yuma:d:{device_id}:users", user_id)
                if dest_account:
                    pipe.sadd(f"yuma:dest:{dest_account}:senders_24h", user_id)
                    pipe.expire(f"yuma:dest:{dest_account}:senders_24h", 86400)
                pipe.expire(f"yuma:u:{user_id}:txs", 86400)
                pipe.execute()
            except Exception:
                pass

        # Siempre mantener sincronizado también el fallback en memoria
        self.in_memory.record_transaction(user_id, amount, dest_account, device_id, current_ts)


# Instancia singleton del Feature Store
feature_store = RealTimeFeatureStore()
