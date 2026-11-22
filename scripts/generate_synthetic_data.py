"""
Generador de datasets sintéticos realistas para Yuma Pay (Billetera Digital Colombiana).
Genera los 5 datasets de referencia:
1. clientes.csv (6.000 usuarios)
2. transacciones.csv (121.000 registros con etiquetas de fraude y modalidades)
3. eventos_app.csv (~48.000 eventos de seguridad y dispositivo)
4. alertas.csv (histórico del motor previo con 92% de falsos positivos)
5. reglas_vigentes.csv (12 reglas de línea base)
"""

import os
import csv
import random
import uuid
from datetime import datetime, timedelta

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CIUDADES = [
    ("Bogotá", 4.6097, -74.0817),
    ("Medellín", 6.2442, -75.5812),
    ("Cali", 3.4516, -76.5320),
    ("Barranquilla", 10.9685, -74.7813),
    ("Bucaramanga", 7.1254, -73.1198),
    ("Pereira", 4.8133, -75.6961),
]

BANCOS_COL = ["BANCOLOMBIA", "DAVIVIENDA", "NEQUI", "DAVIPLATA", "BANCO_DE_BOGOTA", "BBVA"]
CANALES = ["APP_MOVIL", "QR_ESTATICO", "QR_DINAMICO", "PSE", "TRANSFERENCIA_INTERBANCARIA"]
MODALIDADES_FRAUDE = [
    "TOMA_DE_CUENTA_PHISHING",
    "SIM_SWAPPING",
    "CUENTAS_MULA",
    "ENGANO_QR_COMPROBANTE_FALSO",
    "INGENIERIA_SOCIAL"
]

print("Generando clientes.csv (6.000 registros)...")
clientes = []
for i in range(1, 6001):
    cedula = f"CC_{10000000 + (i * 12345) % 89999999}"
    ciudad, lat, lon = random.choice(CIUDADES)
    antiguedad_dias = random.randint(10, 730)
    promedio_mensual = random.choice([80000, 150000, 250000, 500000, 1200000])
    clientes.append({
        "id_cliente": cedula,
        "ciudad": ciudad,
        "lat": lat + random.uniform(-0.05, 0.05),
        "lon": lon + random.uniform(-0.05, 0.05),
        "antiguedad_dias": antiguedad_dias,
        "promedio_monto_habitual": promedio_mensual,
        "dispositivo_habitual": f"dev_{cedula[-8:]}",
        "estado": "ACTIVO"
    })

