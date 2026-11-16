# PostgreSQL on AWS, encrypted B2 backup, recovery on DigitalOcean

Practice recovering a small PostgreSQL database onto a different cloud. You
create a sample inventory database on AWS, encrypt its backup into Backblaze B2,
and restore that backup onto a new DigitalOcean server. The final check is that
the restored records match and you can write new data there.

Pulumi creates the cloud resources using Python. PostgreSQL stores the records;
restic encrypts the backup before uploading it. B2 is object storage, where the
encrypted backup files live. This uses two virtual machines (VMs), not Kubernetes.

**Validation on November 16, 2026: deployment, SQL workload, encrypted backup,
cross-cloud restore and data comparison are UNRUN.** Installed AWS, DigitalOcean
and generated B2 SDK contracts, complete infrastructure hash lock, native syntax,
strict lint and type checks passed in an approved disposable VM. Source and
reviewed SDK artifacts passed malware scans. Application image acquisition,
provider credentials, preview and live recovery remain gated. This is a private
source review draft, not a recovery pass.

## Before you begin

This is a private source-review draft. A real backup and restore have **not**
been demonstrated yet. Use disposable sample data only. You need:

- Authorized AWS, Backblaze B2 and DigitalOcean accounts with the permissions below.
- An approved isolated Linux deployment environment with Python 3.12, the pinned
  Pulumi tools, SSH, restic and an encrypted Pulumi state backend. State records
  the resources Pulumi manages. Keep it outside Git.
- A dedicated SSH key and verified Ubuntu image IDs for both clouds.
- A private place to keep the backup password. Losing it makes the backup unreadable.
- A budget and a cleanup deadline: both servers and stored backups can incur charges.

Follow the steps in order. The AWS database must contain real sample records
before you back it up; the DigitalOcean database must start empty.

## 1. Get the example

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

## How it works

AWS owns one t3.small VM, encrypted 12 GiB gp3 root disk, a small VPC, public
subnet, internet gateway, route table, security group and ephemeral SSH public
key registration. Only SSH from one approved controller IPv4 /32 is allowed.
The guest has no AWS role or cloud credentials. IMDSv2 is required.

B2 holds one private bucket and a one-hour writer key restricted to this backup
location. Recovery adds a separate, read-only one-hour key. The AnyTF bridge lets
Pulumi use the official Backblaze Terraform provider, so you generate its Python
SDK before deployment. An SDK is the library used by the infrastructure program.

DigitalOcean owns one s-1vcpu-1gb VM, SSH public key, tag and firewall. The firewall
exists before the tagged VM. Your verified standard Ubuntu 24.04 x64
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
in your secret store. No B2 credential or repository password enters
either workload VM, cloud-init or Pulumi configuration. Dump bytes stream from
AWS over authenticated SSH through restic; recovery streams decrypted bytes
directly to DO pg_restore. The approved controller can see plaintext in memory.
Encrypted disk/state, SSH trust and the controller's isolation remain necessary.

## 2. Prepare the exact tools

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

Acquire and scan these exact archives/wheels/image bytes inside
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
reviewed local SDK into the locked environment using your approved uv
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

## 3. Configure accounts and create the AWS source

Have your cloud administrator confirm the account permissions before proceeding.
Keep provider tokens in the deployment environment's secret store. The example
does not create accounts, purchase plans or configure credentials for you.

Use short-lived AWS STS provisioning credentials scoped to the owned EC2 instance,
network, security group, volume, key pair and tags plus necessary Describe calls.
No IAM resources are created. Use an expiring DigitalOcean token with the read,
create and delete operations for Droplets, firewalls, SSH keys and tags, firewall
update, and read-only images/regions/sizes/VPC discovery. Scope it to the relevant
team/project where supported; verify actual current token scope names with the
account administrator before use.

