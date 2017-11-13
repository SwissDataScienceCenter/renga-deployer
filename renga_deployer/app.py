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
"""Renga Deployer application."""

import os
import sys
from urllib.parse import urlparse

import connexion
from connexion.resolver import RestyResolver
from flask import jsonify, request
from flask_babelex import Babel
from jose import jwt
from sqlalchemy_utils import functions

from . import config, logging
from .ext import RengaDeployer
from .models import db

logger = logging.getLogger('renga.deployer.app')


def create_app(**kwargs):
    """Create an instance of the flask app."""
    api = connexion.App(__name__, specification_dir='schemas/')
    api.app.config.from_object(config)
    api.app.config.update(**config.from_env(config))
    api.app.config.update(**kwargs)

    api.app.url_map.strict_slashes = False

    deployer_url = urlparse(api.app.config.get('DEPLOYER_URL'))
    api.app.config.setdefault('DEPLOYER_HOST', deployer_url.netloc)
    api.app.config.setdefault('DEPLOYER_SCHEME', deployer_url.scheme)

    api.add_api(
        'renga-deployer-v1.yaml',
        arguments=api.app.config,
        resolver=RestyResolver('renga_deployer.api'),
        swagger_ui=api.app.config['DEPLOYER_SWAGGER_UI'],
    )  # validate_responses=True)

    Babel(api.app)
    db.init_app(api.app)
    RengaDeployer(api.app)

    # add extensions
    if api.app.config['KNOWLEDGE_GRAPH_URL']:
        from .contrib.knowledge_graph import KnowledgeGraphSync
        KnowledgeGraphSync(api.app)

    if api.app.config['RESOURCE_MANAGER_URL']:
        from .contrib.resource_manager import ResourceManager
        ResourceManager(api.app)

    if api.app.config['WSGI_NUM_PROXIES']:
        from werkzeug.contrib.fixers import ProxyFix
        api.app.wsgi_app = ProxyFix(
            api.app.wsgi_app, num_proxies=api.app.config['WSGI_NUM_PROXIES'])

    # create database and tables
    with api.app.app_context():
        if not functions.database_exists(db.engine.url):
            functions.create_database(db.engine.url)
            logger.debug('Database created.')

        db.create_all()
        logger.debug('Database initialized.')

    return api.app
