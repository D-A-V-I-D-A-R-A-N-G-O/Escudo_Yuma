"""
Motor de evaluación de reglas en tiempo real para Escudo Yuma.
Ejecuta el catálogo de reglas de forma ultraveloz (< 2 ms) y soporta
gestión dinámica en caliente de reglas personalizadas creadas por analistas.
"""

from typing import Dict, List, Tuple, Optional, Any
from app.schemas.decision import RuleEvaluationDetail, DecisionEnum
from app.rules.catalog import RULES_CATALOG, FraudRule, DynamicRule


class RulesEngine:
    def __init__(self, rules: List[FraudRule] = None):
        self.rules: List[FraudRule] = list(rules) if rules else list(RULES_CATALOG)

    def evaluate(self, features: Dict[str, float]) -> Tuple[float, Optional[DecisionEnum], List[RuleEvaluationDetail]]:
        """
        Evalúa todas las reglas activas.
        Retorna:
            - rules_score: float entre 0.0 y 1.0
            - hard_decision: DecisionEnum si alguna regla dura se activó (o None)
            - triggered_rules: Lista con los detalles de las reglas disparadas
        """
        triggered_rules: List[RuleEvaluationDetail] = []
        hard_decisions: List[DecisionEnum] = []
        soft_scores: List[float] = []

        for rule in self.rules:
            if not getattr(rule, "active", True):
                continue

            if rule.evaluate(features):
                detail = RuleEvaluationDetail(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    rule_type=rule.rule_type,
                    description=rule.description,
                    impact_score=rule.weight
                )
                triggered_rules.append(detail)

                if rule.forced_decision is not None:
                    hard_decisions.append(rule.forced_decision)
                else:
                    soft_scores.append(rule.weight)

        # Determinar si hay decisión forzada por regla dura
        forced_decision: Optional[DecisionEnum] = None
        if DecisionEnum.RECHAZADA_PREVENTIVA in hard_decisions:
            forced_decision = DecisionEnum.RECHAZADA_PREVENTIVA
        elif DecisionEnum.REVISION_MANUAL in hard_decisions:
            forced_decision = DecisionEnum.REVISION_MANUAL
        elif DecisionEnum.CHALLENGE_2FA in hard_decisions:
            forced_decision = DecisionEnum.CHALLENGE_2FA

        # Calcular score acumulado de reglas
        if not soft_scores and not hard_decisions:
            rules_score = 0.05
        else:
            base_score = 0.90 if forced_decision == DecisionEnum.RECHAZADA_PREVENTIVA else 0.0
            soft_contribution = sum(soft_scores) / max(1.0, len([r for r in self.rules if getattr(r, "active", True)]) * 0.4)
            rules_score = min(1.0, max(base_score, soft_contribution))

        return rules_score, forced_decision, triggered_rules

    def add_custom_rule(
        self,
        rule_id: str,
        name: str,
        rule_type: str,
        field: str,
        operator: str,
        threshold: float,
        weight: float,
        description: str,
        forced_decision: Optional[DecisionEnum] = None
    ) -> DynamicRule:
        """Agrega una regla personalizada en caliente."""
        # Evitar duplicados por ID
        self.rules = [r for r in self.rules if r.rule_id != rule_id]

        new_rule = DynamicRule(
            rule_id=rule_id,
            name=name,
            rule_type=rule_type,
            field=field,
            operator=operator,
            threshold=threshold,
            weight=weight,
            description=description,
            forced_decision=forced_decision,
            active=True
        )
        self.rules.append(new_rule)
        return new_rule

    def delete_rule(self, rule_id: str) -> bool:
        """Elimina una regla por su ID."""
        initial_len = len(self.rules)
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        return len(self.rules) < initial_len

    def toggle_rule(self, rule_id: str, active: Optional[bool] = None) -> Optional[bool]:
        """Activa o desactiva una regla."""
        for r in self.rules:
            if r.rule_id == rule_id:
                if active is None:
                    r.active = not getattr(r, "active", True)
                else:
                    r.active = active
                return r.active
        return None

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """Retorna el listado completo de reglas con sus metadatos y estado."""
        return [r.to_dict() for r in self.rules]


# Instancia singleton del motor de reglas
rules_engine = RulesEngine()
