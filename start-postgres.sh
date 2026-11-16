#!/usr/bin/env bash
# Run as root inside each approved workload VM after scanned artifacts are staged.
set -euo pipefail
umask 077
readonly image='docker.io/library/postgres@sha256:99d1a998c76487d3abb48b141505bda5dcf8089c0c4cd7be40f75de314fa32f0'
test "$(docker version --format '{{.Server.Version}}')" = '28.5.1'
docker image inspect "$image" >/dev/null
# mkdir intentionally fails on an existing data directory. Recovery must start empty.
mkdir /var/lib/postgres-example
head -c 48 /dev/urandom | base64 > /var/lib/postgres-example/password
# The file's parent stays root-only; the image drops to its postgres UID.
chmod 444 /var/lib/postgres-example/password
mkdir /var/lib/postgres-example/data
docker run --detach --name postgres --restart unless-stopped \
  --pull never --network none --memory 512m --cpus 1 --pids-limit 256 \
  --security-opt no-new-privileges:true \
  --log-opt max-size=5m --log-opt max-file=2 \
  --mount type=bind,src=/var/lib/postgres-example/data,dst=/var/lib/postgresql/data \
  --mount type=bind,src=/var/lib/postgres-example/password,dst=/run/db-password,readonly \
  --env POSTGRES_PASSWORD_FILE=/run/db-password \
  --env POSTGRES_HOST_AUTH_METHOD=scram-sha-256 \
  "$image" -c listen_addresses='' -c unix_socket_permissions=0700
for attempt in {1..30}; do
  if docker exec --user postgres postgres pg_isready -U postgres -d postgres >/dev/null; then
    exit 0
  fi
  sleep 2
done
printf 'PostgreSQL readiness exceeded 60 seconds\n' >&2
exit 1
