from dataclasses import dataclass
import json
import logging
from typing import List

import boto3
import botocore

LOGGER = logging.getLogger()

@dataclass
class Config:
    dry_run: bool
    clean_inbound: bool
    clean_outbound: bool


def handler(event, context):
    dry_run = event.get('DryRun', True)
    single_region = event.get('SingleRegion')
    log_level = event.get('LogLevel', 'INFO')
    clean_inbound = event.get('CleanInbound', True)
    clean_outbound = event.get('CleanOutbound', True)

    LOGGER.setLevel(logging.getLevelName(log_level))
    LOGGER.info(f'Parameters: {dry_run=}, {single_region=}, {log_level=}')

    config = Config(dry_run=dry_run, clean_inbound=clean_inbound, clean_outbound=clean_outbound)

    ec2 = boto3.client('ec2')
    response = ec2.describe_regions()
    ec2_regions = [region['RegionName'] for region in response['Regions']]
    LOGGER.info(f'Regions: {ec2_regions}')

    if single_region:
        clean_rules(config=config, region=single_region)
    else:
        for region in ec2_regions:
            clean_rules(config=config, region=region)


def clean_rules(config: Config, region: str):
    LOGGER.info(f'+VPC details for {region}')
    ec2_resource = boto3.resource('ec2', region_name=region)
    ec2_client = boto3.client('ec2', region_name=region)

    filters = [{'Name':'isDefault', 'Values': ['true']}]

    vpcs = list(ec2_resource.vpcs.filter(Filters=filters))

    LOGGER.info(f'{vpcs=}')

    for vpc in vpcs:
        response = ec2_client.describe_vpcs(VpcIds=[vpc.id])
        LOGGER.debug(json.dumps(response, indent=4))

        clean_rules_from_sg(config=config, ec2_client=ec2_client, ec2_resource=ec2_resource, 
                                     vpc_id=response['Vpcs'][0]['VpcId'])



def clean_rules_from_sg(config: Config, ec2_client, ec2_resource, vpc_id: str):
    filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]

    response=ec2_client.describe_security_groups(Filters=filters)
    
    LOGGER.debug(f'Security groups: {response}')

    for security_group in response['SecurityGroups']:
        inbound_rules = default_cidr_rules(security_group['IpPermissions'])
        LOGGER.debug(f'{inbound_rules=}')
    
        outbound_rules = default_cidr_rules(security_group['IpPermissionsEgress'])
        LOGGER.debug(f'{outbound_rules=}')
        
        sg_id = security_group['GroupId']

        sg = ec2_resource.SecurityGroup(sg_id)

        if config.clean_inbound and inbound_rules:
            revoke_rules(sg.revoke_ingress, rules=inbound_rules, sg_id=sg_id, vpc_id=vpc_id, type='inbound', dry_run=config.dry_run)
        if config.clean_outbound and outbound_rules:
            revoke_rules(sg.revoke_egress, rules=outbound_rules, sg_id=sg_id, vpc_id=vpc_id, type='outbound', dry_run=config.dry_run)


def default_cidr_rules(rules: List):
    rules_with_ip_ranges = [rule for rule in rules if rule['IpRanges'] or rule['Ipv6Ranges']]
    LOGGER.debug(f'{rules_with_ip_ranges=}')
    default_cidr_lambda = lambda rule: {'CidrIp': '0.0.0.0/0'} in rule['IpRanges'] or {'CidrIp': '::/0'} in rule['Ipv6Ranges']
    return [rule for rule in rules_with_ip_ranges if default_cidr_lambda(rule)]

def revoke_rules(revoke_function, sg_id: str, vpc_id: str, rules: List, type: str, dry_run: bool):
    LOGGER.info(f'++Warning! security group {sg_id} in default vpc: {vpc_id}, has {type} rules')
    LOGGER.info(f'Deleting rules: {rules=}')
        
    try:
        response = revoke_function(IpPermissions=rules, DryRun=dry_run)
        LOGGER.info(f'Deleted sg result: {response}')
        return len(rules)
    except botocore.exceptions.ClientError as ex:
        if ex.response['Error']['Code'] == 'DryRunOperation':
            LOGGER.info(f'{ex.response["Error"]["Message"]} ({rules=})')
        else:
            raise
