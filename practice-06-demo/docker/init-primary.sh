#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replicator';
EOSQL
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
