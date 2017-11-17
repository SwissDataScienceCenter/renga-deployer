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
"""Implement ``/contexts`` endpoint."""

import json
import uuid

from flask import current_app, request
from werkzeug.exceptions import BadRequest

from renga_deployer.authorization import check_token
from renga_deployer.ext import current_deployer
from renga_deployer.models import Context
from renga_deployer.serializers import ContextSchema
from renga_deployer.utils import validate_uuid

context_schema = ContextSchema()
contexts_schema = ContextSchema(many=True)


@check_token('deployer:contexts_read')
def search():
    """Return a listing of currently known contexts."""
    return contexts_schema.dump(Context.query.all()).data, 200


@check_token('deployer:contexts_read')
def get(context_id):
    """Return information about a specific context."""
    if validate_uuid(context_id):
        context = Context.query.get_or_404(context_id)
        return context_schema.dump(context).data, 200
    raise BadRequest('context_id must be a UUID string')


@check_token('deployer:contexts_read', 'deployer:contexts_write')
def post(spec):
    """Create a new context."""
    context = current_deployer.deployer.create(spec)
    return context_schema.dump(context).data, 201
