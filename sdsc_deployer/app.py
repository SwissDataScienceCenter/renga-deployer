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

import logging
import os
import sys

import connexion
from connexion.resolver import RestyResolver
from flask import jsonify, request
from flask_babelex import Babel
from jose import jwt
from sqlalchemy_utils import functions

from .ext import SDSCDeployer
from .models import db

logging.basicConfig(level=logging.INFO)


def to_bool(e):
    """Convert string to boolean value if possible."""
    if isinstance(e, bool):
        return e
    elif isinstance(e, (int, float)):
        return bool(e)
    elif isinstance(e, str):
        try:
            if '.' in e:
                return bool(float(e))
            else:
                return bool(int(e))
        except ValueError:
            if e.lower() == 'true':
                return True
            elif e.lower() == 'false':
                return False
            else:
                raise ValueError(
                    'Could not decipher boolean from {0}'.format(e))


DEPLOYER_CONFIG = {
    'DEPLOYER_URL':
    os.getenv('DEPLOYER_URL', 'localhost:5000'),
    'DEPLOYER_AUTHORIZATION_URL':
    os.getenv('DEPLOYER_AUTHORIZATION_URL',
              'http://localhost:8080/auth/realms/SDSC/'
              'protocol/openid-connect/auth'),
    'DEPLOYER_TOKEN_URL':
    os.getenv('DEPLOYER_TOKEN_URL', 'http://localhost:8080/auth/realms/SDSC/'
              'protocol/openid-connect/token'),
    # 'DEPLOYER_TOKEN_INFO_URL':
    # os.getenv('DEPLOYER_TOKEN_INFO_URL',
    #           'http://localhost:8080/auth/realms/SDSC/'
    #           'protocol/openid-connect/token/introspect'),
    'DEPLOYER_CLIENT_ID':
    os.getenv('DEPLOYER_CLIENT_ID', 'demo-client'),
    'DEPLOYER_CLIENT_SECRET':
    os.getenv('DEPLOYER_CLIENT_SECRET',
              '5294a18e-e784-4e39-a927-ce816c91c83e'),
    'DEPLOYER_APP_NAME':
    os.getenv('DEPLOYER_APP_NAME', 'demo-client'),
    'SQLALCHEMY_DATABASE_URI':
    os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///deployer.db'),
    'SQLALCHEMY_TRACK_MODIFICATIONS':
    False,
    'DEPLOYER_KG_PUSH':
    to_bool(os.getenv('DEPLOYER_KG_PUSH', False)),
    'DEPLOYER_RM_AUTHORIZE':
    to_bool(os.getenv('DEPLOYER_RM_AUTHORIZE', False)),
    'PLATFORM_SERVICE_API':
    os.getenv('PLATFORM_SERVICE_API', 'http://localhost:9000/api'),
}


def create_app():
    """Create an instance of the flask app."""
    api = connexion.App(
        __name__, specification_dir='schemas/', swagger_ui=True)
    api.app.config.update(DEPLOYER_CONFIG)
    api.add_api(
        'sdsc-deployer-v1.yaml',
        arguments=DEPLOYER_CONFIG,
        resolver=RestyResolver('sdsc_deployer.api'),
    )  # validate_responses=True)

    Babel(api.app)
    db.init_app(api.app)
    SDSCDeployer(api.app)

    # add extensions
    if os.getenv('DEPLOYER_KG_PUSH'):
        from .contrib.knowledge_graph import KnowledgeGraphSync
        KnowledgeGraphSync(api.app)

    if os.getenv('DEPLOYER_RM_AUTHORIZE'):
        from .contrib.resource_manager import ResourceManager
        ResourceManager(api.app)

    # create database and tables
    with api.app.app_context():
        if not functions.database_exists(db.engine.url):
            functions.create_database(db.engine.url)

        db.create_all()

    return api.app


app = create_app()
