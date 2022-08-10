from os import path
from aws_cdk import (
    aws_iam as iam,
    aws_lambda,
    Duration,
    Stack,
)
from constructs import Construct

class CleanDefaultSgRulesStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_role = iam.Role(
            scope=self,
            id=f'DefaultSgRuleCleanerRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'Ec2Policy':
                    iam.PolicyDocument(statements=[
                        iam.PolicyStatement(
                            actions=[
                                'ec2:DescribeRegions',
                                'ec2:DescribeVpcs',
                                'ec2:DescribeSecurityGroups',
                                'ec2:RevokeSecurityGroupIngress',
                                'ec2:RevokeSecurityGroupEgress',
                            ],
                            resources=['*'],
                            effect=iam.Effect.ALLOW,
                        ),
                    ])
            },
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )


        with open(path.join(path.dirname(__file__), 'sg_cleaner/handler.py'), encoding='utf-8') as file:
            lambda_code = file.read()
            
        aws_lambda.Function(
            self, 
            id='DefaultSgRuleCleaner', 
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            role=lambda_role, 
            code=aws_lambda.Code.from_inline(lambda_code),
            handler='index.handler',
            timeout=Duration.minutes(15),
        )
