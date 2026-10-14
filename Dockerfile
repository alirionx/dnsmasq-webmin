# syntax=docker/dockerfile:1

# --- Stage 1: build the Vue SPA ------------------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: install Python dependencies into a venv -------------------------
FROM python:3.12-alpine AS backend
WORKDIR /src
COPY pyproject.toml ./
# dependencies are taken from pyproject.toml (single source of truth); the app
# itself is not installed as package, it is copied into the runtime image
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']))" > requirements.txt \
 && python -m venv /venv \
 && /venv/bin/pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# --- Stage 3: runtime ------------------------------------------------------------
FROM python:3.12-alpine
RUN addgroup -S -g 10001 app && adduser -S -u 10001 -G app -h /app app \
 && mkdir -p /data /etc/dnsmasq.d && chown app:app /data /etc/dnsmasq.d

COPY --from=backend /venv /venv
COPY app/ /app/app/
COPY --from=frontend /src/dist/ /app/frontend/dist/

ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=5000 \
    DNSMASQ_WEBMIN_CONF_DIR=/etc/dnsmasq.d \
    DNSMASQ_WEBMIN_DB_PATH=/data/db.json

WORKDIR /app
USER app
VOLUME ["/data", "/etc/dnsmasq.d"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -q -O /dev/null "http://127.0.0.1:${APP_PORT}/api/service" || exit 1

CMD ["python", "-m", "app.main"]