The B2 provisioning identity needs list/read/create/update/delete access for
owned buckets and list/create/delete application keys. Keep it only in the
approved controller. The native provider reads B2_APPLICATION_KEY_ID and
B2_APPLICATION_KEY. restic uses the different names B2_ACCOUNT_ID and
B2_ACCOUNT_KEY. The runtime issues writer capabilities listBuckets/listFiles/
readFiles/writeFiles/deleteFiles for one bucket and postgres/ prefix; delete is
needed for locks and repository maintenance. Reader capabilities are listBuckets/
listFiles/readFiles and recovery uses --no-lock. Expired application keys must
be replaced by the operator through an inspected Pulumi plan; do not extend a test
deadline to work around expiration.

Use encrypted Pulumi state outside the repository and keep its encryption key
outside the guests. Use a dedicated ephemeral SSH key with no forwarded agent;
only its public half is Pulumi config. Example configuration below is a command
sequence. Set its shell variables from your account inventory first:

| Variable | Value to supply |
| --- | --- |
| `AWS_REGION` | Your selected AWS region |
| `CONTROLLER_IPV4_CIDR` | The deployment environment's approved public IPv4 followed by `/32` |
| `EPHEMERAL_SSH_PUBLIC_KEY` | Public half of your dedicated SSH key |
| `VERIFIED_STANDARD_UBUNTU_AMI` | Verified standard Ubuntu AMD64 image ID in that AWS region |
| `UNIQUE_PRIVATE_B2_BUCKET_NAME` | A new, unique bucket name for this example |

`pulumi preview` shows the proposed changes; `pulumi up` creates billable
resources. Review the account, firewall rules and costs before accepting:

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
read into an external owner-readable-only (mode `0600`) file or secret store; never print
them to logs or commit them. No state or credentials belong in this directory.

## 4. Start PostgreSQL and add sample records

On each VM, stage the exact scanned Docker packages and PostgreSQL image using
standard dpkg/apt and docker load. Include the reviewed OS package dependencies,
use no recommends, no floating apt upgrade and no
automatic image pull. start-postgres.sh checks Docker 28.5.1 and the local image.
Run it through a verified SSH alias with `sudo bash -s`, not by making a public
database port. It refuses an existing data directory and waits at most 60 seconds.
Startup failure leaves data for diagnosis; do not erase a database to retry.

`SOURCE_SSH` is an SSH host alias for the AWS VM, configured with your dedicated
key and a verified host fingerprint. After staging the packages and image, run
from the deployment environment:

```sh
ssh "$SOURCE_SSH" sudo bash -s < start-postgres.sh
```

This starts a new PostgreSQL container. It deliberately refuses an existing
data directory, so run it only on the new, empty source server.

Create the inventory database and write the workload on AWS. A minimal useful
SQL session is:

```sh
ssh "$SOURCE_SSH" sudo docker exec --user postgres postgres createdb -U postgres inventory
ssh "$SOURCE_SSH" sudo docker exec -i --user postgres postgres \
  psql -X -U postgres -d inventory -v ON_ERROR_STOP=1 < inventory.sql
ssh "$SOURCE_SSH" sudo docker exec -i --user postgres postgres \
  psql -X -U postgres -d inventory -v ON_ERROR_STOP=1
```

The last command opens an interactive PostgreSQL session. Enter these statements
there to create a small dataset and a unique recovery marker:

```sql
INSERT INTO recovery_marker (run_id) VALUES ('beginner-demo-001');
INSERT INTO products (sku, quantity, price, note)
VALUES ('workbook', 7, 12.50, 'before backup');
INSERT INTO movements (product_id, delta)
SELECT id, 7 FROM products WHERE sku = 'workbook';
SELECT * FROM recovery_marker ORDER BY run_id;
SELECT * FROM products ORDER BY id;
SELECT * FROM movements ORDER BY id;
```

Use a fresh marker for each trial. Save the complete query results privately as
your baseline, then leave the session with `\q`. Stop other writes while making
the backup. Add sample data only on AWS; never insert the sample again on the
recovery server, or you would not be testing recovery.

## 5. Encrypt and store the backup

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

## 6. Restore onto DigitalOcean

Stop the source database after saving the baseline and backup, so a successful
read cannot accidentally come from the original server:

```sh
ssh "$SOURCE_SSH" sudo docker stop postgres
```

Set `VERIFIED_STANDARD_DO_IMAGE_ID` to the verified standard Ubuntu AMD64 image
ID and `DO_REGION` to the selected DigitalOcean region. Enable the recovery phase:

