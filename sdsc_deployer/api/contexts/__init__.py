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
"""Implement ``/contexts`` endpoint."""

import json

from flask import request, current_app

from sdsc_deployer.ext import current_deployer
from sdsc_deployer.models import Context
from sdsc_deployer.serializers import ContextSchema

context_schema = ContextSchema()
contexts_schema = ContextSchema(many=True)


def search():
    """Return a listing of currently known contexts."""
    return contexts_schema.dump(Context.query.all()).data, 200


def get(context_id):
    """Return information about a specific context."""
    context = Context.query.get_or_404(context_id)
    return context_schema.dump(context).data, 200


def post(spec):
    """Create a new context."""
    if 'sdsc-resource-manager' in current_app.extensions:
        from jose import jwt
        from sdsc_deployer.contrib.resource_manager \
            import request_authorization_token

        # form the resource request and get the authorization token
        resource_request = {
            'permission_holder_id': 0,
            'scope': ['contexts:write'],
            'extra_claims': {
                'spec': spec
            }
        }
        _, token = request.headers.get('Authorization').split()

        access_token = request_authorization_token(token, resource_request)

        # verify the token and create the context
        auth = jwt.decode(
            access_token,
            key=current_app.config['RESOURCE_MANAGER_PUBLIC_KEY'])

        assert auth['iss'] == 'resource-manager'
        assert json.loads(auth['resource_extras'])['spec'] == spec

    context = current_deployer.deployer.create(spec)
    return context_schema.dump(context).data, 201
