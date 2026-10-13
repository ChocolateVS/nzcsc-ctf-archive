#!/usr/bin/env bash
# Thin wrapper: regenerate a competition's compose then drive it.
#   ./manage.sh <comp> gen|up|build|down|restart|ps|logs [service...]
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
COMP="${1:?usage: manage.sh <comp> <gen|up|build|down|restart|ps|logs> [service...]}"
CMD="${2:-up}"
COMPOSE="$DIR/comps/$COMP/docker-compose.yml"
gen(){ python3 "$DIR/gen_compose.py" "$COMP"; }
case "$CMD" in
  gen)     gen ;;
  up)      gen; docker compose -f "$COMPOSE" up -d --build ;;
  apply)   gen; docker compose -f "$COMPOSE" up -d ;;   # regen (refreshes CF IPs) + apply, no rebuild
  build)   gen; docker compose -f "$COMPOSE" build ;;
  down)    docker compose -f "$COMPOSE" down ;;
  restart) gen; docker compose -f "$COMPOSE" up -d --build --force-recreate ;;
  ps)      docker compose -f "$COMPOSE" ps ;;
  logs)    shift 2 || true; docker compose -f "$COMPOSE" logs -f "$@" ;;
  *)       echo "unknown command: $CMD" >&2; exit 1 ;;
esac
