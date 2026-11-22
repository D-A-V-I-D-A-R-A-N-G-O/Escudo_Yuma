"""
Extractor de características de riesgo para Escudo Yuma.
Transforma los atributos crudos de la transacción y los datos del Feature Store
en un vector normalizado de variables de alto impacto predictivo.
"""

from typing import Dict, Any
from datetime import datetime
from app.schemas.decision import TransactionRequest
from app.features.store import feature_store


def extract_features(request: TransactionRequest) -> Dict[str, float]:
    """
    Construye el vector de características numéricas en tiempo real.
    Latencia objetivo: < 15 ms.
    """
    current_ts = request.timestamp.timestamp()
    dest = request.destination_account or request.destination_user_id

    # 1. Recuperar variables precalculadas y de ventana desde el Feature Store
    raw_store = feature_store.fetch_real_time_features(
        user_id=request.user_id,
        device_id=request.device_id,
        dest_account=dest,
        current_ts=current_ts
    )

    # 2. Atributos temporales
    hour = request.timestamp.hour
    is_nighttime = 1.0 if (hour >= 23 or hour <= 5) else 0.0
    is_weekend = 1.0 if request.timestamp.weekday() in (5, 6) else 0.0

    # 3. Métricas de desviación de comportamiento (Z-Score y Ratios)
    user_avg = max(10000.0, raw_store.get("user_avg_amount_30d", 120000.0))
    user_max = max(user_avg, raw_store.get("user_max_amount_30d", 500000.0))

    ratio_vs_avg = round(request.amount / user_avg, 3)
    ratio_vs_max = round(request.amount / user_max, 3)

    # 4. Señales de seguridad de cuenta
    sim_hours = raw_store.get("hours_since_last_sim_change", 9999.0)
    sim_swap_critical_48h = 1.0 if (sim_hours <= 48.0 or getattr(request, "sim_swap_within_48h", False)) else 0.0

    pwd_hours = raw_store.get("hours_since_last_pwd_change", 9999.0)
    pwd_reset_critical_24h = 1.0 if (pwd_hours <= 24.0 or getattr(request, "pwd_reset_within_24h", False)) else 0.0

    # 5. Señales de dispositivo y granja de fraude
    device_is_new = raw_store.get("device_is_new", 0.0)
    device_users = raw_store.get("device_distinct_users_7d", 1.0)
    if getattr(request, "is_shared_device", False):
        device_users = max(5.0, device_users)
    is_mule_device = 1.0 if device_users >= 4.0 else 0.0

    # 6. Señales de grafo de red de mulas
    mule_in_degree = raw_store.get("dest_mule_in_degree_24h", 0.0)
    if getattr(request, "is_mule_destination", False):
        mule_in_degree = max(7.0, mule_in_degree)
    is_mule_destination = 1.0 if (mule_in_degree >= 5.0 or getattr(request, "is_mule_destination", False)) else 0.0

    # 7. Canal de operación codificado
    channel_risk_map = {
        "APP_MOVIL": 0.15,
        "QR_ESTATICO": 0.45,  # Alto riesgo por sustitución física de stickers QR
        "QR_DINAMICO": 0.10,
        "PSE": 0.20,
        "TRANSFERENCIA_INTERBANCARIA": 0.35
    }
    channel_risk = channel_risk_map.get(request.channel.value, 0.20)

    # 8. Señales de IP y Geolocalización (Ubicación anómala y VPN)
    city = getattr(request, "location_city", "Bogotá") or "Bogotá"
    ip = request.ip_address or ""
    is_foreign_location = 1.0 if any(loc in city.lower() for loc in ["miami", "moscú", "moscow", "lagos", "exterior", "internacional"]) else 0.0
    is_different_city = 1.0 if ("bogot" not in city.lower()) else 0.0
    is_geo_anomaly = 1.0 if (is_foreign_location == 1.0 or is_different_city == 1.0) else 0.0

    # Rango de IP catalogada como Proxy, Hosting, VPN o Tor Exit Node (ej. 45.x, 194.x, 185.x)
    is_suspicious_ip = 1.0 if (ip.startswith("45.") or ip.startswith("194.") or ip.startswith("185.") or "vpn" in ip.lower()) else 0.0

    # Vector consolidado ordenado de características
    features = {
        "amount": float(request.amount),
        "ratio_vs_avg_amount": float(ratio_vs_avg),
        "ratio_vs_max_amount": float(ratio_vs_max),
        "tx_count_5m": float(raw_store.get("tx_count_5m", 0.0)),
        "tx_count_1h": float(raw_store.get("tx_count_1h", 0.0)),
        "tx_count_24h": float(raw_store.get("tx_count_24h", 0.0)),
        "is_nighttime": float(is_nighttime),
        "is_weekend": float(is_weekend),
        "device_is_new": float(device_is_new),
        "device_distinct_users_7d": float(device_users),
        "is_mule_device": float(is_mule_device),
        "sim_swap_critical_48h": float(sim_swap_critical_48h),
        "pwd_reset_critical_24h": float(pwd_reset_critical_24h),
        "account_age_days": float(raw_store.get("account_age_days", 180.0)),
        "mule_in_degree_24h": float(mule_in_degree),
        "is_mule_destination": float(is_mule_destination),
        "channel_risk": float(channel_risk),
        "is_geo_anomaly": float(is_geo_anomaly),
        "is_suspicious_ip": float(is_suspicious_ip),
    }

    return features
