FROM python:3.12-slim

# 1. Instalamos UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. Configuración para instalar en SISTEMA (Evita el problema del volumen)
ENV UV_PROJECT_ENVIRONMENT="/usr/local"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# 3. Librerías del sistema
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 4. Instalación de dependencias
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# 5. Copiamos el código
COPY . .

EXPOSE 8000

# 6. Ejecutamos usando Python directo
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]