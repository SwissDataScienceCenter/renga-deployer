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
"""Contrib modules tests."""

import json

import pytest
import requests
from flask import current_app
from jose import jwt

from sdsc_deployer import contrib
from sdsc_deployer.utils import join_url

r_get = requests.get
r_post = requests.post


class Response(object):
    """Fake response."""

    def __init__(self, data, status_code):
        """Initialize fake response object with a json."""
        self.data = data
        self.status_code = status_code

    def json(self):
        """Return json."""
        return self.data


#
# KnowledgeGraph extension fixtures
#


@pytest.fixture()
def kg_app(app):
    """Deployer app with KnowledgeGraph extension."""
    from sdsc_deployer.contrib.knowledge_graph import KnowledgeGraphSync

    with app.app_context():
        KnowledgeGraphSync(app)
        yield app
        app.extensions['sdsc-knowledge-graph-sync'].disconnect()


@pytest.fixture()
def kg_requests(monkeypatch):
    """Monkeypatch requests to immitate the KnowledgeGraph."""
    mutation_url = join_url(current_app.config['PLATFORM_SERVICE_API'],
                            '/mutation/mutation')
    named_type_url = join_url(current_app.config['PLATFORM_SERVICE_API'],
                              '/types/management/named_type')

    def kg_post(*args, **kwargs):
        """Override requests.post for KG urls."""
        if mutation_url in args[0]:
            """Override /api/mutation/mutation."""
            return Response({'uuid': '1234'}, 201)
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
            return Response([{
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
    # from sdsc_deployer.app import app
    from sdsc_deployer.contrib.resource_manager import ResourceManager

    private, public = keypair
    token = jwt.encode(
        {
            'name':
            'John Doe',
            'iss':
            'resource-manager',
            'https://rm.datascience.ch/scope': [
                'contexts:write', 'contexts:read', 'executions:write',
                'executions:read'
            ]
        },
        key=private,
        algorithm='RS256')

    def rm_post(*args, **kwargs):
        """Override post request to the ResourceManager."""
        if join_url(current_app.config['PLATFORM_SERVICE_API'],
                    '/resource-manager/authorize') == args[0]:
            headers = kwargs.get('headers')
            if headers is None or 'Authorization' not in headers:
                return Response({}, 401)

            return Response({'access_token': token}, 200)
        else:
            return r_post(*args, **kwargs)

    monkeypatch.setattr(requests, 'post', rm_post)
    app.config['RESOURCE_MANAGER_PUBLIC_KEY'] = public

    with app.app_context():
        ResourceManager(app)
        yield app


#
# Extension tests
#


def test_kg_extension(kg_app):
    """Test that the extension is added."""
    assert 'sdsc-knowledge-graph-sync' in kg_app.extensions


def test_kg_serialization(kg_app, deployer, kg_requests):
    """Test serialization of a context."""
    from sdsc_deployer.contrib.knowledge_graph import vertex_operation

    # disconnect the signal handlers
    kg_app.extensions['sdsc-knowledge-graph-sync'].disconnect()

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


def test_kg_handlers(kg_app, auth_header, kg_requests):
    """Test Context and Execution creation handlers."""
    with kg_app.test_client() as client:
        # 1. test context creation
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world'
            }),
            content_type='application/json',
            headers=auth_header)

        # 2. test execution creation
        context = json.loads(resp.data)
        resp = client.post(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            data=json.dumps({
                'engine': 'docker'
            }),
            content_type='application/json',
            headers=auth_header)


def test_rm_extension(app, keypair, monkeypatch):
    """Test that the extension is added."""
    from sdsc_deployer.contrib.resource_manager import ResourceManager
    private, public = keypair

    with pytest.raises(RuntimeError):
        ResourceManager(app)

    app.config['RESOURCE_MANAGER_PUBLIC_KEY'] = public
    ResourceManager(app)

    assert 'sdsc-resource-manager' in app.extensions
    assert app.config['RESOURCE_MANAGER_PUBLIC_KEY'] == public


def test_rm_authorization(rm_app, auth_header):
    """Test fetching ResourceManager tokens."""
    from sdsc_deployer.contrib import resource_manager
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
