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
"""Model serializers."""

from flask import current_app
from marshmallow import Schema, fields, post_dump, post_load, pre_dump

from .models import Context, Execution


class SpecificationSchema(Schema):
    """Specification schema."""

    image = fields.String()
    ports = fields.List(fields.String)
    labels = fields.List(fields.String)
    interactive = fields.Boolean()


class ContextSchema(Schema):
    """Context schema for use with REST API."""

    identifier = fields.UUID(attribute='id', dump_only=True)
    spec = fields.Nested(SpecificationSchema)
    jwt = fields.Dict(load_only=True)
    created = fields.DateTime(attribute='created', dump_only=True)

    @post_dump(pass_many=True)
    def add_envelope(self, data, many):
        """Add envelope if needed."""
        if many:
            return {'contexts': data}
        return data

    @post_load
    def make_context(self, data):
        """Create a context."""
        return Context(**data)


class ExecutionSchema(Schema):
    """Execution schema for use with REST API."""

    identifier = fields.UUID(attribute='id', dump_only=True)
    engine = fields.String(required=True)
    environment = fields.Dict()
    engine_id = fields.String(load_only=True)
    jwt = fields.Dict(load_only=True)
    namespace = fields.String(default='default')
    created = fields.DateTime(attribute='created', dump_only=True)
    state = fields.String(dump_only=True)

    @pre_dump
    def get_state(self, data):
        """Get state of an execution."""
        if data.engine_id:
            data.state = current_app.extensions[
                'renga-deployer'].deployer.get_state(data)
        return data

    @post_dump(pass_many=True)
    def add_envelope(self, data, many):
        """Add envelope if needed."""
        if many:
            return {'executions': data}
        return data

    @post_load
    def make_execution(self, data):
        """Create an execution."""
        return Execution(**data)
