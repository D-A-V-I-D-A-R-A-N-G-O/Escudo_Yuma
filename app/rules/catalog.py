"""
Catálogo oficial y dinámico de reglas antifraude para Yuma Pay.
Soporta las 12 reglas de línea base más reglas dinámicas personalizables creadas en caliente por analistas.
"""

from typing import Dict, Any, List, Optional
from app.schemas.decision import DecisionEnum


class FraudRule:
    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: str,  # HARD_BLOCK, CHALLENGE, SOFT_SCORE, REVISION_MANUAL
        weight: float,
        description: str,
        forced_decision: Optional[DecisionEnum] = None,
        active: bool = True,
        is_custom: bool = False
    ):
        self.rule_id = rule_id
        self.name = name
        self.rule_type = rule_type
        self.weight = weight
        self.description = description
        self.forced_decision = forced_decision
        self.active = active
        self.is_custom = is_custom

    def evaluate(self, features: Dict[str, float]) -> bool:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "weight": self.weight,
            "description": self.description,
            "forced_decision": self.forced_decision.value if self.forced_decision else None,
            "active": self.active,
            "is_custom": self.is_custom
        }


class DynamicRule(FraudRule):
    """Regla dinámica creada en caliente por los analistas a través de la interfaz web o API."""
    def __init__(
        self,
        rule_id: str,
        name: str,
        rule_type: str,
        weight: float,
        description: str,
        field: str,
        operator: str,  # >, >=, <, <=, ==, !=
        threshold: float,
        forced_decision: Optional[DecisionEnum] = None,
        active: bool = True
    ):
        super().__init__(
            rule_id=rule_id,
            name=name,
            rule_type=rule_type,
            weight=weight,
            description=description,
            forced_decision=forced_decision,
            active=active,
            is_custom=True
        )
        self.field = field
        self.operator = operator
        self.threshold = threshold

    def evaluate(self, f: Dict[str, float]) -> bool:
        if not self.active:
            return False
        val = f.get(self.field, 0.0)
        op = self.operator
        th = self.threshold

        if op == ">":
            return val > th
        elif op == ">=":
            return val >= th
        elif op == "<":
            return val < th
        elif op == "<=":
            return val <= th
        elif op == "==":
            return abs(val - th) < 1e-5
        elif op == "!=":
            return abs(val - th) >= 1e-5
        return False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "field": self.field,
            "operator": self.operator,
            "threshold": self.threshold
        })
        return d


