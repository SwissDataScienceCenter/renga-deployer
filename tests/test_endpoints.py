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
"""Module tests."""

import json

import pytest
from flask import Flask
from werkzeug.exceptions import BadRequest

from renga_deployer import RengaDeployer
from renga_deployer.ext import current_deployer
from renga_deployer.models import Context, Execution, db


def test_version():
    """Test version import."""
    from renga_deployer import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = RengaDeployer(app)
    assert 'renga-deployer' in app.extensions

    app = Flask('testapp')
    ext = RengaDeployer()
    assert 'renga-deployer' not in app.extensions
    ext.init_app(app)
    assert 'renga-deployer' in app.extensions


def test_view(app):
    """Test view."""
    RengaDeployer(app)
    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == 200
        assert 'Welcome to Renga-Deployer' in str(res.data)


def test_token_check(app, auth_header):
    """Test that token exists in header."""
    with app.test_client() as client:
        # should fail with 401 unauthorized
        resp = client.get('v1/contexts')
        assert resp.status_code == 401

        # should pass
        resp = client.get('v1/contexts', headers=auth_header)
        assert resp.status_code == 200


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_context_execution(app, engine, no_auth_connexion, auth_data,
                           auth_header):
    """Test context execution."""

    with app.test_client() as client:

        # 1. create a context
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world'
            }),
            content_type='application/json',
            headers=auth_header)

        assert resp.status_code == 201

        context = json.loads(resp.data)
        assert context
        assert 'identifier' in context

        # 2. launch an execution of a context
        resp = client.post(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            data=json.dumps({
                'engine': engine
            }),
            content_type='application/json',
            headers=auth_header)

        assert resp.status_code == 201

        execution = json.loads(resp.data)
        assert execution
        assert 'identifier' in execution

        # 3. get a listing of all executions of a context
        resp = client.get(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            headers=auth_header)

        assert resp.status_code == 200
        assert json.loads(resp.data)['executions']

        # 4. get the details of an execution of a context
        resp = client.get(
            'v1/contexts/{0}/executions/{1}'.format(context['identifier'],
                                                    execution['identifier']),
            headers=auth_header)

        assert resp.status_code == 200
        assert all(
            list(execution[k] == v for k, v in json.loads(resp.data).items()
                 if k != 'state'))

        listing = json.loads(
            client.get(
                'v1/contexts/{0}/executions'.format(context['identifier']),
                headers=auth_header).data)

        assert execution['identifier'] in [
            e['identifier'] for e in listing['executions']
        ]

        # 5. get the logs of an execution
        assert b'Hello from Docker!' in client.get(
            'v1/contexts/{0}/executions/{1}/logs'.format(
                context['identifier'], execution['identifier']),
            headers=auth_header).data

        # 6. remove the execution from the engine
        client.delete(
            'v1/contexts/{0}/executions/{1}'.format(context['identifier'],
                                                    execution['identifier']),
            headers=auth_header)
        if engine == 'docker':
            import docker
            client = docker.from_env()
            execution = Execution.query.get(execution['identifier'])
            engine_id = execution.engine_id
            assert not any(c.short_id in engine_id
                           for c in client.containers.list())
            assert execution.jwt == auth_data
            assert execution.context.jwt == auth_data


def test_context_get(app, auth_header):
    """Test context storage."""
    data = {'image': 'hello-world'}

    with app.test_client() as client:
        context = json.loads(
            client.post(
                'v1/contexts',
                data=json.dumps(data),
                content_type='application/json',
                headers=auth_header).data)

        listing = json.loads(
            client.get('v1/contexts', headers=auth_header).data)
        assert context in listing['contexts']

        resp = client.get(
            'v1/contexts/{0}'.format(context['identifier']),
            headers=auth_header)
        assert resp.status_code == 200
        assert context == json.loads(resp.data)

        resp = client.get('v1/contexts/0', headers=auth_header)
        assert resp.status_code == 400
