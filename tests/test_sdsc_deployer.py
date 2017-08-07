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
"""Module tests."""

import json

import pytest
from flask import Flask

from sdsc_deployer import SDSCDeployer
from sdsc_deployer.ext import current_deployer
from sdsc_deployer.models import Context, db


def test_version():
    """Test version import."""
    from sdsc_deployer import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = SDSCDeployer(app)
    assert 'sdsc-deployer' in app.extensions

    app = Flask('testapp')
    ext = SDSCDeployer()
    assert 'sdsc-deployer' not in app.extensions
    ext.init_app(app)
    assert 'sdsc-deployer' in app.extensions


def test_view(app):
    """Test view."""
    SDSCDeployer(app)
    with app.test_client() as client:
        res = client.get("/")
        assert res.status_code == 200
        assert 'Welcome to SDSC-Deployer' in str(res.data)


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_context_execution(app, engine, no_auth_connexion):
    """Test context execution."""

    with app.test_client() as client:
        # create a context
        resp = client.post(
            'v1/contexts',
            data=json.dumps({
                'image': 'hello-world'
            }),
            content_type='application/json', )

        assert resp.status_code == 201

        context = json.loads(resp.data)
        assert context
        assert 'identifier' in context

        resp = client.post(
            'v1/contexts/{0}/executions'.format(context['identifier']),
            data=json.dumps({
                'engine': engine
            }),
            content_type='application/json', )

        assert resp.status_code == 201

        execution = json.loads(resp.data)
        assert execution
        assert 'identifier' in execution

        resp = client.get(
            'v1/contexts/{0}/executions/{1}'.format(context['identifier'],
                                                    execution['identifier']), )

        assert resp.status_code == 200
        assert execution == json.loads(resp.data)

        listing = json.loads(
            client.get(
                'v1/contexts/{0}/executions'.format(context['identifier']), )
            .data)

        assert execution in listing['executions']


def test_context_get(app):
    """Test context storage."""
    data = {'image': 'hello-world'}

    with app.test_client() as client:
        context = json.loads(
            client.post(
                'v1/contexts',
                data=json.dumps(data),
                content_type='application/json', ).data)

        listing = json.loads(client.get('v1/contexts').data)
        assert context in listing['contexts']

        resp = client.get('v1/contexts/{0}'.format(context['identifier']))
        assert resp.status_code == 200
        assert context == json.loads(resp.data)


def test_storage_clear(app):
    """Test that storage gets cleared."""
    Context.create(spec={'image': 'hello-world'})

    with app.test_client() as client:
        listing = json.loads(client.get('v1/contexts').data)
        assert listing['contexts']

        Context.query.delete()
        db.session.commit()

        listing = json.loads(client.get('v1/contexts').data)
        assert not listing['contexts']


def test_storage_append(app):
    """Test that multiple contexts get added."""

    with app.test_client() as client:
        data = {'image': 'hello-world'}

        resp = client.post(
            'v1/contexts',
            data=json.dumps(data),
            content_type='application/json', )
        assert resp.status_code == 201
        listing = json.loads(client.get('v1/contexts').data)
        assert len(listing['contexts']) == 1

        resp = client.post(
            'v1/contexts',
            data=json.dumps(data),
            content_type='application/json', )
        assert resp.status_code == 201
        listing = json.loads(client.get('v1/contexts').data)
        assert len(listing['contexts']) == 2