```sh
pulumi config set recoveryImageId "$VERIFIED_STANDARD_DO_IMAGE_ID"
pulumi config set recoveryRegion "$DO_REGION"
pulumi config set enableRecovery true
pulumi preview --refresh --diff
pulumi up
```

Stage the same reviewed Docker packages and image on the new DigitalOcean VM.
Set `RECOVERY_SSH` to its verified SSH alias and start the blank server:

```sh
ssh "$RECOVERY_SSH" sudo bash -s < start-postgres.sh
```

Switch the restic B2 credentials to the read-only recovery key and set
`SNAPSHOT_ID` to the saved 64-character ID. Keep the original
`RESTIC_REPOSITORY` and `RESTIC_PASSWORD_FILE` values. Then restore:

```sh
bash recover.sh
```

createdb refuses an existing inventory database. pg_restore runs with
--exit-on-error --single-transaction and pipefail detects either stream failure.
A failure leaves a blank or rolled-back database for investigation; rebuilding
an approved disposable target is an explicit operator decision, not an automatic
retry that destroys data. Source runtime never seeds or contacts recovery.

### Check that recovery worked

Connect to the restored database:

```sh
ssh "$RECOVERY_SSH" sudo docker exec -i --user postgres postgres \
  psql -X -U postgres -d inventory -v ON_ERROR_STOP=1
```

Run the same three SELECT statements from step 4 and compare every field with
your saved baseline, including the recovery marker. Then insert a different SKU
without specifying its ID and update the recovered product. Both operations
should succeed, and the generated ID should advance. Keep the source database
stopped during these checks. A running server, a row count or a snapshot ID
alone does not prove recovery. These live checks remain unrun in the recorded trial.

## 7. Understand costs and remove the example

protectData defaults true for the source VM, recovery VM and B2 bucket. Changes
that replace/delete them fail until the operator deliberately changes protection.
AWS root volume encryption is enabled. DO's standard disk protection remains the
provider's contract; no customer-managed DO disk key is claimed. The B2 backup is
client-side encrypted regardless of provider storage encryption. No Object Lock,
automatic retention, lifecycle expiry or scheduled backup is enabled. Do not set
short per-object lifecycle expiration on a restic repository: it can corrupt
retained snapshots. Backups persist until explicitly deleted.

Budget for both VMs, public IPv4 addresses, disks, the deployment environment,
and B2 storage/API/download charges. Check prices for your selected regions and
account before applying. Set a short trial deadline and reserve time for cleanup;
this example does not enforce a spending cap.

This is a single-node database, not high availability or continuous replication.
You can recover only as far as the last successful logical dump (the recovery
point). Recovery time and throughput have not been measured.

### Cleanup checklist

After the trial, including after a failure, follow this checklist. Deleting these
resources can permanently remove the database and its backups. Decide what to
retain before changing protection. The deployment operator:

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
   cannot clean up, uses the operator's provisioning identity; never broadens
   guest permissions. A nonempty bucket must fail deletion visibly.
5. Independently inventories owned AWS instance/EBS/network/key resources,
   DigitalOcean VM/firewall/tag/SSH-key resources and B2 buckets/versions/uploads/
   application keys. Includes any operator-created controller and temporary access
   artifacts. Deletes only owned disposable resources; records billable
   remainders, billing delay and remediation instead of calling them cleaned up.
6. Revokes remaining temporary tokens and SSH keys, deletes private credential
   files and plaintext evidence as appropriate, and removes encrypted state only
   after verified cleanup. Repository password loss prevents recovery.

If SDK generation, scanned artifact staging, B2/DO signup/credentials, VM approval
or cleanup access is unavailable, stop before paid deployment. Those prerequisites
are external, and no live result has been fabricated for them.

## Getting help

For source issues, include the step number, pinned tool versions and a sanitized
error in a repository issue. Keep passwords, provider tokens, SSH keys, state and
raw database records private.

## License

This example's authored code is licensed under the [MIT License](LICENSE) and
is provided as-is, without warranty or a support commitment. Third-party
components retain their own licenses and notices.
