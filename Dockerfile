# Multi-stage build para reducir tamaño y mejorar seguridad
FROM python:3.11-slim AS builder

# Instalar dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements primero para mejor cache
COPY requirements.txt .

# Instalar dependencias
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt


# Stage final - imagen limpia
FROM python:3.11-slim

# Metadatos de la imagen
LABEL maintainer="oscar.javier.alvarado@outlook.com" \
      version="1.0.0" \
      description="Provider Microservice Production Image"

# Variables de entorno para producción
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONPATH=/app \
    APP_ENV=production \
    PORT=8050

# Crear usuario no-root
RUN groupadd -r app -g 1001 && \
    useradd -r -u 1001 -g app -d /app -s /sbin/nologin app

WORKDIR /app

# Instalar solo runtime dependencies necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /usr/local

# Copiar código de la aplicación
COPY --chown=app:app . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /app/logs /app/tmp && \
    chown -R app:app /app && \
    chmod -R 755 /app

# Cambiar a usuario no-root
USER app

# Exponer puerto
EXPOSE ${PORT}

# Health check más robusto
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando optimizado para producción
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 4 --access-log"]