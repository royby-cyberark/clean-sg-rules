
# Deploying the CloudFormation template
* Copy `clean_sg_rules_cf_template.yaml`
* deploy with AWS cli (Replace DefaultSecurityGroupCleaner with anything else you want): 

`aws cloudformation deploy --capabilities CAPABILITY_NAMED_IAM --template-file clean_sg_rules_cf_template.yaml --stack-name DefaultSecurityGroupCleaner`

* If you want to make changes to the Lambda, you need to run `source synth_cf_template` to generate an update CF template file (requires a working CDK env - see below)

* Destroy the stack (replace name if needed): `aws cloudformation delete-stack --stack-name DefaultSecurityGroupCleaner`

# Invoking the Lambda
You can invoke the lambda however you want (console, aws cli, etc.)
By default it will do a dry-run and won't delete anything, but you can look at its cloudwatch to see what it would do.
See defult values below.

* To do a wet run, pass the following input event to the Lambda:
```
{
    "DryRun": true/false (boolean)
}
```

* You can pass the following event parameters:
    "DryRun": true/false (If false - do a wet run)
    "LogLevel": "DEBUG"/"INFO" (Other are ok but have no effect)
    "SingleRegion" - set to a region name if you want to run on one region only, other will run on all regions
    "CleanInbound": true/false - if you want to avoid cleaning inbound (default is true)
    "CleanOutbound": true/false - if you want to avoid cleaning outbound (default is true)

* Example:

```
{
    "DryRun": false,
    "LogLevel": "DEBUG",
    "SingleRegion": "us-east-1",
    "CleanInbound": false,
    "CleanOutbound": true
}
```

* Default values (pass {} for default values):

```
    DryRun=true,
    LogLevel="INFO",
    CleanInbound=true,
    CleanOutbound=true
```

## Invoke from command-line

Under windows you might need to escape the double quotes (replaces " with \")
For example:

`aws lambda invoke --function-name <lambda-name> --cli-binary-format raw-in-base64-out --payload '{ "DryRun": false, "LogLevel": "DEBUG", "CleanInbound": false, "CleanOutbound": true }' lambda_output`

# Working with the CDK project
* Preqs: Python 3.8, pipenv
* Activate virtual env: `pipenv shell`
* Install dependencies: `pipenv sync --dev`
* Then you can run `source synth_cf_template`

    
