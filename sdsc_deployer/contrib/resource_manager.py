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
        if not app.config.get('RESOURCE_MANAGER_URL'):
            RuntimeError('You must provide a RESOURCE_MANAGER_URL')

        jwt_key = app.config['DEPLOYER_JWT_KEY']

        if not jwt_key:
            raise RuntimeError('You must provide the DEPLOYER_JWT_KEY')

        app.before_request(exchange_token)
        app.extensions['sdsc-resource-manager'] = self


def exchange_token():
    """Request new token from resource manager."""
    resource_request = {'service_claims': {'claims': request.view_args}}

    if request.endpoint in current_app.view_functions:
        view_func = current_app.view_functions[request.endpoint]
        if not hasattr(view_func, '_oauth_scopes'):
            return
        resource_request['scope'] = list(
            getattr(view_func, '_oauth_scopes', tuple()))

    access_token = request_authorization_token(request.headers,
                                               resource_request)

    if access_token is None:
        raise Unauthorized('Could not retrieve an ' 'authorization token')

    header_token = 'Bearer {0}'.format(access_token)
    # This is very dirty workaround to immutable request headers.
    request.headers.environ['HTTP_AUTHORIZATION'] = header_token
    assert request.headers['Authorization'] == header_token


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
