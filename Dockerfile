# Multi-stage build para reducir tamaño y mejorar seguridad
FROM python:3.11-alpine AS builder

# Instalar dependencias de compilación
RUN apk add --no-cache \
    gcc \
    libffi-dev \
    linux-headers \
    musl-dev
WORKDIR /app

# Copiar requirements primero para mejor cache
COPY requirements.txt .

# Instalar dependencias en directorio temporal
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt


# Stage final - imagen limpia
FROM python:3.11-alpine

# Metadatos de la imagen
LABEL maintainer="oscar.javier:alvarado@outlook.com" \
      version="1.0.0" \
      description="Provider Microservice Production Image"

# Variables de entorno para producción
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=on \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONPATH=/app \
    APP_ENV=production \
    PORT=8050

# Crear usuario no-root con shell falso
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app --home /app --shell /sbin/nologin app

WORKDIR /app

# Instalar solo runtime dependencies necesarias
RUN apk add --no-cache \
    libstdc++ \
    curl \
    && rm -rf /var/cache/apk/*

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /usr/local

# Copiar código de la aplicación
COPY --chown=app:app . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /app/logs /app/tmp && \
    chown -R app:app /app/logs /app/tmp && \
    chmod -R 750 /app/logs /app/tmp

# Cambiar a usuario no-root
USER app

# Exponer puerto
EXPOSE ${PORT}

# Health check más robusto
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Comando optimizado para producción
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 4 --access-log"]