# Reglas Antifraude Implementadas en Escudo Yuma

## Tipos de Regla
| Tipo | Descripción |
|------|-------------|
| **HARD_BLOCK** | Bloqueo definitivo de la transacción. Requiere intervención humana para revertir. |
| **CHALLENGE** | Desafío al usuario (2FA, OTP, etc.). La transacción puede aprobarse si supera el desafío. |
| **REVISION_MANUAL** | La transacción es marcada para revisión manual por el analista. |
| **SOFT_SCORE** | Aporta un puntaje al modelo de decisión sin forzar veredicto. |

## Tabla Resumen de Reglas
| ID | Nombre | Tipo | Veredicto Forzado |
|----|--------|------|-------------------|
| REG_01_SIM_SWAP_48H | Cambio de SIM reciente (<48h) con monto de riesgo | CHALLENGE | CHALLENGE_2FA |
| REG_02_MULE_DEVICE_FARM | Dispositivo operado por múltiples identidades | HARD_BLOCK | RECHAZADA_PREVENTIVA |
| REG_03_NEW_DEVICE_PWD_RESET | Dispositivo no reconocido tras reseteo reciente | CHALLENGE | CHALLENGE_2FA |
| REG_04_MULE_FAN_IN | Destinatario con alta concentración de captación | HARD_BLOCK | REVISION_MANUAL |
| REG_05_VELOCITY_5M_BURST | Ráfaga transaccional en 5 minutos | CHALLENGE | CHALLENGE_2FA |
| REG_06_NIGHTTIME_OUTLIER | Desviación de monto atípico en horario nocturno | SOFT_SCORE | — |
| REG_07_STATIC_QR_HIGH_AMOUNT | Transacción elevada mediante QR estático | SOFT_SCORE | — |
| REG_08_NEW_ACCOUNT_HIGH_VALUE | Cuenta recién creada con movimiento de alta cuantía | CHALLENGE | CHALLENGE_2FA |
| REG_09_VELOCITY_24H_EXCEEDED | Frecuencia transaccional diaria atípica | SOFT_SCORE | — |
| REG_10_AMOUNT_EXTREME_SPIKE | Monto superior a 6× el promedio del cliente | SOFT_SCORE | — |
| REG_11_HOURLY_VELOCITY_HIGH | Concentración de transacciones en 1 hora | SOFT_SCORE | — |
| REG_12_MULE_DEST_CONFIRMED | Destino con indicios directos de cuenta mula | HARD_BLOCK | RECHAZADA_PREVENTIVA |
| REG_13_GEO_IP_ANOMALY | Conexión desde IP sospechosa o ubicación anómala | CHALLENGE | CHALLENGE_2FA |

## Detalle de Cada Regla

### REG_01_SIM_SWAP_48H
- **Tipo:** CHALLENGE
- **Veredicto Forzado:** CHALLENGE_2FA
- **Peso / Severidad:** 1.80
- **Variables Evaluadas:** `sim_swap_critical_48h`, `amount`
- **Condición:** `sim_swap_critical_48h == 1.0 AND amount >= 300000`
- **Descripción:** Detecta SIM swap crítico dentro de las 48 horas previas a la transacción con monto elevado, obligando al usuario a validar mediante 2FA.
- **Tipología de Fraude:** Suplantación de identidad (SIM swap).

### REG_02_MULE_DEVICE_FARM
- **Tipo:** HARD_BLOCK
- **Veredicto Forzado:** RECHAZADA_PREVENTIVA
- **Peso / Severidad:** 2.00
- **Variables Evaluadas:** `device_distinct_users_7d`
- **Condición:** `device_distinct_users_7d >= 4.0`
- **Descripción:** Un dispositivo usado por más de 4 usuarios diferentes en los últimos 7 días indica posible “farm” de dispositivos para cuentas mula.
- **Tipología de Fraude:** Dispositivo compartido / cuentas mula.

### REG_03_NEW_DEVICE_PWD_RESET
- **Tipo:** CHALLENGE
- **Veredicto Forzado:** CHALLENGE_2FA
- **Peso / Severidad:** 1.60
- **Variables Evaluadas:** `device_is_new`, `pwd_reset_critical_24h`
- **Condición:** `device_is_new == 1.0 AND pwd_reset_critical_24h == 1.0`
- **Descripción:** Un dispositivo nuevo que además ha sufrido un restablecimiento de contraseña en las últimas 24 h se desafía con 2FA.
- **Tipología de Fraude:** Robo de credenciales y uso de nuevo dispositivo.