class RuleSimSwap48h(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_01_SIM_SWAP_48H",
            name="Cambio de SIM reciente (<48h) con monto de riesgo",
            rule_type="CHALLENGE",
            weight=0.85,
            description="El usuario realizó cambio de SIM hace menos de 48 horas y la transferencia supera COP 300.000.",
            forced_decision=DecisionEnum.CHALLENGE_2FA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("sim_swap_critical_48h", 0.0) == 1.0 and f.get("amount", 0.0) >= 300000.0


class RuleMuleDeviceFarm(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_02_MULE_DEVICE_FARM",
            name="Dispositivo operado por múltiples identidades (Granja / Mula)",
            rule_type="HARD_BLOCK",
            weight=1.0,
            description="El hardware del dispositivo ha sido utilizado por 4 o más identidades distintas en los últimos 7 días.",
            forced_decision=DecisionEnum.RECHAZADA_PREVENTIVA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("device_distinct_users_7d", 1.0) >= 4.0


class RuleNewDeviceAndPwdReset(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_03_NEW_DEVICE_PWD_RESET",
            name="Dispositivo no reconocido tras reseteo reciente de clave",
            rule_type="CHALLENGE",
            weight=0.80,
            description="Acceso desde un dispositivo nuevo con cambio de contraseña en las últimas 24 horas.",
            forced_decision=DecisionEnum.CHALLENGE_2FA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("device_is_new", 0.0) == 1.0 and f.get("pwd_reset_critical_24h", 0.0) == 1.0


class RuleMuleFanInNetwork(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_04_MULE_FAN_IN",
            name="Destinatario con alta concentración de captación (Mula)",
            rule_type="HARD_BLOCK",
            weight=0.90,
            description="La cuenta destino ha recibido transferencias de 5 o más clientes diferentes en menos de 24 horas.",
            forced_decision=DecisionEnum.REVISION_MANUAL
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("mule_in_degree_24h", 0.0) >= 5.0


class RuleVelocityBurst5m(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_05_VELOCITY_5M_BURST",
            name="Ráfaga transaccional en 5 minutos",
            rule_type="CHALLENGE",
            weight=0.60,
            description="Más de 3 transacciones ejecutadas en una ventana de 5 minutos.",
            forced_decision=DecisionEnum.CHALLENGE_2FA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("tx_count_5m", 0.0) >= 3.0


class RuleNighttimeOutlier(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_06_NIGHTTIME_OUTLIER",
            name="Desviación de monto atípico en horario nocturno",
            rule_type="SOFT_SCORE",
            weight=0.50,
            description="Monto superior a 4 veces el promedio histórico del cliente entre las 23:00 y las 05:00."
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("is_nighttime", 0.0) == 1.0 and f.get("ratio_vs_avg_amount", 1.0) >= 4.0


class RuleStaticQRHighAmount(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_07_STATIC_QR_HIGH_AMOUNT",
            name="Transacción elevada mediante código QR estático",
            rule_type="SOFT_SCORE",
            weight=0.45,
            description="Monto mayor a COP 800.000 realizado a través de QR estático (riesgo de calcomanía superpuesta)."
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("channel_risk", 0.0) >= 0.40 and f.get("amount", 0.0) >= 800000.0


class RuleNewAccountHighValue(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_08_NEW_ACCOUNT_HIGH_VALUE",
            name="Cuenta recién creada con movimiento de alta cuantía",
            rule_type="CHALLENGE",
            weight=0.70,
            description="Cuenta con menos de 7 días de antigüedad transfiriendo más de COP 1.500.000.",
            forced_decision=DecisionEnum.CHALLENGE_2FA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("account_age_days", 180.0) <= 7.0 and f.get("amount", 0.0) >= 1500000.0


class RuleVelocity24hExceeded(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_09_VELOCITY_24H_EXCEEDED",
            name="Frecuencia transaccional diaria atípica",
            rule_type="SOFT_SCORE",
            weight=0.40,
            description="Más de 12 transacciones acumuladas en las últimas 24 horas."
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("tx_count_24h", 0.0) >= 12.0


class RuleAmountExtremeSpike(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_10_AMOUNT_EXTREME_SPIKE",
            name="Monto superior a 6 veces el promedio del cliente",
            rule_type="SOFT_SCORE",
            weight=0.55,
            description="El monto transado supera 6 veces el promedio habitual de transacciones del cliente."
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("ratio_vs_avg_amount", 1.0) >= 6.0


class RuleHourlyVelocityHigh(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_11_HOURLY_VELOCITY_HIGH",
            name="Concentración de transacciones en 1 hora",
            rule_type="SOFT_SCORE",
            weight=0.35,
            description="Más de 6 transacciones en la última hora."
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("tx_count_1h", 0.0) >= 6.0


class RuleMuleDestinationConfirmed(FraudRule):
    def __init__(self):
        super().__init__(
            rule_id="REG_12_MULE_DEST_CONFIRMED",
            name="Destino con indicios directos de cuenta puente o mula",
            rule_type="HARD_BLOCK",
            weight=0.95,
            description="La cuenta receptora ha sido clasificada con alta centralidad de red en anillos de mulas.",
            forced_decision=DecisionEnum.RECHAZADA_PREVENTIVA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return f.get("is_mule_destination", 0.0) == 1.0 and f.get("amount", 0.0) >= 400000.0


class RuleGeoIpAnomaly(FraudRule):
    """Regla 13: Salto de geolocalización o IP sospechosa (VPN / Extranjero)."""
    def __init__(self):
        super().__init__(
            rule_id="REG_13_GEO_IP_ANOMALY",
            name="Conexión desde IP sospechosa o ubicación anómala",
            rule_type="CHALLENGE",
            weight=0.75,
            description="La transacción proviene de una IP catalogada como VPN/Proxy o desde una ubicación geográfica distante.",
            forced_decision=DecisionEnum.CHALLENGE_2FA
        )

    def evaluate(self, f: Dict[str, float]) -> bool:
        return (f.get("is_geo_anomaly", 0.0) == 1.0 and f.get("amount", 0.0) >= 300000.0) or f.get("is_suspicious_ip", 0.0) == 1.0


def get_default_rules() -> List[FraudRule]:
    return [
        RuleSimSwap48h(),
        RuleMuleDeviceFarm(),
        RuleNewDeviceAndPwdReset(),
        RuleMuleFanInNetwork(),
        RuleVelocityBurst5m(),
        RuleNighttimeOutlier(),
        RuleStaticQRHighAmount(),
        RuleNewAccountHighValue(),
        RuleVelocity24hExceeded(),
        RuleAmountExtremeSpike(),
        RuleHourlyVelocityHigh(),
        RuleMuleDestinationConfirmed(),
        RuleGeoIpAnomaly(),
    ]

RULES_CATALOG: List[FraudRule] = get_default_rules()
