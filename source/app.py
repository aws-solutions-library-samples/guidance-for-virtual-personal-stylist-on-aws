#!/usr/bin/env python3
import os

import aws_cdk as cdk

from virtualstylist.virtualstylist_stack import VirtualstylistStack

app = cdk.App()
VirtualstylistStack(app, "VirtualstylistStack")
app.synth()
