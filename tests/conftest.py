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
"""Pytest configuration."""

import os
import shutil
import tempfile

import pytest
from jose import jwt
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from renga_deployer.app import create_app
from renga_deployer.deployer import Deployer
from renga_deployer.models import db


@pytest.fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    """Flask application fixture."""
    app = create_app()
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_DATABASE_URI='sqlite:///{0}/test.db'.format(instance_path),
        SECRET_KEY='SECRET_KEY',
        TESTING=True, )
    yield app


@pytest.fixture()
def app(base_app):
    """Flask application fixture."""
    with base_app.app_context():
        if database_exists(db.engine.url):
            # drop_database(db.engine.url)
            raise RuntimeError('Database exists')
        create_database(db.engine.url)
        db.create_all()

        yield base_app

        db.drop_all()
        drop_database(db.engine.url)


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
def keypair():
    """Provide a keypair for token de/encription."""
    from Crypto.PublicKey import RSA
    new_key = RSA.generate(1024, e=65537)
    public_key = new_key.publickey().exportKey("PEM").decode()
    private_key = new_key.exportKey("PEM").decode()
    return private_key, public_key


@pytest.fixture()
def auth_data():
    """Provide JWT token data."""
    return {
        'typ': 'Bearer',
        'name': 'John Doe',
        'iss': 'http://localhost:8080/auth/realms/Renga',
    }


@pytest.fixture()
def auth_header(keypair, auth_data):
    """Provide a header with a JWT bearer token."""
    private, public = keypair
    token = jwt.encode(auth_data, key=private, algorithm='RS256')
    return {'Authorization': 'Bearer {0}'.format(token)}
