# Maintaining cross-cloud PostgreSQL recovery

- Keep Python Pulumi and the pinned AWS, DigitalOcean and AnyTF B2 provider
  contracts. Generate and inspect the actual B2 SDK before changing resource
  names, input types or credential handling.
- Preserve separate source, encrypted backup and recovery phases. Never seed the
  recovery database or call file presence a successful restore.
- Keep cloud and B2 credentials outside workload VMs. Preserve strict SSH host
  verification, network isolation, client-side encryption and scoped key expiry.
- Keep complete dependency hashes, artifact pins and explicit release-age gates.
  Run providers, workloads and checks only in an approved scanned sandbox.
- Record actual passed, failed and unrun behavior separately. Live recovery and
  provider cleanup remain unrun until credentials and execution gates permit.
- Keep state, secret files, keys, private logs and research evidence out of this
  repository. Preserve encrypted state until owned cleanup is verified.
- Keep private review repositories private. Public release, license selection
  and shared account changes require applicable owner authorization.
