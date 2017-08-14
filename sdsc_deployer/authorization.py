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
"""Provide decorators for securing endpoints."""

from functools import wraps

from flask import current_app, request
from jose import jwt
from werkzeug.exceptions import Unauthorized

from sdsc_deployer.ext import current_deployer


def resource_manager_authorization(function):
    """If configured, check authorization with the ResourceManager."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if 'sdsc-resource-manager' in current_app.extensions:
            from jose import jwt
            from sdsc_deployer.contrib.resource_manager \
                import request_authorization_token

            if 'data' in kwargs:
                claims = kwargs['data']
            else:
                claims = args

            # form the resource request and get the authorization token
            resource_request = {
                'resource_id': 0,
                'scope': ['contexts:write'],
                'service_claims': {
                    'claims': claims
                }
            }

            access_token = request_authorization_token(request.headers,
                                                       resource_request)

            if access_token is None:
                raise Unauthorized('Could not retrieve an '
                                   'authorization token')

            # verify the token and create the context
            auth = jwt.decode(
                access_token,
                key=current_app.config['RESOURCE_MANAGER_PUBLIC_KEY'])

            if auth['iss'] != 'resource-manager':
                raise Unauthorized(
                    description='Could not verify authorization token.')

            # TODO: validate request
        return function(*args, **kwargs)

    return wrapper


def check_token(function):
    """Check that the request includes an authorization token."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        headers = request.headers

        # verify the token
        if 'Authorization' not in headers:
            raise Unauthorized('Authorization token not found in headers.')
        if not headers['Authorization'].startswith(('Bearer', 'bearer')):
            raise Unauthorized('Authorization token not found in headers.')
        return function(*args, **kwargs)

    return wrapper
