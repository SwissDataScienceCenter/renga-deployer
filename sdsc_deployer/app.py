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
"""SDSC Deployer application."""

import logging
import os
import sys

import connexion
from connexion.resolver import RestyResolver
from flask import jsonify, request
from flask_babelex import Babel
from jose import jwt
from sqlalchemy_utils import functions

from . import config
from .ext import SDSCDeployer
from .models import db

logging.basicConfig(level=logging.INFO)


def create_app(**kwargs):
    """Create an instance of the flask app."""
    api = connexion.App(
        __name__, specification_dir='schemas/')
    api.app.config.from_object(config)
    api.app.config.update(**config.from_env(config))
    api.app.config.update(**kwargs)

    api.add_api(
        'sdsc-deployer-v1.yaml',
        arguments=api.app.config,
        resolver=RestyResolver('sdsc_deployer.api'),
        swagger_ui=api.app.config['DEPLOYER_SWAGGER_UI'],
    )  # validate_responses=True)

    Babel(api.app)
    db.init_app(api.app)
    SDSCDeployer(api.app)

    # add extensions
    if api.app.config['KNOWLEDGE_GRAPH_URL']:
        from .contrib.knowledge_graph import KnowledgeGraphSync
        KnowledgeGraphSync(api.app)

    if api.app.config['RESOURCE_MANAGER_URL']:
        from .contrib.resource_manager import ResourceManager
        ResourceManager(api.app)

    # create database and tables
    with api.app.app_context():
        if not functions.database_exists(db.engine.url):
            functions.create_database(db.engine.url)

        db.create_all()

    return api.app
