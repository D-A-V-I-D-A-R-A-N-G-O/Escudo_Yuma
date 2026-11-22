"""
Pruebas automatizadas para el API de Decisión Escudo Yuma.
Verifica la latencia SLA (<300 ms), disparo de reglas críticas,
integración del modelo ML, explicabilidad SHAP y esquemas de respuesta.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.features.store import feature_store

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"
    assert "version" in data
    assert data["sla_max_ms"] == 300.0


def test_legitimate_transaction():
    """Caso 1: Transacción ordinaria de bajo riesgo (Debe ser APROBADA)."""
    payload = {
        "transaction_id": "test-tx-legit-001",
        "user_id": "CC_1030405060",
        "amount": 35000.0,
        "timestamp": "2026-11-21T14:30:00Z",
        "channel": "APP_MOVIL",
        "destination_user_id": "CC_1099887766",
        "destination_bank": "YUMA_PAY",
        "destination_account": "3001234567",
        "device_id": "dev_trusted_user_1",
        "ip_address": "186.84.10.22",
        "geolocation_lat": 4.7110,
        "geolocation_lon": -74.0721,
        "os_type": "Android",
        "app_version": "3.4.1"
    }
    # Pre-cargar dispositivo como conocido en el Feature Store
    feature_store.in_memory.user_devices["CC_1030405060"].add("dev_trusted_user_1")

    response = client.post("/v1/decision", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["decision"] == "APROBADA"
    assert res["risk_level"] in ("BAJO", "MEDIO")
    assert res["risk_score"] < 0.35
    assert res["sla_compliant"] is True
    assert res["latency_ms"] < 300.0
    assert len(res["top_shap_factors"]) > 0


def test_sim_swap_critical_rule():
    """Caso 2: SIM Swapping en últimas 48 horas con monto relevante (Debe requerir CHALLENGE_2FA)."""
    user = "CC_52891234"
    # Registrar evento de cambio de SIM hace 6 horas
    import time
    feature_store.in_memory.user_sim_change[user] = time.time() - (6 * 3600)

    payload = {
        "transaction_id": "test-tx-simswap-002",
        "user_id": user,
        "amount": 750000.0,
        "timestamp": "2026-11-21T15:00:00Z",
        "channel": "APP_MOVIL",
        "destination_user_id": "CC_1011223344",
        "destination_bank": "BANCOLOMBIA",
        "destination_account": "9876543210",
        "device_id": "dev_sim_swap_suspicious",
        "ip_address": "190.158.45.12",
        "os_type": "Android"
    }

    response = client.post("/v1/decision", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["decision"] == "CHALLENGE_2FA"
    assert any(r["rule_id"] == "REG_01_SIM_SWAP_48H" for r in res["rules_triggered"])
    assert res["latency_ms"] < 300.0


def test_mule_device_farm_rule():
    """Caso 3: Granja de fraude operando con 5 identidades en el mismo teléfono (Debe RECHAZAR PREVENTIVAMENTE)."""
    device_id = "dev_mule_farm_bogota_99"
    # Simular 5 usuarios vinculados a este dispositivo
    feature_store.in_memory.device_users[device_id] = {
        "CC_111", "CC_222", "CC_333", "CC_444", "CC_555"
    }

    payload = {
        "transaction_id": "test-tx-mule-farm-003",
        "user_id": "CC_666",
        "amount": 900000.0,
        "timestamp": "2026-11-21T15:10:00Z",
        "channel": "APP_MOVIL",
        "destination_account": "3119998877",
        "device_id": device_id,
        "ip_address": "186.28.14.9"
    }

    response = client.post("/v1/decision", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["decision"] == "RECHAZADA_PREVENTIVA"
    assert res["risk_level"] == "CRITICO"
    assert any(r["rule_id"] == "REG_02_MULE_DEVICE_FARM" for r in res["rules_triggered"])
    assert res["sla_compliant"] is True


def test_sla_latency_compliance():
    """Caso 4: Medir 15 transacciones consecutivas y verificar P99 < 300 ms."""
    latencies = []
    for i in range(15):
        payload = {
            "transaction_id": f"benchmark-tx-{i}",
            "user_id": f"CC_BENCH_{i}",
            "amount": 100000.0 + (i * 5000),
            "timestamp": "2026-11-21T12:00:00Z",
            "channel": "APP_MOVIL",
            "device_id": f"dev_bench_{i}",
            "ip_address": "186.84.1.1"
        }
        res = client.post("/v1/decision", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["sla_compliant"] is True
        latencies.append(data["latency_ms"])

    max_lat = max(latencies)
    avg_lat = sum(latencies) / len(latencies)
    assert max_lat < 300.0
    print(f"\n[BENCHMARK SLA] Max Latency: {max_lat}ms, Avg Latency: {avg_lat:.2f}ms")
