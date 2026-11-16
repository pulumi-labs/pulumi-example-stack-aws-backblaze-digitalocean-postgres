"""Provision infrastructure only; backup and restore are explicit operator phases."""

from ipaddress import IPv4Network
from pathlib import Path

import pulumi
import pulumi_aws as aws
import pulumi_b2 as b2
import pulumi_digitalocean as do

config = pulumi.Config()
operator = IPv4Network(config.require("operatorCidr"))
if operator.prefixlen != operator.max_prefixlen:
    message = "operatorCidr must be the approved controller IPv4 /32"
    raise pulumi.RunError(message)
public_key = config.require("sshPublicKey")
source_ami = config.require("sourceAmi")
bucket_name = config.require("bucketName")
protect_data = config.get_bool("protectData")
if protect_data is None:
    protect_data = True
enable_recovery = config.get_bool("enableRecovery") or False
cloud_init = Path("ssh-hardening.yaml").read_text(encoding="utf-8")
aws_provider = aws.Provider("aws", opts=pulumi.ResourceOptions(version="7.52.1"))
aws_opts = pulumi.ResourceOptions(provider=aws_provider)
b2_provider = b2.Provider("b2")
b2_opts = pulumi.ResourceOptions(provider=b2_provider)

vpc = aws.ec2.Vpc(
    "source", cidr_block="10.77.0.0/24",
    enable_dns_support=True, enable_dns_hostnames=True, opts=aws_opts,
)
subnet = aws.ec2.Subnet(
    "source", vpc_id=vpc.id, cidr_block="10.77.0.0/25", opts=aws_opts,
)
gateway = aws.ec2.InternetGateway("source", vpc_id=vpc.id, opts=aws_opts)
routes = aws.ec2.RouteTable(
    "source", vpc_id=vpc.id,
    routes=[aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=gateway.id)],
    opts=aws_opts,
)
association = aws.ec2.RouteTableAssociation(
    "source", subnet_id=subnet.id, route_table_id=routes.id, opts=aws_opts,
)
security_group = aws.ec2.SecurityGroup(
    "source", vpc_id=vpc.id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp", from_port=22, to_port=22, cidr_blocks=[str(operator)],
    )],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="tcp", from_port=443, to_port=443, cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupEgressArgs(
            protocol="udp", from_port=53, to_port=53, cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupEgressArgs(
            protocol="tcp", from_port=53, to_port=53, cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    opts=aws_opts,
)
key = aws.ec2.KeyPair("operator", public_key=public_key, opts=aws_opts)
source = aws.ec2.Instance(
    "source", ami=source_ami, instance_type="t3.small",
    subnet_id=subnet.id, vpc_security_group_ids=[security_group.id],
    associate_public_ip_address=True, key_name=key.key_name,
    user_data=cloud_init, user_data_replace_on_change=True,
    metadata_options=aws.ec2.InstanceMetadataOptionsArgs(
        http_tokens="required", http_put_response_hop_limit=1,
    ),
    root_block_device=aws.ec2.InstanceRootBlockDeviceArgs(
        encrypted=True, volume_type="gp3", volume_size=12, delete_on_termination=True,
    ),
    tags={"Workload": "postgres-backup-aws-b2-digitalocean"},
    opts=pulumi.ResourceOptions(
        provider=aws_provider, protect=protect_data, depends_on=[association],
    ),
)
bucket = b2.Bucket(
    "backup", bucket_name=bucket_name, bucket_type="allPrivate",
    opts=pulumi.ResourceOptions(provider=b2_provider, protect=protect_data),
)
writer = b2.ApplicationKey(
    "backup-writer", key_name="postgres-backup-writer",
    bucket_ids=[bucket.bucket_id], name_prefix="postgres/",
    capabilities=["listBuckets", "listFiles", "readFiles", "writeFiles", "deleteFiles"],
    valid_duration_in_seconds=3600, opts=b2_opts,
)
pulumi.export("sourceIp", source.public_ip)
pulumi.export("bucketId", bucket.bucket_id)
pulumi.export(
    "resticRepository", pulumi.Output.concat("b2:", bucket.bucket_name, ":postgres"),
)
pulumi.export("writerKeyId", pulumi.Output.secret(writer.application_key_id))
pulumi.export("writerKey", pulumi.Output.secret(writer.application_key))

if enable_recovery:
    do_provider = do.Provider(
        "digitalocean", opts=pulumi.ResourceOptions(version="4.84.1"),
    )
    do_opts = pulumi.ResourceOptions(provider=do_provider)
    do_key = do.SshKey("operator", public_key=public_key, opts=do_opts)
    recovery_tag = do.Tag("recovery", opts=do_opts)
    firewall = do.Firewall(
        "recovery", tags=[recovery_tag.name],
        inbound_rules=[do.FirewallInboundRuleArgs(
            protocol="tcp", port_range="22", source_addresses=[str(operator)],
        )],
        outbound_rules=[
            do.FirewallOutboundRuleArgs(
                protocol="tcp", port_range="443", destination_addresses=["0.0.0.0/0"],
            ),
            do.FirewallOutboundRuleArgs(
                protocol="udp", port_range="53", destination_addresses=["0.0.0.0/0"],
            ),
            do.FirewallOutboundRuleArgs(
                protocol="tcp", port_range="53", destination_addresses=["0.0.0.0/0"],
            ),
        ],
        opts=do_opts,
    )
    recovery = do.Droplet(
        "recovery", image=config.require("recoveryImageId"),
        region=config.require("recoveryRegion"), size="s-1vcpu-1gb",
        ssh_keys=[do_key.fingerprint], tags=[recovery_tag.name],
        backups=False, monitoring=False, droplet_agent=False, ipv6=False,
        user_data=cloud_init,
        opts=pulumi.ResourceOptions(
            provider=do_provider, protect=protect_data, depends_on=[firewall],
        ),
    )
    reader = b2.ApplicationKey(
        "recovery-reader", key_name="postgres-recovery-reader",
        bucket_ids=[bucket.bucket_id], name_prefix="postgres/",
        capabilities=["listBuckets", "listFiles", "readFiles"],
        valid_duration_in_seconds=3600, opts=b2_opts,
    )
    pulumi.export("recoveryIp", recovery.ipv4_address)
    pulumi.export("readerKeyId", pulumi.Output.secret(reader.application_key_id))
    pulumi.export("readerKey", pulumi.Output.secret(reader.application_key))
