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
"""Retrieve authorization from the Resource Manager service."""

import os

import requests
from flask import current_app, request
from jose import jwt
from werkzeug.exceptions import Unauthorized

from sdsc_deployer.utils import join_url


class ResourceManager(object):
    """Resource Manager requests extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask app initialization."""
        app.config.setdefault('RESOURCE_MANAGER_URL',
                              join_url(
                                  app.config['PLATFORM_SERVICE_API'],
                                  'resource-manager/authorize'))

        rm_key = os.getenv('RESOURCE_MANAGER_PUBLIC_KEY', '')

        if rm_key is '':
            raise RuntimeError('You must provide the '
                               'RESOURCE_MANAGER_PUBLIC_KEY '
                               'environment variable')

        # jose.jwt requires begin/end in the key
        if not rm_key.startswith('-----BEGIN PUBLIC KEY-----'):
            rm_key = """-----BEGIN PUBLIC KEY-----
            {key}
            -----END PUBLIC KEY-----""".format(key=rm_key)

        app.config.setdefault('RESOURCE_MANAGER_PUBLIC_KEY', rm_key)

        app.extensions['sdsc-resource-manager'] = self


def request_authorization_token(headers, resource_request):
    """
    Request resource access token from the ResourceManager.

    :param headers: request headers; must include access token

    :param resource_request: dict specifying the resource request
    """
    r = requests.post(
        current_app.config['RESOURCE_MANAGER_URL'],
        headers=headers,
        json=resource_request)

    if r.status_code != 200:
        return None
    else:
        return r.json()['access_token']
