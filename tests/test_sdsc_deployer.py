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

from flask import Flask
import pytest

from sdsc_deployer import SDSCDeployer

base_data = {
    'env': {
        'image': 'hello-world',
    }
}


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
    """Test docker node deployment"""
    with app.test_client() as client:
        # create a node
        data = base_data
        data['env']['engine'] = engine

        if engine == 'k8s':
            data['env']['namespace'] = 'default'

        resp = client.post(
            'v1/nodes', data=json.dumps(data), content_type='application/json')

        assert resp.status_code == 201

        resp_data = json.loads(resp.data)
        assert resp_data
        assert 'identifier' in resp_data.keys()


def test_node_get(app):
    """Test local node storage"""
    with app.test_client() as client:
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing)


def test_storage_clear(app):
    """Test that storage gets cleared"""
    from sdsc_deployer.nodes import Node, storage_clear_all

    node = Node()
    with app.test_client() as client:
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing) > 0

        storage_clear_all()
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing) == 0


def test_storage_append(app):
    """Test that multiple nodes get added"""
    from sdsc_deployer.nodes import Node, storage_clear_all

    storage_clear_all()

    with app.test_client() as client:
        node1 = Node()
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing) == 1

        node2 = Node()
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing) == 2
