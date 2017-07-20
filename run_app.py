#!/bin/env python

from flask import Flask

from sdsc_deployer.ext import SDSCDeployer

app = Flask('SDSC-Deployer')
deployer = SDSCDeployer(app)

if __name__ == '__main__':
    app.run(debug=True)
