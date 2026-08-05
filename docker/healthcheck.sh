#!/bin/sh
# Docker HEALTHCHECK for the xavani container (F03).
# PID 1 must be alive; when a status port is configured, /health must answer.
if ! kill -0 1 2>/dev/null; then
  exit 1
fi
if [ -n "${XAVANI_PROMETHEUS_PORT}" ]; then
  curl -fsS "http://127.0.0.1:${XAVANI_PROMETHEUS_PORT}/health" >/dev/null 2>&1 || exit 1
fi
exit 0
