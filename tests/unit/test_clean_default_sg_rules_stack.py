import os
from typing import Dict
import boto3
from moto import mock_ec2
import pytest

from clean_default_sg_rules.sg_cleaner.handler import handler
from tests.unit.boto_utils import create_vpc_resources, get_security_groups, init_networks_in_all_regions


@pytest.fixture(scope='function', autouse=True)
def aws_credentials():
    """
    Mocked AWS Credentials for moto
    moto is setting all to foobar_X, but just in case
    """
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


def assert_vpc(region_to_vpcid: Dict):
    for region, vpc_id in region_to_vpcid.items():
        ec2_client = boto3.client('ec2', region_name=region)
        sgs = get_security_groups(ec2_client, vpc_id)
        for sg in sgs:
            response = ec2_client.describe_security_group_rules(Filters=[{'Name': 'group-id', 'Values': [sg['GroupId']]}])
            assert response


@mock_ec2
def test_rules_revoked_only_in_default_vpc():
    ec2_client = boto3.client('ec2')
    # ec2_resource = boto3.resource('ec2')

    region_to_vpcid = init_networks_in_all_regions(ec2_client)
    assert_vpc(region_to_vpcid)



@mock_ec2
def test_default_vpc():
    ec2_resource = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    filters = [{'Name':'isDefault', 'Values': ['true']}]
    vpcs = list(ec2_resource.vpcs.filter(Filters=filters))

    assert len(vpcs) == 1

    sgs = get_security_groups(ec2_client, vpc_id=vpcs[0].id)
    assert len(sgs) == 1
    assert sgs[0]['GroupName'] == 'default'


@mock_ec2
def test_none_default_vpc_no_not_exist():
    ec2_resource = boto3.resource('ec2')
    ec2_client = boto3.client('ec2')
    filters = [{'Name':'isDefault', 'Values': ['flase']}]
    vpcs = list(ec2_resource.vpcs.filter(Filters=filters))

    assert not vpcs

#     assert os.environ['AWS_ACCESS_KEY_ID'] in ['testing', 'foobar_key']


# TODO:
# add add non default vpc
# add non default sg with bad rules
# look at rules in default
# add good rules to defaults
# test: 
# dry_run = event.get('DryRun', True)
# clean_inbound = event.get('CleanInbound', True)
# clean_outbound = event.get('CleanOutbound', True)
# test all regions, single region
# only default vpc is changed
# add sgs are changed
# only bad rules revoked
# test both incoming, outgoing
# 