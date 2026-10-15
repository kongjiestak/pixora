FROM node:22-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml requirements-lock.txt ./
COPY apm/ ./apm/
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt && pip install --no-cache-dir --no-deps . && useradd -u 10001 -m apm && mkdir /data && chown apm /data
COPY --from=web /web/dist ./web/dist
ENV APM_DB=/data/apm.sqlite
USER apm
EXPOSE 8000
CMD ["uvicorn", "apm.server:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
