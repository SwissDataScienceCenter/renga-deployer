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

from flask import current_app, request

from sdsc_deployer.authorization import check_token, \
    resource_manager_authorization
from sdsc_deployer.ext import current_deployer
from sdsc_deployer.models import Context
from sdsc_deployer.serializers import ContextSchema

context_schema = ContextSchema()
contexts_schema = ContextSchema(many=True)


@check_token
def search():
    """Return a listing of currently known contexts."""
    return contexts_schema.dump(Context.query.all()).data, 200


@check_token
def get(context_id):
    """Return information about a specific context."""
    context = Context.query.get_or_404(context_id)
    return context_schema.dump(context).data, 200


@check_token
@resource_manager_authorization
def post(spec):
    """Create a new context."""
    context = current_deployer.deployer.create(spec)
    return context_schema.dump(context).data, 201
