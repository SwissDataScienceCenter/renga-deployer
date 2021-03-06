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
"""Contrib modules tests."""

import json
import time
from collections import namedtuple

import pytest
import requests
from flask import current_app
from jose import jwt
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from renga_deployer import contrib
from renga_deployer.models import Execution, db
from renga_deployer.utils import join_url

r_get = requests.get
r_post = requests.post

Request = namedtuple('Request', ['body', 'headers', 'url'])


class Response(object):
    """Fake response."""

    def __init__(self, content, status_code, headers=None):
        """Initialize fake response object with a json."""
        self.content = content
        self.status_code = status_code
        self.headers = headers or {'header': 'some-header'}

    def json(self):
        """Return json."""
        return self.content

    @property
    def request(self):
        """Return a fake request object."""
        return Request(
            body='1234',
            headers={'header': 'some-header'},
            url='http://example.com')


#
# KnowledgeGraph extension fixtures
#


@pytest.fixture()
def kg_app(base_app):
    """Deployer app with KnowledgeGraph extension."""
    from renga_deployer.contrib.knowledge_graph import KnowledgeGraphSync

    base_app.config['KNOWLEDGE_GRAPH_URL'] = 'http://localhost:9000/api'
    KnowledgeGraphSync(base_app)

    with base_app.app_context():
        if database_exists(db.engine.url):
            # drop_database(db.engine.url)
            raise RuntimeError('Database exists')
        create_database(db.engine.url)
        db.create_all()

        yield base_app

        db.drop_all()
        drop_database(db.engine.url)

        base_app.extensions['renga-knowledge-graph-sync'].disconnect()


named_type_response = Response([{
    'name':
    'context',
    'properties': [{
        'name': 'context_id',
        'data_type': 'string',
        'cardinality': 'single'
    }, {
        'name': 'context_spec_image',
        'data_type': 'string',
        'cardinality': 'single'
    }, {
        'name': 'context_spec_ports',
        'data_type': 'string',
        'cardinality': 'single'
    }]
}, {
    'name':
    'execution',
    'properties': [{
        'name': 'execution_id',
        'data_type': 'string',
        'cardinality': 'single'
    }, {
        'name': 'execution_engine',
        'data_type': 'string',
        'cardinality': 'single'
    }, {
        'name': 'execution_namespace',
        'data_type': 'string',
        'cardinality': 'single'
    }]
}], 200)


@pytest.fixture()
def kg_requests(monkeypatch):
    """Monkeypatch requests to immitate the KnowledgeGraph."""
    mutation_url = join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                            '/mutation/mutation')
    named_type_url = join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                              '/types/management/named_type')
    token_url = current_app.config['DEPLOYER_TOKEN_URL']

    def kg_post(*args, **kwargs):
        """Override requests.post for KG urls."""
        if mutation_url in args[0]:
            """Override /api/mutation/mutation."""
            return Response({'uuid': '1234'}, 201)
        elif token_url in args[0]:
            """Override fetching access tokens."""
            return Response({'access_token': '1234'}, 200)
        else:
            return r_post(*args, **kwargs)

    def kg_get(*args, **kwargs):
        """Overrides requests.get for KG URLs."""
        if mutation_url in args[0]:
            """Override /api/mutation/mutation/uuid."""
            return Response({
                'status': 'completed',
                'response': {
                    'event': {
                        'status': 'success',
                        'results': [{
                            'id': 1234
                        }]
                    }
                }
            }, 200)

        elif named_type_url in args[0]:
            """Override /api/types/management/named_type."""
            return named_type_response
        else:
            return r_get(*args, **kwargs)

    monkeypatch.setattr(requests, 'get', kg_get)
    monkeypatch.setattr(requests, 'post', kg_post)


#
# ResourceManager extension fixtures
#


@pytest.fixture()
def rm_app(app, keypair, monkeypatch):
    """Deployer app with ResourceManager extension."""
    # from renga_deployer.app import app
    from renga_deployer.contrib.resource_manager import ResourceManager

    private, public = keypair
    token = jwt.encode(
        {
            'name':
            'John Doe',
            'iss':
            'resource-manager',
            'https://rm.datascience.ch/scope': [
                'deployer:contexts_write', 'deployer:contexts_read',
                'deployer:executions_write', 'deployer:executions_read'
            ]
        },
        key=private,
        algorithm='RS256')

    app.config['RESOURCE_MANAGER_URL'] = 'http://localhost:9000/api'
    app.config['DEPLOYER_JWT_KEY'] = public
    app.config['DEPLOYER_JWT_ISSUER'] = 'resource-manager'

    def rm_post(*args, **kwargs):
        """Override post request to the ResourceManager."""
        if current_app.config['RESOURCE_MANAGER_URL'] == args[0]:
            headers = kwargs.get('headers')
            if headers is None or 'Authorization' not in headers:
                return Response({}, 401)

            return Response({'access_token': token}, 200)
        else:
            return r_post(*args, **kwargs)

    monkeypatch.setattr(requests, 'post', rm_post)

    with app.app_context():
        ResourceManager(app)
        yield app


#
# Extension tests
#


def test_kg_extension(kg_app):
    """Test that the extension is added."""
    assert 'renga-knowledge-graph-sync' in kg_app.extensions


