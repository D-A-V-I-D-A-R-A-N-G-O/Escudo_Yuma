"""
Esquemas Pydantic para el API de Decisión Antifraude.
Modelos estrictos para validación de entrada y respuesta auditable.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum


class ChannelEnum(str, Enum):
    APP_MOVIL = "APP_MOVIL"
    QR_ESTATICO = "QR_ESTATICO"
    QR_DINAMICO = "QR_DINAMICO"
    PSE = "PSE"
    TRANSFERENCIA_INTERBANCARIA = "TRANSFERENCIA_INTERBANCARIA"


class DecisionEnum(str, Enum):
    APROBADA = "APROBADA"
    CHALLENGE_2FA = "CHALLENGE_2FA"             # Step-up authentication (Biometría / OTP)
    REVISION_MANUAL = "REVISION_MANUAL"         # Cola de analistas humanos
    RECHAZADA_PREVENTIVA = "RECHAZADA_PREVENTIVA" # Rechazo preventivo inmediato


class RiskLevelEnum(str, Enum):
    BAJO = "BAJO"
    MEDIO = "MEDIO"
    ALTO = "ALTO"
    CRITICO = "CRITICO"


class TransactionRequest(BaseModel):
    """Payload de entrada recibido antes de autorizar la transacción."""
    transaction_id: str = Field(..., description="Identificador único UUID de la transacción")
    user_id: str = Field(..., description="Identificador del usuario / Cédula de Ciudadanía")
    amount: float = Field(..., gt=0, description="Monto de la transacción en COP (Pesos Colombianos)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Marca temporal UTC de la transacción")
    channel: ChannelEnum = Field(..., description="Canal origen de la transacción")
    destination_user_id: Optional[str] = Field(None, description="Usuario receptor en Yuma Pay o llave Transfiya")
    destination_bank: Optional[str] = Field(None, description="Banco destino (Bancolombia, Davivienda, Nequi, etc.)")
    destination_account: Optional[str] = Field(None, description="Número de cuenta o celular destino")
    device_id: str = Field(..., description="Identificador único del hardware / UUID del dispositivo")
    ip_address: str = Field(..., description="Dirección IP pública del cliente")
    geolocation_lat: Optional[float] = Field(None, description="Latitud GPS capturada por la app")
    geolocation_lon: Optional[float] = Field(None, description="Longitud GPS capturada por la app")
    location_city: Optional[str] = Field("Bogotá", description="Ciudad o región de la transacción")
    os_type: Optional[str] = Field("Android", description="Sistema operativo móvil (Android, iOS)")
    app_version: Optional[str] = Field("3.4.1", description="Versión de la app instalada")
    # Banderas contextuales de seguridad (útiles para la app móvil y simulación de incidentes)
    sim_swap_within_48h: Optional[bool] = Field(False, description="Indica si hubo cambio de SIM en <48 horas")
    pwd_reset_within_24h: Optional[bool] = Field(False, description="Indica si hubo cambio de clave en <24 horas")
    is_mule_destination: Optional[bool] = Field(False, description="Indica si la cuenta destino es sospechosa de mula")
    is_shared_device: Optional[bool] = Field(False, description="Indica si el dispositivo está compartido por múltiples cédulas")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "transaction_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "user_id": "CC_1020495812",
                "amount": 850000.0,
                "timestamp": "2026-11-21T09:15:00Z",
                "channel": "APP_MOVIL",
                "destination_user_id": "CC_1098234110",
                "destination_bank": "NEQUI",
                "destination_account": "3129847120",
                "device_id": "dev_f4a889b7291a",
                "ip_address": "186.84.92.14",
                "geolocation_lat": 4.60971,
                "geolocation_lon": -74.08175,
                "os_type": "Android",
                "app_version": "3.4.1"
            }
        }
    )


class ShapExplanation(BaseModel):
    """Explicación individual por factor según SHAP."""
    feature: str = Field(..., description="Nombre técnico de la variable")
    feature_value: float = Field(..., description="Valor medido para esta transacción")
    shap_value: float = Field(..., description="Impacto relativo en el log-odds de fraude")
    human_explanation: str = Field(..., description="Explicación legible para analistas y auditoría SFC")


class RuleEvaluationDetail(BaseModel):
    """Detalle de una regla evaluada."""
    rule_id: str
    rule_name: str
    rule_type: str  # HARD_BLOCK, CHALLENGE, SOFT_SCORE
    description: str
    impact_score: float


class DecisionResponse(BaseModel):
    """Respuesta síncrona entregada al core transaccional antes de 300 ms."""
    transaction_id: str
    decision: DecisionEnum
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Score unificado de fraude entre 0.0 y 1.0")
    risk_level: RiskLevelEnum
    ml_score: float = Field(..., description="Score generado por el modelo XGBoost")
    rules_score: float = Field(..., description="Score generado por el motor de reglas")
    latency_ms: float = Field(..., description="Latencia total de evaluación en milisegundos")
    sla_compliant: bool = Field(..., description="True si latency_ms < 300 ms")
    model_version: str = Field(..., description="Versión del modelo en producción")
    decision_reasons: List[str] = Field(..., description="Resumen de causas de la decisión")
    rules_triggered: List[RuleEvaluationDetail] = Field(default_factory=list)
    top_shap_factors: List[ShapExplanation] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