with open(os.path.join(DATA_DIR, "clientes.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=clientes[0].keys())
    writer.writeheader()
    writer.writerows(clientes)

print("Generando eventos_app.csv (48.000 eventos de seguridad)...")
eventos = []
base_time = datetime(2026, 10, 1, 0, 0, 0)
tipos_evento = ["LOGIN_EXITOSO", "LOGIN_FALLIDO", "CAMBIO_CONTRASENA", "REPORTE_CAMBIO_SIM", "DISPOSITIVO_VINCULADO"]
pesos_evento = [0.70, 0.15, 0.05, 0.03, 0.07]

for i in range(48000):
    cli = random.choice(clientes)
    tipo = random.choices(tipos_evento, weights=pesos_evento)[0]
    ts = base_time + timedelta(minutes=random.randint(1, 50000))
    eventos.append({
        "id_evento": f"EVT_{i+1:06d}",
        "id_cliente": cli["id_cliente"],
        "tipo_evento": tipo,
        "timestamp": ts.isoformat(),
        "ip": f"186.84.{random.randint(1, 254)}.{random.randint(1, 254)}",
        "id_dispositivo": cli["dispositivo_habitual"] if random.random() > 0.10 else f"dev_unknown_{random.randint(100, 999)}"
    })

with open(os.path.join(DATA_DIR, "eventos_app.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=eventos[0].keys())
    writer.writeheader()
    writer.writerows(eventos)

print("Generando transacciones.csv (121.000 transacciones)...")
# Tasa de fraude natural ~ 1.9% (~2.300 fraudes mensuales)
transacciones = []
for i in range(121000):
    cli = random.choice(clientes)
    tx_time = base_time + timedelta(minutes=random.randint(1, 45000))
    is_night = (tx_time.hour >= 23 or tx_time.hour <= 5)

    # Decidir si es fraude
    is_fraud = random.random() < 0.019
    modalidad = ""
    canal = random.choice(CANALES)

    if is_fraud:
        modalidad = random.choice(MODALIDADES_FRAUDE)
        if modalidad == "TOMA_DE_CUENTA_PHISHING":
            monto = random.randint(800000, 3500000)
            dispositivo = f"dev_fraud_{random.randint(10, 50)}"
        elif modalidad == "SIM_SWAPPING":
            monto = random.randint(1200000, 4800000)
            dispositivo = f"dev_sim_{random.randint(1, 100)}"
        elif modalidad == "CUENTAS_MULA":
            monto = random.randint(500000, 2000000)
            dispositivo = f"dev_mule_ring_{random.randint(1, 10)}"
        elif modalidad == "ENGANO_QR_COMPROBANTE_FALSO":
            monto = random.randint(200000, 1500000)
            canal = "QR_ESTATICO"
            dispositivo = cli["dispositivo_habitual"]
        else: # INGENIERIA_SOCIAL
            monto = random.randint(400000, 2800000)
            dispositivo = cli["dispositivo_habitual"]
    else:
        # Transacción legítima
        monto = max(5000, int(random.gauss(cli["promedio_monto_habitual"], cli["promedio_monto_habitual"] * 0.4)))
        dispositivo = cli["dispositivo_habitual"] if random.random() > 0.05 else f"dev_new_{random.randint(1, 500)}"

    transacciones.append({
        "id_transaccion": str(uuid.uuid4()),
        "id_cliente": cli["id_cliente"],
        "monto_cop": monto,
        "fecha_hora": tx_time.isoformat(),
        "canal": canal,
        "id_destino": f"CC_{random.randint(10000000, 99999999)}",
        "banco_destino": random.choice(BANCOS_COL),
        "id_dispositivo": dispositivo,
        "ip": f"186.84.{random.randint(1, 254)}.{random.randint(1, 254)}",
        "es_fraude": 1 if is_fraud else 0,
        "modalidad_fraude": modalidad
    })

with open(os.path.join(DATA_DIR, "transacciones.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=transacciones[0].keys())
    writer.writeheader()
    writer.writerows(transacciones)

print("Generando alertas.csv (Histórico del motor actual con 92% de falsos positivos)...")
# 4.000 alertas simuladas
alertas = []
fraud_txs = [t for t in transacciones if t["es_fraude"] == 1]
legit_txs = [t for t in transacciones if t["es_fraude"] == 0]

for i in range(4000):
    # 92% de falsos positivos -> 8% fraude real
    es_real = random.random() < 0.08
    tx = random.choice(fraud_txs) if (es_real and fraud_txs) else random.choice(legit_txs)
    alertas.append({
        "id_alerta": f"ALT_{i+1:06d}",
        "id_transaccion": tx["id_transaccion"],
        "id_cliente": tx["id_cliente"],
        "monto_cop": tx["monto_cop"],
        "regla_disparada": random.choice([
            "R01_MONTO_SUPERIOR_1M",
            "R02_HORARIO_NOCTURNO",
            "R03_TRANSACCION_FIN_DE_SEMANA",
            "R04_CAMBIO_DE_CANAL"
        ]),
        "resultado_investigacion": "FRAUDE_CONFIRMADO" if tx["es_fraude"] == 1 else "FALSO_POSITIVO"
    })

with open(os.path.join(DATA_DIR, "alertas.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=alertas[0].keys())
    writer.writeheader()
    writer.writerows(alertas)

print("Generando reglas_vigentes.csv (12 reglas de línea base)...")
reglas = [
    {"id_regla": "R01", "nombre": "Monto Mayor a 1M COP", "tipo": "ESTATICA", "umbral": "monto > 1000000", "tasa_fp_actual": "88%"},
    {"id_regla": "R02", "nombre": "Horario Nocturno Simple", "tipo": "ESTATICA", "umbral": "hora >= 23 or hora <= 5", "tasa_fp_actual": "95%"},
    {"id_regla": "R03", "nombre": "Monto Mayor a 3M en Fin de Semana", "tipo": "ESTATICA", "umbral": "fin_semana and monto > 3000000", "tasa_fp_actual": "91%"},
    {"id_regla": "R04", "nombre": "Frecuencia mayor a 3 txs en 1 hora", "tipo": "ESTATICA", "umbral": "count_1h > 3", "tasa_fp_actual": "89%"},
    {"id_regla": "R05", "nombre": "Nuevo Dispositivo Simple", "tipo": "ESTATICA", "umbral": "dispositivo != habitual", "tasa_fp_actual": "96%"},
    {"id_regla": "R06", "nombre": "Destino Nuevo con monto > 500k", "tipo": "ESTATICA", "umbral": "destino_nuevo and monto > 500000", "tasa_fp_actual": "90%"},
    {"id_regla": "R07", "nombre": "Cambio de SIM sin considerar tiempo", "tipo": "ESTATICA", "umbral": "sim_change == True", "tasa_fp_actual": "85%"},
    {"id_regla": "R08", "nombre": "IP de departamento diferente", "tipo": "ESTATICA", "umbral": "ip_depto != cliente_depto", "tasa_fp_actual": "97%"},
    {"id_regla": "R09", "nombre": "Monto redondo mayor a 500k", "tipo": "ESTATICA", "umbral": "monto % 100000 == 0 and monto >= 500000", "tasa_fp_actual": "93%"},
    {"id_regla": "R10", "nombre": "Transferencia por QR estático > 300k", "tipo": "ESTATICA", "umbral": "canal == QR_ESTATICO and monto > 300000", "tasa_fp_actual": "92%"},
    {"id_regla": "R11", "nombre": "Cuenta con antigüedad < 30 días", "tipo": "ESTATICA", "umbral": "antiguedad < 30 and monto > 200000", "tasa_fp_actual": "87%"},
    {"id_regla": "R12", "nombre": "Más de 5 destinos en 24h", "tipo": "ESTATICA", "umbral": "destinos_24h > 5", "tasa_fp_actual": "94%"}
]

with open(os.path.join(DATA_DIR, "reglas_vigentes.csv"), "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=reglas[0].keys())
    writer.writeheader()
    writer.writerows(reglas)

print("¡Datasets sintéticos generados exitosamente en la carpeta 'data/'!")
