FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias de compilación para C++/SHAP/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponer puerto de FastAPI
EXPOSE 8000

# Ejecutar con Uvicorn multi-worker para alta concurrencia (150+ TPS)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
