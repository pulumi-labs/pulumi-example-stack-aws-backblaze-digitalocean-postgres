# PostgreSQL on AWS, encrypted B2 backup, recovery on DigitalOcean

This Python Pulumi example gives an operator a small inventory SQL workload on
an AWS VM, a client-side encrypted PostgreSQL logical backup in Backblaze B2,
and a separate DigitalOcean VM that reads and writes the recovered records.
There is no EKS or Kubernetes dependency.

**Validation on November 16, 2026: deployment, SQL workload, encrypted backup,
cross-cloud restore and data comparison are UNRUN.** Installed AWS, DigitalOcean
and generated B2 SDK contracts, complete infrastructure hash lock, native syntax,
strict lint and type checks passed in an approved disposable VM. Source and
reviewed SDK artifacts passed malware scans. Application image acquisition,
provider credentials, preview and live recovery remain gated. This is a private
source review draft, not a recovery pass.

Private review repository: `pulumi-labs/pulumi-example-stack-aws-backblaze-digitalocean-postgres`.

```sh
git clone https://github.com/pulumi-labs/pulumi-example-stack-aws-backblaze-digitalocean-postgres.git
cd pulumi-example-stack-aws-backblaze-digitalocean-postgres
```

The phases are deliberately separate. Initial `pulumi up` creates only AWS and
B2 infrastructure. The operator starts PostgreSQL, writes actual SQL records and
takes the backup. Only then does `enableRecovery=true` add DigitalOcean resources.
`recover.sh` reads the exact recorded encrypted restic snapshot into pg_restore;
it never seeds the recovery database. The acceptance contract compares full
records and a unique nonce before making new writes against recovery.

## Architecture and exposure

AWS owns one t3.small VM, encrypted 12 GiB gp3 root disk, a small VPC, public
subnet, internet gateway, route table, security group and ephemeral SSH public
key registration. Only SSH from one approved controller IPv4 /32 is allowed.
The guest has no AWS role or cloud credentials. IMDSv2 is required.

B2 owns one allPrivate bucket and a one-hour, bucket/prefix-scoped restic writer
key. Recovery adds an independent read-only one-hour key. AnyTF bridges the
official Backblaze Terraform provider; no published native Python B2 package was
found at the inspected PyPI endpoint. Missing native packaging is not a provider
eligibility failure.

DigitalOcean owns one s-1vcpu-1gb VM, SSH public key, tag and firewall. The firewall
exists before the tagged VM. The parent's verified standard Ubuntu 24.04 x64
image ID and region are required inputs. Automatic provider backups, monitoring
and guest console agent installation are disabled.

Neither VM publishes a PostgreSQL port. PostgreSQL runs with network=none and
listens only on a private Unix socket. SSH-authenticated sudo/docker exec as the
postgres OS user is the SQL access boundary. This example intentionally provides
an operator SQL workload rather than an unauthenticated web application.
Guest egress permits HTTPS and DNS; artifacts are staged by the controller using
SSH. There are no floating installers in cloud-init.

restic 0.18.1 encrypts and authenticates the logical archive before B2 upload.
The repository password is generated and retained separately from B2 credentials
in the parent's secret store. No B2 credential or repository password enters
either workload VM, cloud-init or Pulumi configuration. Dump bytes stream from
AWS over authenticated SSH through restic; recovery streams decrypted bytes
directly to DO pg_restore. The approved controller can see plaintext in memory.
Encrypted disk/state, SSH trust and the controller's isolation remain necessary.

## Pins and acquisition

`artifacts.json` contains exact tool URLs, hashes, Docker package pins and the
Linux AMD64 PostgreSQL image. `requirements.lock` contains the complete
resolver-generated infrastructure closure for CPython 3.12, Linux x86_64.

| Component | Exact version |
| --- | --- |
| Pulumi CLI and Python SDK | 3.273.0 |
| AWS provider SDK/plugin | 7.52.1 |
| DigitalOcean provider SDK/plugin | 4.84.1 |
| AnyTF bridge plugin | 1.4.0 |
| Backblaze Terraform provider | 0.14.1 |
| restic | 0.18.1 |
| Docker engine/CLI | 28.5.1 |
| containerd.io | 1.7.28 |
| PostgreSQL | 17.12-bookworm, pinned Linux AMD64 digest in artifacts.json |

PostgreSQL 17.12 includes the November 12 security fixes. Its image reaches the
four-day release-age threshold on November 16, 2026 at 22:16:19 UTC; earlier
execution requires the owner's explicit waiver. No waiver or scan coverage is
claimed. The Linux AMD64 image matches both selected VM architectures and
includes matching pg_dump/pg_restore tools on both clouds.

The parent must acquire and scan these exact archives/wheels/image bytes inside
the approved VM, reuse matching cached bytes where possible, resolve/lock the
standard OS dependency closure and verify signatures/signed package indexes.
No host install, import, test, build, preview or provider execution is permitted.
No custom OS image is needed.

Generate the B2 SDK only after both bridge/provider archives have matching
complete scan evidence, inside the approved controller:

