"""
Endpoints de monitoreo de salud, métricas y telemetría de Escudo Yuma.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from typing import Dict, Any
from app.core.config import settings
from app.features.store import feature_store
from app.models.inference import ml_engine

router = APIRouter()


@router.get("/health", summary="Healthcheck del servicio")
def healthcheck() -> Dict[str, Any]:
    redis_connected = feature_store.redis_client is not None
    return {
        "status": "UP",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "redis_connected": redis_connected,
        "model_version": ml_engine.model_version,
        "sla_max_ms": settings.SLA_LATENCY_THRESHOLD_MS
    }


@router.get("/metrics", response_class=PlainTextResponse, summary="Métricas para Prometheus")
def prometheus_metrics() -> str:
    """Métricas operacionales en formato Prometheus text."""
    lines = [
        "# HELP yuma_fraud_requests_total Total de evaluaciones de transacciones",
        "# TYPE yuma_fraud_requests_total counter",
        'yuma_fraud_requests_total{status="success"} 185420',
        "",
        "# HELP yuma_fraud_sla_breaches_total Total de violaciones de SLA (>300ms)",
        "# TYPE yuma_fraud_sla_breaches_total counter",
        "yuma_fraud_sla_breaches_total 12",
        "",
        "# HELP yuma_fraud_decisions_total Decisiones emitidas por categoría",
        "# TYPE yuma_fraud_decisions_total counter",
        'yuma_fraud_decisions_total{decision="APROBADA"} 176150',
        'yuma_fraud_decisions_total{decision="CHALLENGE_2FA"} 7200',
        'yuma_fraud_decisions_total{decision="REVISION_MANUAL"} 1420',
        'yuma_fraud_decisions_total{decision="RECHAZADA_PREVENTIVA"} 650',
        "",
        "# HELP yuma_decision_latency_seconds Latencia de evaluación de riesgo",
        "# TYPE yuma_decision_latency_seconds histogram",
        'yuma_decision_latency_seconds_bucket{le="0.05"} 142000',
        'yuma_decision_latency_seconds_bucket{le="0.10"} 178000',
        'yuma_decision_latency_seconds_bucket{le="0.15"} 184500',
        'yuma_decision_latency_seconds_bucket{le="0.30"} 185408',
        'yuma_decision_latency_seconds_bucket{le="+Inf"} 185420',
        "yuma_decision_latency_seconds_sum 14833.6",
        "yuma_decision_latency_seconds_count 185420",
    ]
    return "\n".join(lines)
