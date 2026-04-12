#!/bin/sh

set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
NPMW="$ROOT_DIR/scripts/npmw"

ensure_workspace_ready() {
  if [ ! -d "$ROOT_DIR/node_modules" ]; then
    echo "Root workspace dependencies missing. Running npm install..."
    "$NPMW" install
  fi
}

usage() {
  cat <<'EOF'
Usage: ./start.sh <command>

Commands:
  web                 Start the browser-based app on top of the app API
  web-bg              Start the browser-based app in the background
  app-api             Start the app API on 127.0.0.1:8000
  nutrition-service   Start the nutrition service on 127.0.0.1:8001
  mobile              Start the Expo mobile app
  all                 Start app API and nutrition service in background, then start Expo
  db:seed             Seed the local nutrition database
  test:python         Run the Python test suites
EOF
}

if [ "$#" -lt 1 ]; then
  usage
  exit 1
fi

cd "$ROOT_DIR"

case "$1" in
  web)
    "$NPMW" run web:start
    ;;
  web-bg)
    nohup sh "$ROOT_DIR/start.sh" web >/tmp/health-tech-web.log 2>&1 &
    echo "Web app started in background. Logs: /tmp/health-tech-web.log"
    ;;
  app-api)
    "$NPMW" run app-api:start
    ;;
  nutrition-service)
    "$NPMW" run nutrition-service:start
    ;;
  mobile)
    ensure_workspace_ready
    "$NPMW" run mobile:start
    ;;
  all)
    ensure_workspace_ready
    nohup sh "$ROOT_DIR/start.sh" app-api >/tmp/health-tech-app-api.log 2>&1 &
    nohup sh "$ROOT_DIR/start.sh" nutrition-service >/tmp/health-tech-nutrition-service.log 2>&1 &
    "$NPMW" run mobile:start
    ;;
  db:seed)
    "$NPMW" run db:seed
    ;;
  test:python)
    "$NPMW" run test:python
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $1" >&2
    usage
    exit 1
    ;;
esac
