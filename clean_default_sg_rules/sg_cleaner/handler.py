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
    sg_ids = [id['GroupId'] for id in response['SecurityGroups']]

    response = ec2_client.describe_security_group_rules(Filters=[{'Name': 'group-id', 'Values': sg_ids}])

    for rule in response['SecurityGroupRules']:
        if rule_is_forbidden(rule):
            revoke_rule(ec2_resource, rule=rule, config=config)


def rule_is_forbidden(rule) -> bool:
    forbidden = rule.get('CidrIpv4') == '0.0.0.0/0' or rule.get('CidrIpv6') == '::/0'
    LOGGER.debug(f'checking if rule_is_forbidden: {rule}. result: {forbidden}')
    return forbidden


def revoke_rule(ec2_resource, rule, config: Config):
    rule_type = 'outbound' if rule['IsEgress'] else 'ingress'
    LOGGER.info(f'++Warning! forbidden {rule_type} rule found: {rule}')
    rule_id = rule['SecurityGroupRuleId']
    sg = ec2_resource.SecurityGroup(rule['GroupId'])

    # We can revoke all rules, but it might be better to go rule by rule
    if rule['IsEgress'] and config.clean_outbound:
        call_revoke_rules(sg.revoke_egress, rule_ids=[rule_id], dry_run=config.dry_run)

    if not rule['IsEgress'] and config.clean_inbound:
        call_revoke_rules(sg.revoke_ingress, rule_ids=[rule_id], dry_run=config.dry_run)


def call_revoke_rules(revoke_function, rule_ids: List, dry_run: bool):
    try:
        response = revoke_function(SecurityGroupRuleIds=rule_ids, DryRun=dry_run)
        LOGGER.info(f'Deleted sg result: {response}')
    except botocore.exceptions.ClientError as ex:
        if ex.response['Error']['Code'] == 'DryRunOperation':
            LOGGER.info(f'{ex.response["Error"]["Message"]} ({rule_ids=})')
        else:
            raise