```sh
pulumi package gen-sdk terraform-provider@1.4.0 \
  --language python --local --out sdks/b2 -- \
  registry.opentofu.org/backblaze/b2 0.14.1
```

The pinned CLI's gen-sdk command writes the Python SDK to `sdks/b2/python`.
Inspect its actual Bucket, ApplicationKey, Provider and input/output signatures.
Hash and scan generated runnable files before importing them. Then install the
reviewed local SDK into the locked environment using the parent's approved uv
path, with dependency installation disabled after its real metadata is checked.
It is deliberately not checked in with fabricated generated bytes or hashes.
Generate/lock any newly declared dependencies before proceeding if they differ
from requirements.lock. Native SDK generation, schema serialization and imports
remain an explicit external prerequisite.

Create `.venv` with CPython 3.12 and install the exact hash-checked wheel closure
with uv, `--only-binary :all:` and `--require-hashes -r requirements.lock`.
Install the scanned generated SDK locally with `--no-deps --no-build-isolation`
after reviewing its build requirements. Do not allow Pulumi to resolve a newer
provider or regenerate packages implicitly during deployment. Confirm plugin
inventory, actual imports, native argument serialization, Bash syntax, SQL and
manifest parsing in the approved VM before preview. If the SDK generates
different names or types, correct the source and repeat only the affected checks.

## Accounts, state and configuration

Parent-owned prerequisites: AWS, B2 and DigitalOcean account access, secure
credential-file references, signup permission if needed, verified execution VM,
budget reconciliation and absolute UTC test-stop/cleanup deadlines. This source
does not read account credentials or create accounts. No paid subscription,
public release, research commit or polished export is authorized.

Use short-lived AWS STS provisioning credentials scoped to the owned EC2 instance,
network, security group, volume, key pair and tags plus necessary Describe calls.
No IAM resources are created. Use an expiring DigitalOcean token with the read,
create and delete operations for Droplets, firewalls, SSH keys and tags, firewall
update, and read-only images/regions/sizes/VPC discovery. Scope it to the relevant
team/project where supported; verify actual current token scope names with the
parent before use.

The B2 provisioning identity needs list/read/create/update/delete access for
owned buckets and list/create/delete application keys. Keep it only in the
approved controller. The native provider reads B2_APPLICATION_KEY_ID and
B2_APPLICATION_KEY. restic uses the different names B2_ACCOUNT_ID and
B2_ACCOUNT_KEY. The runtime issues writer capabilities listBuckets/listFiles/
readFiles/writeFiles/deleteFiles for one bucket and postgres/ prefix; delete is
needed for locks and repository maintenance. Reader capabilities are listBuckets/
listFiles/readFiles and recovery uses --no-lock. Expired application keys must
be replaced by the parent through an inspected Pulumi plan; do not extend a test
deadline to work around expiration.

Use encrypted Pulumi state outside the repository and keep its encryption key
outside the guests. Use a dedicated ephemeral SSH key with no forwarded agent;
only its public half is Pulumi config. Example configuration below is a command
sequence whose shell variables are supplied by the parent, not literal values:

```sh
pulumi stack init recovery-demo
pulumi config set aws:region "$AWS_REGION"
pulumi config set operatorCidr "$CONTROLLER_IPV4_CIDR"
pulumi config set sshPublicKey "$EPHEMERAL_SSH_PUBLIC_KEY"
pulumi config set sourceAmi "$VERIFIED_STANDARD_UBUNTU_AMI"
pulumi config set bucketName "$UNIQUE_PRIVATE_B2_BUCKET_NAME"
pulumi config set enableRecovery false
pulumi config set protectData true
pulumi preview --diff
# Parent inspects exact resource, firewall, replacement and cost diffs first.
pulumi up
```

Keep provider credentials in the approved environment, not argv/config/user-data.
Secret outputs writerKeyId/writerKey and readerKeyId/readerKey may be securely
read by the parent into an external mode-0600 file or secret store; never print
them to logs or commit them. No state or credentials belong in this directory.

## Source, backup and recovery

On both VMs the parent stages the exact scanned Docker packages and PostgreSQL
image with standard dpkg/apt and docker load. Include required OS packages from
the parent's reviewed lock, use no recommends, no floating apt upgrade and no
automatic image pull. start-postgres.sh checks Docker 28.5.1 and the local image.
Run it through a verified SSH alias with `sudo bash -s`, not by making a public
database port. It refuses an existing data directory and waits at most 60 seconds.
Startup failure leaves data for diagnosis; do not erase a database to retry.

Create the inventory database and write the workload on AWS. A minimal useful
SQL session is:

```sh
ssh "$SOURCE_SSH" sudo docker exec --user postgres postgres createdb -U postgres inventory
ssh "$SOURCE_SSH" sudo docker exec -i --user postgres postgres \
  psql -X -U postgres -d inventory -v ON_ERROR_STOP=1 < inventory.sql
ssh "$SOURCE_SSH" sudo docker exec -i --user postgres postgres \
  psql -X -U postgres -d inventory -v ON_ERROR_STOP=1
```

