"""
Pruebas automatizadas para la gestión dinámica de reglas y endpoints de auditoría.
Valida la creación en caliente de reglas personalizadas, activación/desactivación y su efecto inmediato en la decisión.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_rules():
    response = client.get("/v1/rules")
    assert response.status_code == 200
    rules = response.json()
    assert len(rules) >= 12
    assert any(r["rule_id"] == "REG_01_SIM_SWAP_48H" for r in rules)


def test_create_and_trigger_custom_rule():
    """Prueba de Concepto: Crear regla dinámica en caliente y verificar que impacta la decisión."""
    custom_rule = {
        "rule_id": "CUSTOM_POC_AMOUNT_PSE",
        "name": "Bloqueo por monto superior a 3M",
        "rule_type": "HARD_BLOCK",
        "field": "amount",
        "operator": ">",
        "threshold": 3000000.0,
        "weight": 1.0,
        "description": "Regla personalizada de prueba para bloquear montos extraordinarios",
        "forced_decision": "RECHAZADA_PREVENTIVA"
    }

    # 1. Crear regla
    res_create = client.post("/v1/rules", json=custom_rule)
    assert res_create.status_code == 201

    # 2. Transacción que supera el umbral (COP 3.500.000)
    tx_over = {
        "transaction_id": "tx-poc-custom-001",
        "user_id": "CC_11223344",
        "amount": 3500000.0,
        "channel": "PSE",
        "destination_account": "3009998877",
        "device_id": "dev_poc_user",
        "ip_address": "186.84.1.1"
    }
    res_eval = client.post("/v1/decision", json=tx_over)
    assert res_eval.status_code == 200
    data = res_eval.json()

    # La regla personalizada debe haberse activado y forzado el rechazo preventivo
    assert data["decision"] == "RECHAZADA_PREVENTIVA"
    assert any(r["rule_id"] == "CUSTOM_POC_AMOUNT_PSE" for r in data["rules_triggered"])

    # 3. Pausar la regla
    res_toggle = client.patch("/v1/rules/CUSTOM_POC_AMOUNT_PSE/toggle")
    assert res_toggle.status_code == 200
    assert res_toggle.json()["active"] is False

    # 4. Re-evaluar la misma transacción con la regla pausada (ya no debe forzar rechazo preventivo por esa regla)
    res_eval2 = client.post("/v1/decision", json=tx_over)
    assert res_eval2.status_code == 200
    data2 = res_eval2.json()
    assert not any(r["rule_id"] == "CUSTOM_POC_AMOUNT_PSE" for r in data2["rules_triggered"])

    # 5. Limpiar y eliminar la regla
    res_del = client.delete("/v1/rules/CUSTOM_POC_AMOUNT_PSE")
    assert res_del.status_code == 200


def test_transactions_audit_endpoint():
    res = client.get("/v1/transactions")
    assert res.status_code == 200
    txs = res.json()
    assert isinstance(txs, list)
    assert len(txs) > 0


def test_stats_endpoint():
    res = client.get("/v1/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "tasa_falsos_positivos" in stats
    assert "tasa_captura_fraude" in stats
