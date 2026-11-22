# Prompt para Google Antigravity / Gemini – Escudo Yuma

**Copia y pega el contenido a partir de la línea siguiente:**

---

Actúa como un Arquitecto de Soluciones Senior y Tech Lead experto en sistemas antifraude en tiempo real para fintechs. Debes diseñar e implementar el sistema **«Escudo Yuma»** para la billetera digital colombiana Yuma Pay.

**Restricción crítica e innegociable:**  
Usa **exclusivamente** herramientas de código abierto con licencias que permitan uso comercial libre (MIT, Apache 2.0, BSD, MPL, LGPL, etc.). Está prohibido proponer cualquier software propietario (no AWS Fraud Detector, no Google Vertex AI, no Databricks, no Snowflake, no Sift, no Feedzai, etc.).

### Contexto del problema

Yuma Pay es una billetera digital colombiana (SEDPE) con 4,2 millones de usuarios y aproximadamente 1,8 millones de transacciones diarias. Actualmente detecta el fraude **después** de que el dinero ya salió de la cuenta. El motor actual usa reglas estáticas y genera cerca de 4.000 alertas diarias con un **92 % de falsos positivos**. Hay alrededor de 2.300 fraudes confirmados al mes con pérdidas promedio de COP 1.150 millones mensuales.

Las modalidades de fraude más relevantes son:
- Toma de cuenta (phishing, smishing, falsos asesores)
- SIM swapping
- Cuentas mula (suplantación de identidad en vinculación)
- Engaños con códigos QR y comprobantes falsos
- Ingeniería social

**Requisitos no negociables del sistema:**
- Calificación de riesgo **antes de autorizar** la operación
- Latencia máxima de **300 milisegundos**
- Soportar picos de **150 transacciones por segundo**
- Combinar reglas + modelos de aprendizaje automático + análisis de comportamiento + dispositivo + redes de cuentas
- Cada decisión debe ser **explicable y auditable**
- Reducir los falsos positivos del 92 % a menos del 60 % sin aumentar el fraude que se deja pasar
- Un bloqueo definitivo de cuenta siempre requiere revisión de un analista
- Cumplir Ley 1581 de 2012, Ley 1266 de 2008, instrucciones de la Superintendencia Financiera y SARLAFT
- Desplegable en nube y contenedores

### Stack tecnológico obligatorio (solo Open Source)

| Capa                        | Tecnología recomendada                  | Licencia     |
|----------------------------|-----------------------------------------|--------------|
| API de decisión            | FastAPI + Uvicorn                       | MIT          |
| Feature Store en tiempo real | Redis o Dragonfly                     | BSD / Apache |
| Streaming de eventos       | Apache Kafka o Redpanda                 | Apache 2.0   |
| Machine Learning           | XGBoost + LightGBM + scikit-learn       | Apache 2.0   |
| Explicabilidad             | SHAP                                    | MIT          |
| Análisis de redes (grafo)  | NetworkX o Neo4j Community Edition      | BSD / GPL    |
| Model Registry             | MLflow                                  | Apache 2.0   |
| Observabilidad             | Prometheus + Grafana                    | Apache 2.0   |
| Contenedores               | Docker + Docker Compose                 | Apache 2.0   |
| Base de datos              | PostgreSQL + ClickHouse (opcional)      | Open Source  |
| Dashboard de analistas     | Streamlit o Gradio                      | Apache / MIT |

### Datos disponibles (sintéticos)

- `transacciones.csv` (~121.000 filas) con etiqueta `es_fraude` y `modalidad_fraude`
- `clientes.csv` (6.000 clientes)
- `eventos_app.csv` (~48.000 eventos de sesión, dispositivo, cambio de clave y SIM)
- `alertas.csv` (histórico del motor actual)
- `reglas_vigentes.csv` (12 reglas de línea base)

### Entregables que necesito que generes de forma completa y profesional

1. **Arquitectura detallada**
   - Diagrama textual o en formato Mermaid de la arquitectura completa
   - Descripción clara de cada componente y justificación de la elección tecnológica

2. **Diseño del Feature Store**
   - Lista completa de features de alto valor (incluyendo features de ventana, comportamiento, dispositivo y grafo)
   - Cómo se calculan en tiempo real (streaming) y en batch

3. **Diseño del modelo de Machine Learning**
   - Algoritmo recomendado y justificación
   - Estrategia de entrenamiento, manejo del desbalance de clases y métricas objetivo
   - Cómo combinar el score del modelo con el motor de reglas

4. **Motor de reglas en tiempo real**
   - Estructura recomendada
   - Lista de reglas prioritarias con su lógica

5. **Especificación completa de la API de decisión**
   - Endpoint principal `/v1/decision`
   - Request y Response completos (debe incluir: score, decisión, razones, explicación SHAP, versión del modelo y latencia)

6. **Flujo completo de una transacción**
   - Desde que el usuario confirma el envío hasta la respuesta final, con tiempos estimados por etapa

7. **Estructura de proyecto recomendada**
   - Árbol de carpetas y archivos sugerido

8. **Plan de implementación por fases** para una hackatón
   - Qué priorizar en el día 1, día 2 y día 3

9. **Código de ejemplo funcional** de:
   - Servicio de decisión en FastAPI (esqueleto listo para extender)
   - Cálculo de features básicas
   - Inferencia con XGBoost + explicación con SHAP

10. **Estrategia de despliegue**
    - Docker Compose completo y listo para levantar el sistema

### Formato de respuesta esperado

Responde de forma estructurada, profesional y lista para ser usada como base de implementación real del proyecto. Usa títulos claros, listas y bloques de código. Sé concreto y evita generalidades.

---

**Fin del prompt**