Enter real SQL inserts/updates in that session. The research run's
separate acceptance assets supply a small inventory workload and nonce, rather
than mixing test fixtures into the runtime. Only source receives seed SQL.
Quiesce writes while capturing the baseline and backup.

Generate a random strong repository password once in an external mode-0600 file.
Set RESTIC_REPOSITORY to the exact resticRepository output, RESTIC_PASSWORD_FILE
to that file and the restic B2 variables to the expiring writer key. Initialize
once with `restic init`, then:

```sh
bash backup.sh > "$PRIVATE_EVIDENCE_DIRECTORY/backup.jsonl"
restic check --read-data
```

Require exit zero and save the full snapshot_id from the successful JSON summary.
The native --stdin-from-command option rejects a failed pg_dump or SSH session
instead of committing an empty successful snapshot. The backup contains one
custom-format inventory.dump. Roles/global settings are intentionally outside
this single-database SQL workload; pg_restore uses --no-owner --no-acl.

Keep source stopped for recovery acceptance. Enable the DO phase:

```sh
pulumi config set recoveryImageId "$VERIFIED_STANDARD_DO_IMAGE_ID"
pulumi config set recoveryRegion "$DO_REGION"
pulumi config set enableRecovery true
pulumi preview --refresh --diff
pulumi up
```

Start the blank DO PostgreSQL server, set RECOVERY_SSH to its verified alias,
switch restic credentials to the reader key and set SNAPSHOT_ID to the saved
64-character ID. Keep the original repository and password:

```sh
bash recover.sh
```

createdb refuses an existing inventory database. pg_restore runs with
--exit-on-error --single-transaction and pipefail detects either stream failure.
A failure leaves a blank or rolled-back database for investigation; rebuilding
an approved disposable target is an explicit parent decision, not an automatic
retry that destroys data. Source runtime never seeds or contacts recovery.

Query all restored records, compare their canonical ordered representation with
the pre-backup source baseline and require the same unique nonce. Then insert a
new row and update a recovered row on DO. The research acceptance contract gives
exact commands and verifies the restored identity sequence continues correctly.
A snapshot ID, downloaded file, row count or server-ready result is insufficient.

## Protection, cost and cleanup

protectData defaults true for the source VM, recovery VM and B2 bucket. Changes
that replace/delete them fail until the parent deliberately changes protection.
AWS root volume encryption is enabled. DO's standard disk protection remains the
provider's contract; no customer-managed DO disk key is claimed. The B2 backup is
client-side encrypted regardless of provider storage encryption. No Object Lock,
automatic retention, lifecycle expiry or scheduled backup is enabled. Do not set
short per-object lifecycle expiration on a restic repository: it can corrupt
retained snapshots. Backups persist until explicitly deleted.

The shared cap is $50 per UTC calendar week, Monday through Sunday. The parent
reported estimated/delayed zero new-week usage and retains a $4 prior-retry
reserve. Neither is a final bill or permission to spend the remainder. Price the
chosen AWS region/DO size, public IPv4, disk, controller, B2 storage/API/downloads
and cleanup reserve before applying; no current price is asserted here. Use only
small synthetic records and a short bounded run. This is a single-node source,
not HA, continuous replication or point-in-time recovery. RPO is the last
successful logical dump; RTO and throughput are unmeasured.

At success, failure, cancellation or the test-stop deadline, the parent:

1. Exports sanitized SQL comparison assertions, exact source/runtime hashes,
   snapshot ID, resource IDs, times and all mixed/unrun results outside guests.
2. Stops source/recovery workload processes. Keeps encrypted state, password and
   provisioning/cleanup access until independent cleanup is complete.
3. Explicitly authorizes irreversible destruction of the sample data and backups.
   Reviews B2 file versions, hides/delete markers and unfinished large uploads
   for this owned bucket. Uses the standard B2 console/native tools to delete
   **all versions** and cancel unfinished uploads. A current-file hide or restic
   forget alone does not empty a versioned B2 bucket. No automatic force-delete
   helper or Object Lock bypass is provided.
4. Sets protectData=false, reviews/applies that protection change, then runs
   `pulumi destroy` from the approved controller. If an expired runtime key
   cannot clean up, uses the parent's provisioning identity; never broadens
   guest permissions. A nonempty bucket must fail deletion visibly.
5. Independently inventories owned AWS instance/EBS/network/key resources,
   DigitalOcean VM/firewall/tag/SSH-key resources and B2 buckets/versions/uploads/
   application keys. Includes any parent-created controller and temporary access
   artifacts. Deletes only owned disposable resources; records billable
   remainders, billing delay and remediation instead of calling them cleaned up.
6. Revokes remaining temporary tokens and SSH keys, deletes private credential
   files and plaintext evidence as appropriate, and removes encrypted state only
   after verified cleanup. Repository password loss prevents recovery.

If SDK generation, scanned artifact staging, B2/DO signup/credentials, VM approval
or cleanup access is unavailable, stop before paid deployment. Those prerequisites
are external, and no live result has been fabricated for them.

## License

This example's authored code is licensed under the [MIT License](LICENSE) and
is provided as-is, without warranty or a support commitment. Third-party
components retain their own licenses and notices.
