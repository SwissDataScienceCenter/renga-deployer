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

from __future__ import absolute_import, print_function

import json

from flask import Flask

from sdsc_deployer import SDSCDeployer

post_data = json.dumps({
    'app_id': 0,
    'deploy_id': 0,
    'docker_image': 'hello-world',
    'network_ports': 0
})


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


def test_node_post(app):
    """Test docker node deployment"""
    with app.test_client() as client:
        # create one node
        resp = client.post(
            'v1/nodes', data=post_data, content_type='application/json')
        assert resp.status_code == 201
        resp_data = json.loads(resp.data)
        assert resp_data
        assert 'identifier' in resp_data.keys()


def test_node_get(app):
    """Test local node storage"""
    with app.test_client() as client:
        client.post(
            'v1/nodes', data=post_data, content_type='application/json')
        listing = json.loads(client.get('v1/nodes').data)
        assert len(listing) == 2
