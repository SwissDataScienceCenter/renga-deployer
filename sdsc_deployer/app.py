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

import os

import connexion
from connexion.resolver import RestyResolver
from flask_babelex import Babel

from .ext import SDSCDeployer
from .models import db

api = connexion.App(__name__, specification_dir='schemas/', swagger_ui=True)
api.add_api(
    'sdsc-deployer-v1.yaml',
    resolver=RestyResolver('sdsc_deployer.api'), )  # validate_responses=True)

Babel(api.app)
api.app.config.setdefault(
    'SQLALCHEMY_DATABASE_URI',
    os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///deployer.db'), )
db.init_app(api.app)
SDSCDeployer(api.app)

app = api.app
