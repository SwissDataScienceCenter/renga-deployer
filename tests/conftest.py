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


@pytest.fixture()
def access_token():
    """Retrieve an authorization token from keycloak."""
    if os.getenv('DEPLOYER_TOKEN_URL'):
        resp = requests.post(
            os.getenv('DEPLOYER_TOKEN_URL'),
            data={
                'grant_type': 'password',
                'username': 'demo',
                'password': 'demo',
                'client_id': 'demo-client',
                'client_secret': '5294a18e-e784-4e39-a927-ce816c91c83e'
            })
        access_token = resp.json()['access_token']
    else:
        access_token = 'eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA'\
                       '6ICJtaDdxbEtWTGdTXzh6QkNhc3EtdFhCbU4tcUs4LWdIa1N'\
                       'Jb21RZHkyUmpzIn0.eyJqdGkiOiI2YTE2Yjk1My02MjdhLTQ'\
                       '3NWMtYTc5ZS1mNTdlNjQ5YjczMGMiLCJleHAiOjE1MDE4NDk'\
                       '0OTEsIm5iZiI6MCwiaWF0IjoxNTAxODQ2NDkxLCJpc3MiOiJ'\
                       'odHRwOi8vbG9jYWxob3N0OjgwODAvYXV0aC9yZWFsbXMvU0R'\
                       'TQyIsImF1ZCI6ImRlbW8tY2xpZW50Iiwic3ViIjoiZTE0NGI'\
                       'yMzUtNzkzYi00ZTJlLWJiMWYtMWY4YmFjY2MzMjFmIiwidHl'\
                       'wIjoiQmVhcmVyIiwiYXpwIjoiZGVtby1jbGllbnQiLCJhdXR'\
                       'oX3RpbWUiOjAsInNlc3Npb25fc3RhdGUiOiJjNGQ3ZjI2Ni0'\
                       '5YTFjLTQwNzItODc3OS1lMjg0MWNkYWNiODkiLCJhY3IiOiI'\
                       'xIiwiYWxsb3dlZC1vcmlnaW5zIjpbImh0dHA6Ly9sb2NhbGh'\
                       'vc3Q6OTAwMSJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOls'\
                       'ib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJ'\
                       'dfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9'\
                       'sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3V'\
                       'udC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sIm5hbWUiOiJ'\
                       'Kb2huIERvZSIsInByZWZlcnJlZF91c2VybmFtZSI6ImRlbW8'\
                       'iLCJnaXZlbl9uYW1lIjoiSm9obiIsImZhbWlseV9uYW1lIjo'\
                       'iRG9lIiwiZW1haWwiOiJkZW1vQGRhdGFzY2llbmNlLmNoIn0'\
                       '.AWA9-GY7sasT8n9DdS7ujefpeC-C8X0MmVGQHzHbySOlygw'\
                       'HqBykND0taNB953KrpzLUPBCUO8NZGMi2zCy1MLKLFj3aDqC'\
                       'jxtxOBOE0TzbbLSUzQ2lmijhbrP_E-g6oFZQUPaHNpAhP7Xt'\
                       'cDLTs0iDJmw1Zoi5RAvYLlD3raN6ZmiPidfKTteappHXPrXm'\
                       'aXBZJ1TWASUlrkExT6sHd7Ut4wZ_xFd5fo0js1ln3b_g6znp'\
                       'cAW2ex84r9l3JWNvaVom6q2w2S6txoARS4AReA_F_TTGrOIJ'\
                       'q0AIGuF-MwKvjpYpdBpwxa2tYVTDFQF27_IL-2UgtjwsLgKH'\
                       'Hvo482Q'

    return access_token
