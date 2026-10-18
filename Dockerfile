FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHUGCHUG_ONLINE=1 \
    CHUGCHUG_STATE_DIR=/data \
    PORT=8000

WORKDIR /app

RUN groupadd --system --gid 10001 chugchug \
    && useradd --system --uid 10001 --gid chugchug --home-dir /app chugchug \
    && mkdir -p /data \
    && chown chugchug:chugchug /data

COPY --chown=chugchug:chugchug chugchug/ /app/chugchug/
COPY --chown=chugchug:chugchug web/ /app/web/
COPY --chown=chugchug:chugchug dataset/reference/ /app/dataset/reference/
COPY --chown=chugchug:chugchug dataset/historical/ /app/dataset/historical/
COPY --chown=chugchug:chugchug dataset/incoming/ /app/dataset/incoming/
COPY --chown=chugchug:chugchug dataset/review_records/ /app/dataset/review_records/

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz', timeout=2).read()"

CMD ["python", "-m", "chugchug.server"]