### REG_04_MULE_FAN_IN
- **Tipo:** HARD_BLOCK
- **Veredicto Forzado:** REVISION_MANUAL
- **Peso / Severidad:** 1.90
- **Variables Evaluadas:** `mule_in_degree_24h`
- **Condición:** `mule_in_degree_24h >= 5.0`
- **Descripción:** Destinatario que recibe un número elevado de transferencias en 24 h, señalando posible cuenta mula.
- **Tipología de Fraude:** Concentración de fondos en cuentas sospechosas.

### REG_05_VELOCITY_5M_BURST
- **Tipo:** CHALLENGE
- **Veredicto Forzado:** CHALLENGE_2FA
- **Peso / Severidad:** 1.40
- **Variables Evaluadas:** `tx_count_5m`
- **Condición:** `tx_count_5m >= 3.0`
- **Descripción:** Tres o más transacciones en un intervalo de 5 minutos generan un desafío adicional.
- **Tipología de Fraude:** Ataque de ráfaga (burst).

### REG_06_NIGHTTIME_OUTLIER
- **Tipo:** SOFT_SCORE
- **Veredicto Forzado:** —
- **Peso / Severidad:** 0.80
- **Variables Evaluadas:** `is_nighttime`, `ratio_vs_avg_amount`
- **Condición:** `is_nighttime == 1.0 AND ratio_vs_avg_amount >= 4.0`
- **Descripción:** Monto atípico durante horarios nocturnos que aumenta el puntaje de riesgo.
- **Tipología de Fraude:** Transacciones fuera de patrón horario.

### REG_07_STATIC_QR_HIGH_AMOUNT
- **Tipo:** SOFT_SCORE
- **Veredicto Forzado:** —
- **Peso / Severidad:** 0.70
- **Variables Evaluadas:** `channel_risk`, `amount`
- **Condición:** `channel_risk >= 0.40 AND amount >= 800000`
- **Descripción:** Uso de QR estático con alto riesgo y monto elevado incrementa el riesgo global.
- **Tipología de Fraude:** Clonación de código QR estático.

### REG_08_NEW_ACCOUNT_HIGH_VALUE
- **Tipo:** CHALLENGE
- **Veredicto Forzado:** CHALLENGE_2FA
- **Peso / Severidad:** 1.55
- **Variables Evaluadas:** `account_age_days`, `amount`
- **Condición:** `account_age_days <= 7.0 AND amount >= 1500000`
- **Descripción:** Cuenta recién creada que ejecuta una transacción de alto valor obliga a 2FA.
- **Tipología de Fraude:** Lavado de dinero vía cuentas recién creadas.

### REG_09_VELOCITY_24H_EXCEEDED
- **Tipo:** SOFT_SCORE
- **Veredicto Forzado:** —
- **Peso / Severidad:** 0.75
- **Variables Evaluadas:** `tx_count_24h`
- **Condición:** `tx_count_24h >= 12.0`
- **Descripción:** Alta frecuencia diaria añade puntaje de riesgo.
- **Tipología de Fraude:** Volumen anómalo.

### REG_10_AMOUNT_EXTREME_SPIKE
- **Tipo:** SOFT_SCORE
- **Veredicto Forzado:** —
- **Peso / Severidad:** 0.85
- **Variables Evaluadas:** `ratio_vs_avg_amount`
- **Condición:** `ratio_vs_avg_amount >= 6.0`
- **Descripción:** Monto que supera 6 × el promedio histórico del cliente incrementa el riesgo.
- **Tipología de Fraude:** Spike de monto.

### REG_11_HOURLY_VELOCITY_HIGH
- **Tipo:** SOFT_SCORE
- **Veredicto Forzado:** —
- **Peso / Severidad:** 0.78
- **Variables Evaluadas:** `tx_count_1h`
- **Condición:** `tx_count_1h >= 6.0`
- **Descripción:** Concentración de transacciones en una hora eleva el puntaje.
- **Tipología de Fraude:** Burst por hora.

