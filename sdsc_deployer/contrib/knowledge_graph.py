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
"""Send events to Graph Mutation Service."""

import os
import uuid

import requests
from flask import current_app, request
from sqlalchemy_utils.types import JSONType, UUIDType

from sdsc_deployer.deployer import context_created, execution_created
from sdsc_deployer.models import Context, Execution, db
from sdsc_deployer.utils import _join_url


class GraphContext(db.Model):
    """Represent a graph context node."""

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Graph identifier."""

    context_id = db.Column(UUIDType, db.ForeignKey(Context.id))
    """Context identifier."""

    context = db.relationship(Context, backref='graph')


class GraphExecution(db.Model):
    """Represent a graph execution node."""

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Graph identifier."""

    execution_id = db.Column(UUIDType, db.ForeignKey(Execution.id))
    """Context identifier."""

    execution = db.relationship(Execution, backref='graph')


class KnowledgeGraphSync(object):
    """Knowledge Graph Sync extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.config.setdefault('GRAPH_MUTATION_URL',
                              os.getenv('GRAPH_MUTATION_URL',
                                        'https://localhost:9000/api/mutation'))

        context_created.connect(create_context)
        execution_created.connect(create_execution)

        app.extensions['sdsc-knowledge-graph-sync'] = self


def create_context(context, token=None):
    """Create context node."""
    token = token or request.headers['Authorization']
    headers = {'Authorization': token}

    response = requests.post(
        _join_url(current_app.config['GRAPH_MUTATION_URL'], '/mutation'),
        json=create_vertex(context),
        headers=headers, )

    # TODO: the uuid is *not* the ID we want... need to fix
    db.session.add(GraphContext(id=response.json()['uuid'], context=context))
    db.session.commit()


def create_execution(execution, token=None):
    """Create execution node and vertex connecting context."""
    token = token or request.headers['Authorization']
    headers = {'Authorization': token}

    response = requests.post(
        _join_url(current_app.config['GRAPH_MUTATION_URL'], '/mutation'),
        json=create_vertex(execution),
        headers=headers, )

    # TODO: the uuid is *not* the ID we want... need to fix
    db.session.add(
        GraphExecution(id=response.json()['uuid'], execution=execution))
    db.session.commit()

    if execution.context.graph is None:
        context_created(execution.context, token=token)

    # TODO create edge
    # execution.graph.id -> execution.context.graph.id


def sync(token=None):
    """Sync all nodes with graph service."""
    raise NotImplemented()

    for context in Context.query.joined(Context.graph).filter(
            GraphContext.id.is_(None)):
        print(context, 'needs to be pushed')

    for execution in Execution.query.joined(Execution.graph).filter(
            GraphExecution.id.is_(None)):
        print(execution, 'needs to be pushed')


def create_vertex(obj):
    """
    Serialize Context or Execution to KnowledgeGraph schema.

    We iterate through the type definitions presented by the graph typesystem
    to extract the pieces we need from the object.
    """
    named_type = named_types[obj.__class__]
    properties = []
    for t in requests.get('http://localhost:9000'
                          '/api/types/management/named_type').json():
        if t['name'] == named_type:
            for prop in t['properties']:
                names = prop['name'].split('_')

                if len(names) == 2:
                    value = getattr(obj, names[1])
                elif len(names) == 3:
                    value = getattr(obj, names[1])[names[2]]
                else:
                    raise RuntimeError('Bad format for named type')

                # map to correct type
                value = type_mapping[prop['data_type']](value)

                # append the property
                properties.append({
                    'key':
                    'deployer:{named_type}_{key}'.format(
                        named_type=named_type, key='_'.join(names[1:])),
                    'data_type':
                    'string',
                    'cardinality':
                    'single',
                    'values': [{
                        'key':
                        'deployer:{named_type}_{key}'.format(
                            named_type=named_type, key='_'.join(names[1:])),
                        'data_type':
                        prop['data_type'],
                        'value':
                        value
                    }]
                })

    mutation_schema = {
        'operations': [{
            'type': 'create_vertex',
            'element': {
                'temp_id': 0,
                'types':
                ['deployer:{named_type}'.format(named_type=named_type)],
                'properties': properties
            }
        }]
    }

    return mutation_schema


named_types = {Context: 'context', Execution: 'execution'}
type_mapping = {'string': str}
