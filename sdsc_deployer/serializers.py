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
"""Model serializers."""

from marshmallow import Schema, fields, post_dump, post_load

from .models import Context, Execution


class SpecificationSchema(Schema):
    """Specification schema."""

    image = fields.String()
    ports = fields.Dict()


class ContextSchema(Schema):
    """Context schema for use with REST API."""

    identifier = fields.UUID(attribute='id', dump_only=True)
    spec = fields.Nested(SpecificationSchema)

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
    namespace = fields.String(default='default')
    engine_id = fields.String(load_only=True)

    @post_dump(pass_many=True)
    def add_envelope(self, data, many):
        """Add envelope if needed."""
        if many:
            return {'executions': data}
        return data

    @post_load
    def make_execution(self, data):
        """Create a context."""
        return Execution(**data)