### REG_12_MULE_DEST_CONFIRMED
- **Tipo:** HARD_BLOCK
- **Veredicto Forzado:** RECHAZADA_PREVENTIVA
- **Peso / Severidad:** 2.00
- **Variables Evaluadas:** `is_mule_destination`, `amount`
- **Condición:** `is_mule_destination == 1.0 AND amount >= 400000`
- **Descripción:** Destino identificado como cuenta mula con monto relevante bloquea la transacción.
- **Tipología de Fraude:** Transferencia a cuenta mula.

### REG_13_GEO_IP_ANOMALY
- **Tipo:** CHALLENGE
- **Veredicto Forzado:** CHALLENGE_2FA
- **Peso / Severidad:** 1.70 (IP) / 1.45 (Geo)
- **Variables Evaluadas:** `is_geo_anomaly`, `is_suspicious_ip`, `amount`
- **Condición:** `(is_geo_anomaly == 1.0 AND amount >= 300000) OR is_suspicious_ip == 1.0`
- **Descripción:** Conexión desde IP sospechosa (rangos 45.*, 194.*, 185.* o contiene "vpn") o ubicación geográfica atípica (ciudades exteriores) genera desafío 2FA.
- **Tipología de Fraude:** Fraude por ubicación / uso de VPN/Tor.

## Variables de Características Disponibles
| Variable | Tipo | Descripción |
|----------|------|-------------|
| `sim_swap_critical_48h` | binario | 1 si el número de teléfono cambió de SIM en las últimas 48 h. |
| `device_distinct_users_7d` | entero | Cantidad de usuarios diferentes que usaron el mismo dispositivo en los últimos 7 días. |
| `device_is_new` | binario | 1 si el dispositivo nunca se había usado antes por el usuario. |
| `pwd_reset_critical_24h` | binario | 1 si la cuenta tuvo un restablecimiento de contraseña crítico en las últimas 24 h. |
| `mule_in_degree_24h` | entero | Número de transferencias entrantes a la cuenta destino en 24 h. |
| `tx_count_5m` | entero | Número de transacciones en los últimos 5 min. |
| `is_nighttime` | binario | 1 si la transacción ocurre entre 00:00‑05:00 (zona del cliente). |
| `ratio_vs_avg_amount` | decimal | Monto / promedio histórico del cliente. |
| `channel_risk` | decimal | Riesgo asociado al canal (QR estático, QR dinámico, web, etc.). |
| `account_age_days` | entero | Días desde la creación de la cuenta. |
| `tx_count_24h` | entero | Número de transacciones en las últimas 24 h. |
| `tx_count_1h` | entero | Número de transacciones en la última hora. |
| `is_mule_destination` | binario | 1 si la cuenta destino está marcada como posible cuenta mula. |
| `is_suspicious_ip` | binario | 1 si la IP pertenece a rangos sospechosos o contiene la palabra "vpn". |
| `is_geo_anomaly` | binario | 1 si la ciudad reportada está fuera del territorio habitual del cliente. |
| `amount` | entero | Monto de la transacción (en COP). |
| `ip_address` | texto | Dirección IP de la petición. |
| `location_city` | texto | Ciudad declarada por el cliente. |

## Creación de Reglas Personalizadas
- **API REST:** `POST /v1/rules` con JSON que incluye `id`, `name`, `type`, `condition`, `forced_decision`, `weight`.
- **UI Monitor:** En la tabla de reglas, botón **"Crear Regla"** abre un modal donde se pueden definir los campos anteriores y activar/desactivar la regla.
- **Persistencia:** Actualmente las reglas se guardan en memoria. Para persistir entre reinicios, se recomienda exportar a `json` y cargarlas al iniciar la aplicación.

## Umbrales de Decisión Global
| Rango de Score Final | Veredicto |
|----------------------|-----------|
| < 0.35 | **APROBADA** |
| 0.35 – 0.65 | **CHALLENGE_2FA** |
| 0.65 – 0.85 | **REVISION_MANUAL** |
| ≥ 0.85 | **RECHAZADA_PREVENTIVA** |

> **Nota:** El Score Final = `0.70 × ML_Score + 0.30 × Rules_Score`.

---
*Este documento está generado automáticamente por Antigravity y refleja el estado actual del motor de reglas del proyecto Escudo Yuma.*