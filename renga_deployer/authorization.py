# -*- coding: utf-8 -*-
#
# Copyright 2017 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
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

import logging
from functools import wraps

from flask import current_app, g, request
from jose import jwt
from werkzeug.exceptions import Unauthorized

from renga_deployer.ext import current_deployer

logger = logging.getLogger('renga.deployer.authorization')


def check_token(*scopes):
    """Check that the request includes an authorization token."""
    method = None

    if len(scopes) == 1 and callable(scopes[0]):
        method = scopes[0]
        scopes = tuple()

    def decorator(function):
        """Store scopes on view function."""
        setattr(function, '_oauth_scopes', scopes)

        @wraps(function)
        def wrapper(*args, **kwargs):
            """Check JWT and scopes."""
            access_token = getattr(g, 'access_token',
                                   request.headers.get('Authorization'))

            # verify the token
            if not access_token or not access_token.lower().startswith(
                    'bearer '):
                logger.warn('Authorization token not found in headers.',
                            extra={'g': g, 'request': request.json()})
                raise Unauthorized('Authorization token not found in headers.')

            access_token = access_token[len('bearer '):]

            # verify the token and create the context
            key = current_app.config['DEPLOYER_JWT_KEY']
            options = {
                'verify_signature': key is not None,
            }

            g.jwt = auth = jwt.decode(
                access_token,
                issuer=current_app.config['DEPLOYER_JWT_ISSUER'],
                key=key,
                options=options, )

            scope_key = current_app.config['DEPLOYER_TOKEN_SCOPE_KEY']
            if scope_key and not all(
                    s in auth.get(scope_key, []) for s in scopes):
                logger.warn('Insufficient scope.',
                            extra={'g': g, 'request': request.json(),
                                   'scope_key': scope_key})
                raise Unauthorized('Insufficient scope.')

            return function(*args, **kwargs)

        return wrapper

    return decorator(method) if method else decorator
