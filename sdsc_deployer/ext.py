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
"""SDSC Deployer Service."""

from __future__ import absolute_import, print_function

from flask import current_app, g, request
from werkzeug.local import LocalProxy

from . import config
from .deployer import Deployer
from .views import blueprint

try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack

current_deployer = LocalProxy(lambda: current_app.extensions['sdsc-deployer'])


class SDSCDeployer(object):
    """SDSC-Deployer extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        app.register_blueprint(blueprint)
        app.register_blueprint(v1.bp, url_prefix='/v1')
        app.extensions['sdsc-deployer'] = self

        # TOOD replace with a persitent object store
        self.storage = {}

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('DEPLOYER_'):
                app.config.setdefault(k, getattr(config, k))

    @property
    def deployer(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'sdsc_deployer'):
                ctx.sdsc_deployer = Deployer(
                    engines={'docker', 'docker:///var/lib/docker.sock'})
            return ctx.sdsc_deployer
