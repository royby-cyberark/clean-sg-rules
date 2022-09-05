from typing import Dict, List

import boto3


def get_security_groups(ec2_client, vpc_id: str) -> List:
    filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
    response=ec2_client.describe_security_groups(Filters=filters)
    return response['SecurityGroups']


def create_sg_rule(function, group_id: str, allowed_ipv4: str):
    return function(
            GroupId=group_id, 
            IpPermissions=[
                {
                    'FromPort': -1,
                    'ToPort': -1,
                    'IpRanges': [
                        {
                            'CidrIp': '0.0.0.0/0'
                        },
                        {
                            'CidrIp': allowed_ipv4
                        }
                    ],
                    'Ipv6Ranges': [
                        {
                            'CidrIpv6': '::/0'
                        },
                    ]
                }
            ]
        )


def create_vpc_resources(ec2_client, ec2_resource, security_groups: List[str], allowed_ipv4: str):
    response = ec2_client.create_vpc(CidrBlock='10.0.0.0/16')
    vpc = ec2_resource.Vpc(response['Vpc']['VpcId'])

    for sg_name in security_groups:
        sg = vpc.create_security_group(GroupName=sg_name, Description=sg_name)

        create_sg_rule(ec2_client.authorize_security_group_ingress, group_id=sg.group_id, allowed_ipv4=allowed_ipv4)
        create_sg_rule(ec2_client.authorize_security_group_egress, group_id=sg.group_id, allowed_ipv4=allowed_ipv4)

    return vpc


def init_networks_in_all_regions(ec2_client) -> Dict:
    response = ec2_client.describe_regions()
    ec2_regions = [region['RegionName'] for region in response['Regions']]

    result = dict()
    for region in ec2_regions:
        ec2_client = boto3.client('ec2', region_name=region)
        ec2_resource = boto3.resource('ec2', region_name=region)
        vpc = create_vpc_resources(ec2_client, ec2_resource, security_groups=['moshe_sg'], allowed_ipv4='1.1.1.1/32')
        result[region] = vpc.vpc_id

    return result
