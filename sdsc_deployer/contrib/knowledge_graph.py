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
import time
import uuid

import requests
from flask import current_app, request
from sqlalchemy.types import Integer
from sqlalchemy_utils.types import JSONType, UUIDType

from sdsc_deployer.deployer import context_created, execution_created
from sdsc_deployer.models import Context, Execution, db
from sdsc_deployer.utils import join_url


class GraphContext(db.Model):
    """Represent a graph context node."""

    id = db.Column(Integer, primary_key=True, default=0)
    """Graph identifier."""

    context_id = db.Column(UUIDType, db.ForeignKey(Context.id))
    """Context identifier."""

    context = db.relationship(Context, backref='graph')


class GraphExecution(db.Model):
    """Represent a graph execution node."""

    id = db.Column(Integer, primary_key=True, default=0)
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
        self._named_types = None

    def init_app(self, app):
        """Flask application initialization."""
        app.config.setdefault('PLATFORM_SERVICE_API',
                              os.getenv('PLATFORM_SERVICE_API',
                                        'https://localhost:9000/api/'))

        context_created.connect(create_context)
        execution_created.connect(create_execution)

        app.extensions['sdsc-knowledge-graph-sync'] = self

    def disconnect(self):
        """Remove signal handlers."""
        context_created.disconnect(create_context)
        execution_created.disconnect(create_execution)

    @property
    def named_types(self):
        """Fetch named types from types service."""
        if self._named_types is None:
            self._named_types = requests.get(
                join_url(current_app.config['PLATFORM_SERVICE_API'],
                         'types/management/named_type')).json()
        return self._named_types


def create_context(context, token=None):
    """Create context node."""
    token = token or request.headers['Authorization']

    response = mutation(
        [vertex_operation(context, temp_id=0)],
        wait_for_response=True,
        token=token)

    if response['response']['event']['status'] == 'success':
        vertex_id = response['response']['event']['results'][0]['id']
    else:
        print(response)
        raise RuntimeError('Adding vertex failed')

    db.session.add(GraphContext(id=vertex_id, context=context))
    db.session.commit()


def create_execution(execution, token=None):
    """Create execution node and vertex connecting context."""
    token = token or request.headers['Authorization']

    operations = [
        vertex_operation(execution, temp_id=0), {
            'type': 'create_edge',
            'element': {
                'label': 'deployer:launch',
                'from': {
                    'type': 'persisted_vertex',
                    'id': execution.context.graph[0].id,
                },
                'to': {
                    'type': 'new_vertex',
                    'id': 0
                }
            }
        }
    ]

    response = mutation(operations, wait_for_response=True, token=token)

    if response['response']['event']['status'] == 'success':
        vertex_id = response['response']['event']['results'][0]['id']
    else:
        print(response)
        raise RuntimeError('Adding vertex and/or edge failed')

    db.session.add(GraphExecution(id=vertex_id, execution=execution))
    db.session.commit()


def sync(token=None):
    """Sync all nodes with graph service."""
    raise NotImplementedError()

    for context in Context.query.joined(Context.graph).filter(
            GraphContext.id.is_(None)):
        print(context, 'needs to be pushed')

    for execution in Execution.query.joined(Execution.graph).filter(
            GraphExecution.id.is_(None)):
        print(execution, 'needs to be pushed')


def vertex_operation(obj, temp_id):
    """
    Serialize Context or Execution to KnowledgeGraph schema.

    We iterate through the type definitions presented by the graph typesystem
    to extract the pieces we need from the object.

    TODO: use marshmallow or similar to serialize
    """
    try:
        named_type = named_types_mapping[obj.__class__]
    except KeyError:
        raise NotImplementedError(
            'No support for serializing {0}'.format(obj.__class__))

    # named_types are in format `namespace:name`
    name = named_type.split(':')[1]

    properties = []
    for t in current_app.extensions['sdsc-knowledge-graph-sync'].named_types:
        if t['name'] == name:
            for prop in t['properties']:
                prop_names = prop['name'].split('_')
                try:
                    if len(prop_names) == 2:
                        value = getattr(obj, prop_names[1])
                    elif len(prop_names) == 3:
                        value = getattr(obj, prop_names[1])[prop_names[2]]
                    else:
                        raise RuntimeError('Bad format for named type')
                except (KeyError, AttributeError):
                    # the property was not found in obj, go to the next one
                    continue

                # map to correct type
                value = type_mapping[prop['data_type']](value)

                # append the property
                properties.append({
                    'key':
                    '{named_type}_{key}'.format(
                        named_type=named_type, key='_'.join(prop_names[1:])),
                    'data_type':
                    prop['data_type'],
                    'cardinality':
                    prop['cardinality'],
                    'values': [{
                        'key':
                        '{named_type}_{key}'.format(
                            named_type=named_type,
                            key='_'.join(prop_names[1:])),
                        'data_type':
                        prop['data_type'],
                        'value':
                        value
                    }]
                })

    operation = {
        'type': 'create_vertex',
        'element': {
            'temp_id': temp_id,
            'types': ['{named_type}'.format(named_type=named_type)],
            'properties': properties
        }
    }

    return operation


def mutation(operations, wait_for_response=False, token=None):
    """
    Submit a mutation to the graph.

    If ``wait_for_response == True`` the return value is the reponse JSON,
    otherwise the mutation UUID is returned.
    """
    platform_url = current_app.config['PLATFORM_SERVICE_API']
    headers = {'Authorization': token}

    response = requests.post(
        join_url(platform_url, '/mutation/mutation'),
        json={'operations': operations},
        headers=headers, )

    uuid = response.json()['uuid']

    if wait_for_response:
        completed = False
        while not completed:
            response = requests.get(
                join_url(
                    platform_url,
                    '/mutation/mutation/{uuid}'.format(uuid=uuid))).json()
            completed = response['status'] == 'completed'
            # sleep for 200 miliseconds
            time.sleep(0.2)

        return response

    return response.json()['uuid']


named_types_mapping = {
    Context: 'deployer:context',
    Execution: 'deployer:execution'
}
type_mapping = {'string': str}
