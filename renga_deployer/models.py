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
"""Models sub-module."""

import uuid
from collections import namedtuple

from flask import g, has_request_context
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.types import String
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

db = SQLAlchemy()
"""Core database object."""


def load_jwt():
    """Load JWT from a context."""
    if has_request_context():
        return g.jwt


class Context(db.Model, Timestamp):
    """Execution context.

    Additionally it contains two columns ``created`` and ``updated``
    with automatically managed timestamps.
    """

    __tablename__ = 'contexts'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Context identifier."""

    spec = db.Column(
        db.JSON(none_as_null=True).with_variant(JSONType, 'sqlite'))
    """Context specification."""

    jwt = db.Column(
        db.JSON(none_as_null=True).with_variant(JSONType, 'sqlite'),
        default=load_jwt)
    """JWT with which the context has been created."""

    creator = db.Column(String)
    """Creator of the context."""

    @classmethod
    def create(cls, spec=None):
        """Create a new context."""
        if 'ports' in spec:
            spec['ports'] = list(filter(None, spec['ports']))
        context = cls(spec=spec, id=uuid.uuid4())
        return context


class Execution(db.Model, Timestamp):
    """Represent an execution of a context.

    Additionally it contains two columns ``created`` and ``updated``
    with automatically managed timestamps.
    """

    __tablename__ = 'executions'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Execution identifier."""

    engine = db.Column(db.String, index=True)
    """Engine name."""

    engine_id = db.Column(db.String, index=True)
    """Internal identifier returned by an engine."""

    namespace = db.Column(db.String)
    """Namespace name."""

    environment = db.Column(
        db.JSON(none_as_null=True).with_variant(JSONType, 'sqlite'),
        default=dict)

    context_id = db.Column(UUIDType, db.ForeignKey(Context.id))
    """Context identifier from which the execution started."""

    context = db.relationship(
        Context,
        backref=db.backref(
            'executions', lazy='dynamic', cascade='all, delete-orphan'),
        lazy='joined')

    jwt = db.Column(
        db.JSON(none_as_null=True).with_variant(JSONType, 'sqlite'),
        default=load_jwt)
    """JWT with which the execution has been created."""

    @classmethod
    def from_context(cls, context, **kwargs):
        """Create a new execution for a given context."""
        kwargs.setdefault('environment', {})
        kwargs.setdefault('id', uuid.uuid4())
        kwargs['environment']['RENGA_CONTEXT_ID'] = str(context.id)
        execution = cls(context=context, **kwargs)
        return execution
