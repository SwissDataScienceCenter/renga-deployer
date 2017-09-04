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
"""Configuration options can be also provided as environmental variables."""

import ast
import os

DEPLOYER_DEFAULT_VALUE = 'foobar'
"""Default value for the application."""

DEPLOYER_URL = 'localhost:5000'
"""Basre URL for the service."""

DEPLOYER_BASE_PATH = '/v1'
"""Base path for the API."""

DEPLOYER_AUTHORIZATION_URL = ('http://localhost:8080/auth/realms/Renga/'
                              'protocol/openid-connect/auth')
"""OpenID-Connect authorization endpoint."""

DEPLOYER_TOKEN_URL = ('http://localhost:8080/auth/realms/Renga/'
                      'protocol/openid-connect/token')
"""OpenID-Connect token endpoint."""

# FIXME
# DEPLOYER_TOKEN_INFO_URL = ('http://localhost:8080/auth/realms/Renga/'
#                            'protocol/openid-connect/token/introspect')

DEPLOYER_CLIENT_ID = 'demo-client'
"""Client identifier used for OIDC authentication."""

DEPLOYER_CLIENT_SECRET = None
"""Client credentials used for OIDC authentication."""

DEPLOYER_APP_NAME = 'demo-client'
"""Application name."""

DEPLOYER_JWT_ISSUER = 'http://localhost:8080/auth/realms/Renga'
"""JWT issuer used for token verification."""

DEPLOYER_JWT_KEY = None
"""Public key used to verify JWT tokens."""

DEPLOYER_TOKEN_SCOPE_KEY = None
"""Key inside JWT containing scopes.

Use 'https://rm.datascience.ch/scope' in combination with resource manager.
"""

DEPLOYER_SWAGGER_UI = False
"""Enable Swagger UI."""

DEPLOYER_BASE_TEMPLATE = 'renga_deployer/base.html'
"""Default base template for the demo page."""

RENGA_AUTHORIZATION_CLIENT_SECRET = None
"""Client secret for fetching the service access token."""

RENGA_AUTHORIZATION_CLIENT_ID = None
"""Client id for fetching the service access token."""

SQLALCHEMY_DATABASE_URI = 'sqlite:///deployer.db'
"""The URI of the database to be used for preserving internal state."""

SQLALCHEMY_TRACK_MODIFICATIONS = False
"""Should Flask-SQLAlchemy will track modifications of objects."""

KNOWLEDGE_GRAPH_URL = None
"""Push contexts and executions to the KnowledgeGraph."""

RESOURCE_MANAGER_URL = None
"""Obtain and validate ResourceManager authorization tokens."""

RENGA_ENDPOINT = 'http://localhost/api'
"""URL for other platform services."""

WSGI_NUM_PROXIES = None
"""The number of proxy servers in front of the app.

Disable proxy fixer by setting value evaluating to ``False``.
"""


def from_env(config):
    """Load configuration options from environment variables."""
    result = {}
    for name, value in os.environ.items():
        if not hasattr(config, name) and name.isupper():
            continue

        # Evaluate value
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            pass

        result[name] = value

    return result
