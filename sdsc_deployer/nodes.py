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
"""Nodes sub-module."""

import uuid
from collections import namedtuple

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils.models import Timestamp
from sqlalchemy_utils.types import JSONType, UUIDType

db = SQLAlchemy()
"""Core database object."""


class Node(db.Model):
    """Represent node metadata."""

    __tablename__ = 'nodes'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Node identifier."""

    data = db.Column(
        db.JSON(none_as_null=True).with_variant(JSONType, 'sqlite'),
        index=True)
    """Node definition."""

    @classmethod
    def create(cls, data=None):
        """Create a new node."""
        node = cls(data=data)
        db.session.add(node)
        db.session.commit()
        return node


class ExecutionEnvironment(db.Model, Timestamp):
    """Represent an execution environment.

    Additionally it constans two columns ``created`` and ``updated``
    with automatically managed timestamps.
    """

    __tablename__ = 'execution_environments'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Execution identifier."""

    engine = db.Column(db.String, index=True)
    """Engine name."""

    engine_id = db.Column(db.String, index=True)
    """Internal identifier returned by an engine."""

    namespace = db.Column(db.String)
    """Namespace name."""

    node_id = db.Column(UUIDType, db.ForeignKey(Node.id))
    """Node identifier from which the execution started."""

    execution = db.relationship(Node, backref=db.backref(
        'nodes', lazy='dynamic', cascade='all, delete-orphan'), lazy='joined')

    @classmethod
    def from_node(cls, node, **kwargs):
        """Create a new execution for a given node."""
        execution = cls(node_id=node.id, **kwargs)
        db.session.add(execution)
        db.session.commit()
        return execution
