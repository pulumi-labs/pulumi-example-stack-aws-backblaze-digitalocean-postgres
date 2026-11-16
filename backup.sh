#!/usr/bin/env bash
# Controller only. B2 credentials and RESTIC_PASSWORD_FILE are supplied securely.
set -euo pipefail
umask 077
: "${SOURCE_SSH:?Set a verified SSH host alias for the AWS VM}"
: "${RESTIC_REPOSITORY:?Set the exact Pulumi resticRepository output}"
: "${RESTIC_PASSWORD_FILE:?Set an external mode-0600 repository password file}"
: "${B2_ACCOUNT_ID:?Set the short-lived bucket-scoped writer key ID}"
: "${B2_ACCOUNT_KEY:?Set the short-lived bucket-scoped writer key}"
test "$(restic version | cut -d' ' -f2)" = '0.18.1'
# --stdin-from-command refuses to commit a snapshot if SSH or pg_dump fails.
restic backup --json --host aws-postgres --tag postgres-logical \
  --stdin-filename inventory.dump --stdin-from-command -- \
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ForwardAgent=no \
  "$SOURCE_SSH" sudo docker exec --user postgres postgres \
  pg_dump --username=postgres --dbname=inventory --format=custom --no-owner --no-acl
