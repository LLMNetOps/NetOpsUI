# Manager service: skill library, agent profiles, read-only config views.
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./

ENV DATA_DIR=/data/netopsui \
    NETOPS_AGENT_HOME=/data/netops \
    HERMES_HOME=/data/hermes \
    MANAGER_PORT=8200

# Loopback only: nginx (same host network) is the sole way in.
CMD ["sh", "-c", "exec uvicorn main:app --host 127.0.0.1 --port ${MANAGER_PORT}"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/api/health' % os.environ['MANAGER_PORT'], timeout=2)" || exit 1
