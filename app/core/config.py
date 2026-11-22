"""
Configuración central del sistema Escudo Yuma.
Gestión de variables de entorno mediante Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Escudo Yuma - Fraud Decision Engine"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # SLA y Latencia
    SLA_LATENCY_THRESHOLD_MS: float = 300.0  # Máximo no negociable 300 ms
    SLA_WARNING_THRESHOLD_MS: float = 150.0

    # Conectividad de Almacenamiento
    REDIS_URL: str = "redis://localhost:6379/0"
    POSTGRES_URL: str = "postgresql://yuma_admin:EscudoYuma2026!@localhost:5432/escudo_yuma_db"

    # Umbrales de Calificación de Riesgo (0.0 a 1.0)
    # Calibrados para reducir falsos positivos a < 60%
    SCORE_THRESHOLD_APPROVE: float = 0.35      # < 0.35 -> APROBADA
    SCORE_THRESHOLD_CHALLENGE: float = 0.65    # 0.35 a 0.65 -> STEP_UP (Biometría / OTP)
    SCORE_THRESHOLD_REVIEW: float = 0.85       # 0.65 a 0.85 -> REVISIÓN MANUAL
    # >= 0.85 -> RECHAZO PREVENTIVO TEMPORAL (Bloqueo definitivo solo por analista)

    # Pesos de Hibridación: Score_Final = (w_ml * Score_ML) + (w_rules * Score_Rules)
    WEIGHT_ML_MODEL: float = 0.70
    WEIGHT_RULES_ENGINE: float = 0.30

    # Rutas de artefactos
    MODEL_PATH: str = "app/models/artifacts/model_xgboost_v1.json"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
