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
"""Send events to Graph Mutation Service."""

import logging
import os
import time
import uuid

import requests
from flask import abort, current_app, request
from sqlalchemy.types import Integer
from sqlalchemy_utils.types import JSONType, UUIDType
from werkzeug.exceptions import InternalServerError
from werkzeug.wrappers import Response

from renga_deployer.deployer import context_created, execution_created, \
    execution_launched
from renga_deployer.models import Context, Execution, db
from renga_deployer.utils import dict_from_labels, join_url

logger = logging.getLogger('renga.deployer.contrib.knowledge_graph')


class GraphContext(db.Model):
    """Represent a graph context node."""

    __tablename__ = 'graph_context'

    id = db.Column(Integer, primary_key=True, default=0)
    """Graph identifier."""

    context_id = db.Column(UUIDType, db.ForeignKey(Context.id))
    """Context identifier."""

    context = db.relationship(Context, backref='graph')


class GraphExecution(db.Model):
    """Represent a graph execution node."""

    __tablename__ = 'graph_execution'

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
        if not app.config.get('KNOWLEDGE_GRAPH_URL'):
            RuntimeError('You must provide a KNOWLEDGE_GRAPH_URL')
        app.extensions['renga-knowledge-graph-sync'] = self

        # connect signal handlers
        context_created.connect(create_context)
        execution_created.connect(create_execution)
        execution_launched.connect(launch_execution)

        logger.debug('Knowledge graph extension started.')

    def disconnect(self):
        """Remove signal handlers."""
        context_created.disconnect(create_context)
        execution_created.disconnect(create_execution)

    @property
    def named_types(self):
        """Fetch named types from types service."""
        if self._named_types is None:
            service_access_token = get_service_access_token(
                token_url=current_app.config['DEPLOYER_TOKEN_URL'],
                audience='renga-services',
                client_id=current_app.config['RENGA_AUTHORIZATION_CLIENT_ID'],
                client_secret=current_app.config[
                    'RENGA_AUTHORIZATION_CLIENT_SECRET'])

            headers = {
                'Authorization': 'Bearer {}'.format(service_access_token)
            }

            response = requests.get(
                join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                         'types/management/named_type'),
                headers=headers)
            if not 200 <= response.status_code < 300:
                logger.error('Retrieving types failed.')
                raise RuntimeError('Retrieving types failed.')
            else:
                self._named_types = response.json()
        return self._named_types


def create_context(context, service_access_token=None):
    """Create context node."""
    if service_access_token is None:
        service_access_token = get_service_access_token(
            token_url=current_app.config['DEPLOYER_TOKEN_URL'],
            audience='renga-services',
            client_id=current_app.config['RENGA_AUTHORIZATION_CLIENT_ID'],
            client_secret=current_app.config[
                'RENGA_AUTHORIZATION_CLIENT_SECRET'])

    try:
        operations = [vertex_operation(context, temp_id=0)]
    except RuntimeError:
        db.session.rollback()
        abort(Response('Vertex operation failed.', 504))

    # link the context to a project if a project_id is provided
    project_id = request.headers.get('Renga-Projects-Project')

    if project_id:
        operations.append({
            'type': 'create_edge',
            'element': {
                'label': 'project:is_part_of',
                'from': {
                    'type': 'new_vertex',
                    'id': 0
                },
                'to': {
                    'type': 'persisted_vertex',
                    'id': int(project_id)
                }
            }
        })

    response = mutation(
        operations,
        wait_for_response=True,
        service_access_token=service_access_token).json()

    if response['response']['event']['status'] == 'success':
        vertex_id = response['response']['event']['results'][0]['id']
        context.spec.setdefault('labels', [])
        context.spec['labels'].insert(
            0, 'renga.execution_context.vertex_id={0}'.format(vertex_id))
        db.session.add(GraphContext(id=vertex_id, context=context))
    else:
        logger.error('Mutation failed.', extra={'response': response})
        raise InternalServerError('Adding vertex and/or edge failed')


def create_execution(execution, token=None, service_access_token=None):
    """Create execution node and vertex connecting context."""
    token = token or request.headers['Authorization']

    if service_access_token is None:
        service_access_token = get_service_access_token(
            token_url=current_app.config['DEPLOYER_TOKEN_URL'],
            audience='renga-services',
            client_id=current_app.config['RENGA_AUTHORIZATION_CLIENT_ID'],
            client_secret=current_app.config[
                'RENGA_AUTHORIZATION_CLIENT_SECRET'])

    try:
        operations = [vertex_operation(execution, temp_id=0)]
    except RuntimeError:
        db.session.rollback()
        abort(Response('Vertex operation failed.', 504))

    operations.append({
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
    })

    response = mutation(
        operations,
        wait_for_response=True,
        service_access_token=service_access_token).json()

    if response['response']['event']['status'] == 'success':
        vertex_id = response['response']['event']['results'][0]['id']
    else:
        logger.error('Mutation failed.', extra={'response': response})
        raise InternalServerError('Adding vertex and/or edge failed')

    db.session.add(GraphExecution(id=vertex_id, execution=execution))

    execution.environment.update({
        'RENGA_VERTEX_ID':
        vertex_id,
        'RENGA_ACCESS_TOKEN':
        token[len('Bearer'):].strip(),
        'RENGA_ENDPOINT':
        current_app.config['RENGA_ENDPOINT']
    })


def launch_execution(execution, token=None):
    """Update the execution with launch info."""
    pass


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
    for t in current_app.extensions['renga-knowledge-graph-sync'].named_types:
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


def mutation(operations, wait_for_response=False, service_access_token=None):
    """
    Submit a mutation to the graph.

    If ``wait_for_response == True`` the return value is the reponse JSON,
    otherwise the mutation UUID is returned.
    """
    knowledge_graph_url = current_app.config['KNOWLEDGE_GRAPH_URL']

    headers = {'Authorization': 'Bearer {}'.format(service_access_token)}

    response = requests.post(
        join_url(knowledge_graph_url, '/mutation/mutation'),
        json={'operations': operations},
        headers=headers)

    if not 200 <= response.status_code < 300 and 'uuid' not in response.json():
        logger.warn(
            'Mutation request failed.', extra={'response': response.json()})
        abort(Response('Mutation service failed.', status=504))

    uuid = response.json().get('uuid')

    if wait_for_response:
        completed = False
        while not completed:
            response = requests.get(
                join_url(
                    knowledge_graph_url,
                    '/mutation/mutation/{uuid}'.format(uuid=uuid)),
                headers=headers)
            completed = response.json()['status'] == 'completed'
            # sleep for 200 miliseconds
            time.sleep(0.2)
    return response


def get_service_access_token(token_url, audience, client_id, client_secret):
    """Retrieve a service access token."""
    r = requests.post(
        token_url,
        data={
            'audience': audience,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        })
    return r.json()['access_token']


named_types_mapping = {
    Context: 'deployer:context',
    Execution: 'deployer:execution'
}
type_mapping = {'string': str}
