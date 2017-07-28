# -*- coding: utf-8 -*-
#
# Copyright 2017 Swiss Data Science Center
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""SDSC Deployer application."""

import os

import connexion
from connexion.resolver import RestyResolver
from flask import jsonify, request
from flask_babelex import Babel
from jose import jwt

from .ext import SDSCDeployer
from .models import db

DEPLOYER_CONFIG = {
    'DEPLOYER_URL':
    os.getenv('DEPLOYER_URL', 'localhost:5000'),
    'DEPLOYER_AUTHORIZATION_URL':
    os.getenv('DEPLOYER_AUTHORIZATION_URL',
              'https://testing.datascience.ch:8080/auth/realms/SDSC/'
              'protocol/openid-connect/auth'),
    'DEPLOYER_TOKEN_URL':
    os.getenv('DEPLOYER_TOKEN_URL',
              'https://testing.datascience.ch:8080/auth/realms/SDSC/'
              'protocol/openid-connect/token'),
    # x-tokenInfoUrl: "https://testing.datascience.ch:8080/auth/realms/SDSC/"
    #                 "protocol/openid-connect/token/introspect"
    # 'DEPLOYER_TOKEN_INFO_URL':
    # os.getenv('DEPLOYER_TOKEN_INFO_URL', 'http://localhost:5000/tokeninfo'),
    'DEPLOYER_CLIENT_ID':
    os.getenv('DEPLOYER_CLIENT_ID', 'demo-client'),
    'DEPLOYER_CLIENT_SECRET':
    os.getenv('DEPLOYER_CLIENT_SECRET', None),
    'DEPLOYER_APP_NAME':
    os.getenv('DEPLOYER_APP_NAME', 'demo-client'),
    'SQLALCHEMY_DATABASE_URI':
    os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///deployer.db'),
}

api = connexion.App(__name__, specification_dir='schemas/', swagger_ui=True)
api.app.config.update(DEPLOYER_CONFIG)
api.add_api(
    'sdsc-deployer-v1.yaml',
    arguments=DEPLOYER_CONFIG,
    resolver=RestyResolver('sdsc_deployer.api'), )  # validate_responses=True)

Babel(api.app)
db.init_app(api.app)
SDSCDeployer(api.app)

if os.getenv('DEPLOYER_GRAPH_MUTATION_URL'):
    from .contrib.knowledge_graph import KnowledgeGraphSync
    KnowledgeGraphSync(api.app)


@api.app.route('/tokeninfo')
def tokeninfo():
    """Return token information."""
    token = jwt.decode(
        request.args.get('access_token'),
        api.app.config['DEPLOYER_CLIENT_SECRET'],
        algorithms=['RS256'],
        audience=api.app.config['DEPLOYER_CLIENT_ID'],
        options={
            'verify_signature': False,  # FIXME enable verification
        }, )

    # FIXME configure scopes
    token.setdefault('scope', ['write:contexts', 'read:contexts'])
    return jsonify(token)


app = api.app
