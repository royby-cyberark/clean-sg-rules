import aws_cdk as core
import aws_cdk.assertions as assertions

from clean_default_sg_rules.clean_default_sg_rules_stack import CleanDefaultSgRulesStack

# example tests. To run these tests, uncomment this file along with the example
# resource in clean_default_sg_rules/clean_default_sg_rules_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CleanDefaultSgRulesStack(app, "clean-default-sg-rules")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
