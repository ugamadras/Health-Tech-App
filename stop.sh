#!/bin/sh

set -eu

usage() {
  cat <<'EOF'
Usage: ./stop.sh <command>

Commands:
  web                 Stop the browser-based app API process
  app-api             Stop the app API
  nutrition-service   Stop the nutrition service
  mobile              Stop Expo if it was started from this project
  all                 Stop app API, nutrition service, and Expo
EOF
}

stop_pattern() {
  pattern="$1"
  if pkill -f "$pattern" 2>/dev/null; then
    echo "Stopped: $pattern"
  else
    echo "Not running: $pattern"
  fi
}

if [ "$#" -lt 1 ]; then
  usage
  exit 1
fi

case "$1" in
  web)
    stop_pattern "scripts/run_app_api.py"
    ;;
  app-api)
    stop_pattern "scripts/run_app_api.py"
    ;;
  nutrition-service)
    stop_pattern "scripts/run_nutrition_service.py"
    ;;
  mobile)
    stop_pattern "expo start"
    ;;
  all)
    stop_pattern "scripts/run_app_api.py"
    stop_pattern "scripts/run_nutrition_service.py"
    stop_pattern "expo start"
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
