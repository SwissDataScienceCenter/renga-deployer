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

import shutil
import tempfile

import pytest
from sqlalchemy_utils.functions import create_database, database_exists, \
    drop_database

from sdsc_deployer.deployer import Deployer
from sdsc_deployer.models import db


@pytest.yield_fixture()
def instance_path():
    """Temporary instance path."""
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.fixture()
def base_app(instance_path):
    """Flask application fixture."""
    from sdsc_deployer.app import app
    app.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        # SQLALCHEMY_DATABASE_URI='sqlite:///{0}/test.db'.format(instance_path),
        SECRET_KEY='SECRET_KEY',
        TESTING=True, )
    yield app


@pytest.yield_fixture()
def app(base_app):
    """Flask application fixture."""
    with base_app.app_context():
        if database_exists(db.engine.url):
            drop_database(db.engine.url)
            # raise RuntimeError('Database exists')
        create_database(db.engine.url)
        db.create_all()

    with base_app.app_context():
        yield base_app

    with base_app.app_context():
        db.drop_all()
        drop_database(db.engine.url)


@pytest.fixture()
def deployer():
    """Initiate a deployer."""
    return Deployer(engines={'docker': 'docker:///var/lib/docker.sock'})