def test_kg_serialization(kg_app, deployer, kg_requests):
    """Test serialization of a context."""
    from renga_deployer.contrib.knowledge_graph import vertex_operation

    # disconnect the signal handlers
    kg_app.extensions['renga-knowledge-graph-sync'].disconnect()

    context = deployer.create({'image': 'hello-world'})
    operation = vertex_operation(context, temp_id=0)
    assert len(operation['element']['properties']) == 2

    context = deployer.create({'image': 'hello-world', 'ports': {9999: 9999}})
    operation = vertex_operation(context, temp_id=0)
    assert len(operation['element']['properties']) == 3

    execution = deployer.launch(context, engine='docker')
    operation = vertex_operation(context, temp_id=0)
    assert len(operation['element']['properties']) == 3

    with pytest.raises(NotImplementedError):
        vertex_operation(1, 0)


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_kg_handlers(kg_app, auth_header, kg_requests, engine):
    """Test Context and Execution creation handlers."""
    with kg_app.test_client() as client:
        # 1. test context creation
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world',
                'namespace': 'default'
            }),
            content_type='application/json',
            headers=auth_header)

        context = json.loads(resp.data.decode())
        assert 'labels' in context['spec']
        assert 'renga.execution_context.vertex_id=1234' in context['spec'][
            'labels']

        # 2. test execution creation
        resp = client.post(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            data=json.dumps({
                'engine': engine
            }),
            content_type='application/json',
            headers=auth_header)
        execution = Execution.query.get(json.loads(
            resp.data.decode())['identifier'])

        assert 'RENGA_VERTEX_ID' in current_app.extensions[
            'renga-deployer'].deployer.ENGINES[
                engine]().get_execution_environment(execution)

        # 3. cleanup jobs
        time.sleep(5)
        client.delete(
            'v1/contexts/{0}/executions/{1}'.format(context['identifier'],
                                                    execution.id),
            headers=auth_header)


def test_missing_kg_endpoint(kg_app, auth_header, kg_requests, monkeypatch):
    """Test that missing the mutation service is handled gracefully."""
    mutation_url = join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                            '/mutation/mutation')
    token_url = current_app.config['DEPLOYER_TOKEN_URL']

    def kg_post(*args, **kwargs):
        """Override requests.post for KG urls."""
        if mutation_url in args[0]:
            """Override /api/mutation/mutation."""
            return Response({}, 404)
        elif token_url in args[0]:
            """Override fetching access tokens."""
            return Response({'access_token': '1234'}, 200)

    monkeypatch.setattr(requests, 'post', kg_post)

    with kg_app.test_client() as client:
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world',
                'namespace': 'default'
            }),
            content_type='application/json',
            headers=auth_header)

    assert resp.status_code == 504


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_failed_mutation(kg_app, auth_header, kg_requests, monkeypatch,
                         engine):
    """Test response to mutation failure."""
    with kg_app.test_client() as client:
        # 1. test context creation
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world',
                'namespace': 'default'
            }),
            content_type='application/json',
            headers=auth_header)

        context = json.loads(resp.data.decode())

    mutation_url = join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                            '/mutation/mutation')
    named_type_url = join_url(current_app.config['KNOWLEDGE_GRAPH_URL'],
                              '/types/management/named_type')

    def kg_get_failed(*args, **kwargs):
        """Overrides requests.get for KG URLs."""
        if mutation_url in args[0]:
            """Override /api/mutation/mutation/uuid."""
            return Response({
                'status': 'completed',
                'response': {
                    'event': {
                        'status': 'failed',
                        'results': [{
                            'id': 1234
                        }]
                    }
                }
            }, 200)
        elif named_type_url in args[0]:
            """Override /api/types/management/named_type."""
            return named_type_response
        else:
            return r_get(*args, **kwargs)

    monkeypatch.setattr(requests, 'get', kg_get_failed)

    # 2. test failure due to failed mutation
    with kg_app.test_client() as client:
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world',
                'namespace': 'default'
            }),
            content_type='application/json',
            headers=auth_header)
        assert resp.status_code == 500

        # 2. test failure during execution creation
        resp = client.post(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            data=json.dumps({
                'engine': engine
            }),
            content_type='application/json',
            headers=auth_header)
        assert resp.status_code == 500


def test_rm_extension(app, keypair, monkeypatch):
    """Test that the extension is added."""
    from renga_deployer.contrib.resource_manager import ResourceManager
    private, public = keypair

    app.config['DEPLOYER_JWT_KEY'] = None
    with pytest.raises(RuntimeError):
        ResourceManager(app)

    app.config['DEPLOYER_JWT_KEY'] = public
    ResourceManager(app)

    assert 'renga-resource-manager' in app.extensions
    assert app.config['DEPLOYER_JWT_KEY'] == public


def test_rm_authorization(rm_app, auth_header):
    """Test fetching ResourceManager tokens."""
    from renga_deployer.contrib import resource_manager
    access_token = resource_manager.request_authorization_token(
        auth_header, {'payload': '1234'})

    assert access_token

    access_token = resource_manager.request_authorization_token(
        {}, {'payload': '1234'})

    assert access_token is None


def test_rm_decorator(rm_app, auth_header):
    """Test the functioning of resource_manager_authorization decorator."""
    with rm_app.test_client() as client:
        # context creation should succeed
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world'
            }),
            content_type='application/json',
            headers=auth_header)
