#!/bin/bash
set -e
PGDATA=/var/lib/postgresql/data
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  until pg_basebackup -h primary -U replicator -D "$PGDATA" -R -X stream; do
    echo "waiting for primary..."
    rm -rf "${PGDATA:?}"/*
    sleep 2
  done
  chmod 0700 "$PGDATA"
fi
exec postgres -D "$PGDATA" -c hot_standby=on -c recovery_min_apply_delay=2s
