"""
Endpoint principal de decisión de riesgo en tiempo real (/v1/decision).
Orquesta la extracción de variables, el motor de reglas, la inferencia ML,
la explicación SHAP y el cumplimiento de la latencia máxima no negociable de 300 ms.
"""

import time
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from app.schemas.decision import (
    TransactionRequest,
    DecisionResponse,
    DecisionEnum,
    RiskLevelEnum
)
from app.core.config import settings
from app.features.extractor import extract_features
from app.features.store import feature_store
from app.features.audit import audit_buffer
from app.rules.engine import rules_engine
from app.models.inference import ml_engine

logger = logging.getLogger("escudo_yuma.decision")
router = APIRouter()


def persist_audit_log_and_update_state(request: TransactionRequest, response: DecisionResponse):
    """
    Tarea en segundo plano para no demorar la respuesta de autorización al usuario.
    Registra el evento en el Feature Store e inserta el log auditable para la SFC.
    """
    try:
        dest = request.destination_account or request.destination_user_id
        current_ts = request.timestamp.timestamp()
        feature_store.commit_transaction_event(
            user_id=request.user_id,
            amount=request.amount,
            dest_account=dest,
            device_id=request.device_id,
            current_ts=current_ts
        )
        audit_buffer.record({
            "transaction_id": response.transaction_id,
            "user_id": request.user_id,
            "amount": request.amount,
            "channel": request.channel.value,
            "destination_bank": request.destination_bank or "YUMA_PAY",
            "destination_account": dest or "N/A",
            "ip_address": request.ip_address,
            "location_city": getattr(request, "location_city", "Bogotá") or "Bogotá",
            "decision": response.decision.value,
            "risk_score": response.risk_score,
            "risk_level": response.risk_level.value,
            "ml_score": response.ml_score,
            "rules_score": response.rules_score,
            "latency_ms": response.latency_ms,
            "sla_compliant": response.sla_compliant,
            "timestamp": response.evaluated_at.isoformat(),
            "rules_triggered": [r.model_dump() for r in response.rules_triggered],
            "top_shap_factors": [s.model_dump() for s in response.top_shap_factors],
            "reasons": response.decision_reasons
        })
    except Exception as e:
        logger.error(f"Error registrando auditoría en background: {e}")


@router.post(
    "/decision",
    response_model=DecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluar riesgo de transacción en tiempo real",
    description="Califica el riesgo de una transacción antes de autorizar la salida de fondos. Latencia SLA < 300ms."
)
async def evaluate_transaction(
    request: TransactionRequest,
    background_tasks: BackgroundTasks
) -> DecisionResponse:
    start_time = time.perf_counter()

    try:
        # 1. Extracción de características (Feature Store + Enriquecimiento)
        features = extract_features(request)

        # 2. Evaluación del motor de reglas
        rules_score, hard_decision, rules_triggered = rules_engine.evaluate(features)

        # 3. Inferencia de Machine Learning (XGBoost) + Explicación SHAP
        ml_score, top_shaps = ml_engine.predict_and_explain(features)

        # 4. Hibridación de Score (ML + Reglas)
        risk_score = round(
            (settings.WEIGHT_ML_MODEL * ml_score) + (settings.WEIGHT_RULES_ENGINE * rules_score),
            4
        )
        risk_score = min(1.0, max(0.0, risk_score))

        # 5. Determinación de la decisión final
        reasons = []

        if hard_decision is not None:
            # Regla dura toma precedencia
            final_decision = hard_decision
            reasons.append(f"Activación de regla crítica mandatoria: {rules_triggered[0].rule_name}")
        else:
            # Calificación basada en score continuo optimizado
            if risk_score < settings.SCORE_THRESHOLD_APPROVE:
                final_decision = DecisionEnum.APROBADA
                reasons.append("Transacción consistente con el perfil histórico y parámetros de bajo riesgo.")
            elif risk_score < settings.SCORE_THRESHOLD_CHALLENGE:
                final_decision = DecisionEnum.CHALLENGE_2FA
                reasons.append("Riesgo moderado: Se requiere autenticación robusta de segundo factor (Biometría / OTP).")
            elif risk_score < settings.SCORE_THRESHOLD_REVIEW:
                final_decision = DecisionEnum.REVISION_MANUAL
                reasons.append("Riesgo elevado: Derivada a mesa de control de analistas para verificación preventiva.")
            else:
                final_decision = DecisionEnum.RECHAZADA_PREVENTIVA
                reasons.append("Riesgo crítico de fraude: Operación rechazada preventivamente.")

        # Añadir razones basadas en factores SHAP destacados
        for s in top_shaps[:2]:
            if s.shap_value > 0.5:
                reasons.append(s.human_explanation)

        # 6. Clasificación de nivel de riesgo
        if risk_score < 0.25:
            risk_level = RiskLevelEnum.BAJO
        elif risk_score < 0.55:
            risk_level = RiskLevelEnum.MEDIO
        elif risk_score < 0.80:
            risk_level = RiskLevelEnum.ALTO
        else:
            risk_level = RiskLevelEnum.CRITICO

        # 7. Cálculo de latencia transcurrida y validación de SLA
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        sla_compliant = elapsed_ms <= settings.SLA_LATENCY_THRESHOLD_MS

        if not sla_compliant:
            logger.warning(
                f"[SLA BREACH] Transacción {request.transaction_id} tardó {elapsed_ms}ms "
                f"(Límite: {settings.SLA_LATENCY_THRESHOLD_MS}ms)"
            )

        response = DecisionResponse(
            transaction_id=request.transaction_id,
            decision=final_decision,
            risk_score=risk_score,
            risk_level=risk_level,
            ml_score=ml_score,
            rules_score=rules_score,
            latency_ms=elapsed_ms,
            sla_compliant=sla_compliant,
            model_version=ml_engine.model_version,
            decision_reasons=reasons,
            rules_triggered=rules_triggered,
            top_shap_factors=top_shaps
        )

        # 8. Despachar persistencia y actualización de contadores en background
        background_tasks.add_task(persist_audit_log_and_update_state, request, response)

        return response

    except Exception as e:
        logger.error(f"Error procesando transacción {request.transaction_id}: {str(e)}", exc_info=True)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        # Modo Fail-Secure regulatorio: en fallo catastrófico, requerir desafío 2FA para proteger fondos
        return DecisionResponse(
            transaction_id=request.transaction_id,
            decision=DecisionEnum.CHALLENGE_2FA,
            risk_score=0.50,
            risk_level=RiskLevelEnum.MEDIO,
            ml_score=0.50,
            rules_score=0.50,
            latency_ms=elapsed_ms,
            sla_compliant=elapsed_ms <= settings.SLA_LATENCY_THRESHOLD_MS,
            model_version=ml_engine.model_version,
            decision_reasons=["Mecanismo de salvaguarda (Fail-Secure) activado por contingencia del sistema."],
            rules_triggered=[],
            top_shap_factors=[]
        )
