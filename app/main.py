"""
Punto de entrada de la aplicación FastAPI para Escudo Yuma.
Configura middlewares, enrutadores, CORS, consola web interactiva y documentación OpenAPI.
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.endpoints import decision, health, rules

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Escudo Yuma - Motor Antifraude en Tiempo Real
    Sistema de prevención de fraude pre-transaccional para la billetera digital **Yuma Pay** (SEDPE).

    ### Principales Capacidades:
    * **Decisión Pre-Transaccional en < 300 ms** (P99 < 15 ms).
    * **Hibridación** de Reglas Expertas de Alto Impacto + XGBoost ML.
    * **Explicabilidad SHAP** local factor a factor para auditoría y Ley 1581 / Habeas Data.
    * **Gestor Dinámico de Reglas Antifraude**: Creación, activación/desactivación y evaluación en caliente.
    * **Interfaz Web Interactiva**: Centro de control de operaciones y simulador PoC pre-cargado.
    * **100% Código Abierto** y conforme a normativas de la Superintendencia Financiera de Colombia (SFC) y SARLAFT.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusión de Rutas de API
app.include_router(health.router, tags=["Monitoreo & Salud"])
app.include_router(decision.router, prefix="/v1", tags=["Motor de Decisión"])
app.include_router(rules.router, prefix="/v1", tags=["Gestión de Reglas & Auditoría"])

# Cargar plantillas HTML interactivas
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def read_template(filename: str) -> str:
    path = os.path.join(TEMPLATES_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"<h2>Plantilla {filename} no encontrada.</h2>"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def hub_view():
    """Página principal de selección y vista en pantalla dividida (Split-Screen PoC)."""
    return HTMLResponse(content=read_template("hub.html"))


@app.get("/banco", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
def banco_view():
    """Simulador de la App Móvil / Billetera Digital Yuma Pay (Cliente)."""
    return HTMLResponse(content=read_template("banco.html"))


@app.get("/monitor", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def monitor_view():
    """Consola del Administrador y Monitor Antifraude con Notificaciones en Vivo."""
    return HTMLResponse(content=read_template("monitor.html"))
