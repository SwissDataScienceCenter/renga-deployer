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
from sdsc_deployer.nodes import db


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
def test_node_post(app, engine):
    """Test docker node deployment."""
    with app.test_client() as client:
        # create a node
        data = {'image': 'hello-world'}

        resp = client.post(
            'v1/nodes', data=json.dumps(data), content_type='application/json')

        assert resp.status_code == 201

        resp_data = json.loads(resp.data)
        assert resp_data
        assert 'identifier' in resp_data


def test_node_get(app):
    """Test local node storage."""
    with app.test_client() as client:
        listing = json.loads(client.get('v1/nodes').data)
        assert listing


def test_storage_clear(app):
    """Test that storage gets cleared."""
    from sdsc_deployer.nodes import Node

    node = Node.create({'image': 'hello-world'})
    with app.test_client() as client:
        listing = json.loads(client.get('v1/nodes').data)
        assert listing['nodes']

        Node.query.delete()
        db.session.commit()

        listing = json.loads(client.get('v1/nodes').data)
        assert not listing['nodes']


def test_storage_append(app):
    """Test that multiple nodes get added."""
    with app.test_client() as client:
        data = {'image': 'hello-world'}

        client.post(
            'v1/nodes', data=json.dumps(data), content_type='application/json')
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing['nodes']) == 1

        client.post(
            'v1/nodes', data=json.dumps(data), content_type='application/json')
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing['nodes']) == 2
