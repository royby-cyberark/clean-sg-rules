import json
import logging
from typing import List

import boto3
import botocore


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def handler(event, context):
    dry_run = event.get('DryRun', True).lower() == 'true'
    single_region = event.get('SingleRegion')
    log_level = event.get('LogLevel', 'INFO')
    LOGGER.setLevel(logging.getLevelName(log_level))

    ec2 = boto3.client('ec2')
    # Retrieves all regions/endpoints that work with EC2
    response = ec2.describe_regions()
    ec2_regions = [region['RegionName'] for region in response['Regions']]
    LOGGER.info(f'Regions: {ec2_regions}')

    if single_region:
        clean_rules_from_default_vpc_sg(dry_run=dry_run, region=region)
    else:
        for region in ec2_regions:
            clean_rules_from_default_vpc_sg(dry_run=dry_run, region=region)


def clean_rules_from_default_vpc_sg(dry_run: bool, region: str):
    LOGGER.info(f'+++ Reading VPC details for {region}')
    ec2 = boto3.resource('ec2', region_name=region)
    client = boto3.client('ec2', region_name=region)

    filters = [{'Name':'isDefault', 'Values': ['true']}]

    vpcs = list(ec2.vpcs.filter(Filters=filters))

    LOGGER.info(f'{vpcs=}')

    for vpc in vpcs:
        response = client.describe_vpcs(VpcIds=[vpc.id])
        LOGGER.debug(json.dumps(response, indent=4))

        remove_rules_from_default_sg(dry_run=dry_run, 
                                     ec2_client=client, ec2_resource=ec2, 
                                     vpc_id=response['Vpcs'][0]['VpcId'])


def remove_rules_from_default_sg(dry_run: bool, ec2_client, ec2_resource, vpc_id: str):
    
    filters=[
        {
            'Name': 'vpc-id',
            'Values': [vpc_id]
        }
    ]

    response=ec2_client.describe_security_groups(Filters=filters)
    
    LOGGER.debug(f'Security groups: {response}')

    for security_group in response['SecurityGroups']:
        inbound_rules = rules_with_default_cidr_rules(security_group['IpPermissions'])
        outbound_rules = rules_with_default_cidr_rules(security_group['IpPermissionsEgress'])
        sg_id = security_group['GroupId']

        sg = ec2_resource.SecurityGroup(sg_id)
        revoke_rules(sg, rules=inbound_rules, sg_id=sg_id, vpc_id=vpc_id, type='inbound', dry_run=dry_run)
        revoke_rules(sg, rules=outbound_rules, sg_id=sg_id, vpc_id=vpc_id, type='outbound', dry_run=dry_run)

def rules_with_default_cidr_rules(rules: List):
    rules_with_ip_ranges = [rule for rule in rules if rule['IpRanges'] or rule['Ipv6Ranges']]
    
    default_cidr_lambda = lambda rule: {'CidrIp': '0.0.0.0/0'} in rule['IpRanges'] or {'CidrIp': '::/0'} in rule['Ipv6Ranges']
    return [rule for rule in rules_with_ip_ranges if default_cidr_lambda(rule)]

def revoke_rules(sg, sg_id: str, vpc_id: str, rules: List, type: str, dry_run: bool):
    if not rules:
        LOGGER.info(f'Security group {sg_id} in default vpc: {vpc_id}, has no {type} rules')
        return

    LOGGER.info(f'Warning! security group {sg_id} in default vpc: {vpc_id}, has {type} rules')
    LOGGER.info('Deleting rules: {rules}')
        
    try:
        sg.revoke_ingress(IpPermissions=rules, DryRun=dry_run)
    except botocore.exceptions.ClientError as ex:
        if ex.response['Error']['Code'] == 'DryRunOperation':
            LOGGER.info(f'{ex.response["Error"]["Message"]} ({rules=})')
        else:
            raise
