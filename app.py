#!/usr/bin/env python3
import os

import aws_cdk as cdk

from clean_default_sg_rules.clean_default_sg_rules_stack import CleanDefaultSgRulesStack


app = cdk.App()
CleanDefaultSgRulesStack(app, "CleanDefaultSgRulesStack", 
                         synthesizer=cdk.DefaultStackSynthesizer(generate_bootstrap_version_rule=False))

app.synth()
