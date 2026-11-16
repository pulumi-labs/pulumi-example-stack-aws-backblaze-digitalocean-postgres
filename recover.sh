#!/usr/bin/env bash
# Controller only. Use the read-only B2 key and the exact recorded snapshot ID.
set -euo pipefail
: "${RECOVERY_SSH:?Set a verified SSH host alias for the DigitalOcean VM}"
: "${SNAPSHOT_ID:?Set the full 64-character snapshot ID from successful backup}"
: "${RESTIC_REPOSITORY:?Set the original repository}"
: "${RESTIC_PASSWORD_FILE:?Set the original external repository password file}"
: "${B2_ACCOUNT_ID:?Set the short-lived read-only recovery key ID}"
: "${B2_ACCOUNT_KEY:?Set the short-lived read-only recovery key}"
[[ "$SNAPSHOT_ID" =~ ^[a-f0-9]{64}$ ]]
test "$(restic version | cut -d' ' -f2)" = '0.18.1'
# createdb fails if inventory already exists. No clean/overwrite shortcut is used.
ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ForwardAgent=no \
  "$RECOVERY_SSH" sudo docker exec --user postgres postgres \
  createdb --username=postgres inventory
restic --no-lock dump "$SNAPSHOT_ID" /inventory.dump |
  ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ForwardAgent=no \
    "$RECOVERY_SSH" sudo docker exec --interactive --user postgres postgres \
    pg_restore --username=postgres --dbname=inventory \
    --no-owner --no-acl --exit-on-error --single-transaction
