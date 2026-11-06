FROM python:3.15-slim@sha256:8c13a3f37a6a5b71498228e902c4b9f51c1f7900d49fabf71f9a650c6120e0d0

WORKDIR /app

# Version, stamped by CI (see .build-container in .gitlab-ci.yml) — read at
# runtime by hannah_webui/version.py, exposed via the /version endpoint and
# the header badge. "dev" for local `docker build` without --build-arg.
ARG VERSION=dev
RUN echo "${VERSION#v}" > VERSION

# System packages: git is required for config backup/restore
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code
COPY main.py gunicorn.conf.py wsgi.py ./
COPY hannah_webui/ hannah_webui/

# Daten-Verzeichnis (wird als Volume gemountet) — hält u.a. das persistierte
# selbstsignierte TLS-Zertifikat (hannah_webui/tls.py, #61)
RUN useradd -r -u 1000 appuser \
    && mkdir -p /data \
    && chown appuser:appuser /data
VOLUME ["/data"]
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
