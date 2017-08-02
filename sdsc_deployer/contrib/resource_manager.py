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
"""Send events to Graph Mutation Service."""

import os

import requests
from flask import current_app, request
from jose import jwt

from sdsc_deployer.utils import _join_url


class ResourceManager(object):
    """Resource Manager requests exension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask app initialization."""
        app.config.setdefault(
            'RESOURCE_MANAGER_URL',
            os.getenv('RESOURCE_MANAGER_URL',
                      'http://localhost:9000/api/resource-manager/authorize'))

        rm_key = os.getenv('RESOURCE_MANAGER_PUBLIC_KEY', None)

        if not rm_key.startswith('-----BEGIN PUBLIC KEY-----'):
            rm_key = """-----BEGIN PUBLIC KEY-----
            {key}
            -----END PUBLIC KEY-----""".format(key=rm_key)

        app.config.setdefault('RESOURCE_MANAGER_PUBLIC_KEY', rm_key)


def request_authorization_token(access_token, resource_request):
    """
    Request resource access token from the ResourceManager.

    :param token: access token

    :param resource_request: dict specifying the resource request
    """
    headers = {
        'Authorization': 'Bearer {token}'.format(token=access_token),
        'Content-type': 'application/json'
    }

    r = requests.post(
        current_app.config['RESOURCE_MANAGER_URL'],
        headers=headers,
        json=resource_request)

    return r.json()['access_token']
