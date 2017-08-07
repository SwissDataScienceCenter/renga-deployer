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
"""Pytest configuration."""

import os
import shutil
import tempfile

import pytest
import requests
from jose import jwt
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from sdsc_deployer.app import create_app
from sdsc_deployer.deployer import Deployer
from sdsc_deployer.models import db


@pytest.fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture(scope='module')
def base_app():
    """Flask application fixture."""
    app = create_app()
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # SQLALCHEMY_DATABASE_URI='sqlite:///{0}/test.db'.format(instance_path),
        SECRET_KEY='SECRET_KEY',
        TESTING=True, )
    yield app


@pytest.fixture(scope='module')
def app(base_app):
    """Flask application fixture."""
    with base_app.app_context():
        if database_exists(db.engine.url):
            drop_database(db.engine.url)
            # raise RuntimeError('Database exists')
        create_database(db.engine.url)
        db.create_all()

        yield base_app

        db.drop_all()
        drop_database(db.engine.url)


@pytest.fixture(scope='module')
def kg_app(app):
    """Deployer app with Knowledge Graph extension."""
    # from sdsc_deployer.app import app
    from sdsc_deployer.contrib.knowledge_graph import KnowledgeGraphSync

    with app.app_context():
        KnowledgeGraphSync(app)
        yield app
        app.extensions['sdsc-knowledge-graph-sync'].disconnect()


@pytest.fixture()
def deployer():
    """Initiate a deployer."""
    return Deployer(engines={'docker': 'docker:///var/lib/docker.sock'})


@pytest.fixture(autouse=True)
def no_auth_connexion(monkeypatch):
    """Turn off authorization checking in connexion."""
    import connexion

    def security_passthrough(x, func):
        return func

    monkeypatch.setattr(connexion.operation.SecureOperation,
                        'security_decorator', security_passthrough)


@pytest.fixture()
def key():
    """Provide a key for token de/encription."""
    return 'a1234'


@pytest.fixture()
def auth_header(key):
    """Provide a header with a JWT bearer token."""
    return {
        'Authorization':
        'Bearer {0}'.format(jwt.encode(
            {
                'typ': 'Bearer',
                'name': 'John Doe'
            }, key='a1234'))
    }
