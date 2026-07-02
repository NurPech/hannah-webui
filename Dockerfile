FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1

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

# Daten-Verzeichnis (wird als Volume gemountet)
RUN useradd -r -u 1000 appuser
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
