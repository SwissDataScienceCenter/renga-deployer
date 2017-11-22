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
"""Deployer sub-module."""

import logging
import os

from blinker import Namespace

from . import engines
from .models import Context, Execution, db

deployer_signals = Namespace()

context_created = deployer_signals.signal('context-created')
execution_created = deployer_signals.signal('execution-created')
execution_launched = deployer_signals.signal('execution-launched')

logger = logging.getLogger('renga.deployer.deployer')


class Deployer(object):
    """Handling the executions of contexts."""

    ENGINES = {'docker': engines.DockerEngine, 'k8s': engines.K8SEngine}

    def __init__(self, engines=None, **kwargs):
        """Create a Deployer instance.

        :param engines: dict of engine name:uri pairs
        """
        self.engines = engines or {}

    @classmethod
    def from_env(cls, prefix='DEPLOYER_'):
        """Create a Deployer from environment variables."""
        engines = {}

        # grab engine definitions
        engine_prefix = prefix + 'ENGINE_'
        for key in os.environ:
            if key.startswith(engine_prefix):
                engine = key[len(engine_prefix):].lower()
                engines[engine] = os.environ[key]

        return cls(engines=engines)

    def create(self, spec):
        """Create a context with a given specification."""
        context = Context.create(spec=spec)
        db.session.add(context)
        context_created.send(context)
        db.session.commit()
        return context

    def launch(self, context=None, engine=None, **kwargs):
        """Create new execution for a given context."""
        execution = Execution.from_context(context, engine=engine, **kwargs)
        db.session.add(execution)
        execution_created.send(execution)

        execution = self.ENGINES[engine]().launch(execution)
        execution_launched.send(execution)

        db.session.commit()
        return execution

    def stop(self, execution, remove=False):
        """Stop a running execution, optionally removing it from engine."""
        self.ENGINES[execution.engine]().stop(execution, remove=remove)

    def get_logs(self, execution):
        """Ask engine to extract logs."""
        # FIXME use configuration
        return self.ENGINES[execution.engine]().get_logs(execution)

    def get_host_ports(self, execution):
        """Fetch hostname and ports for the running execution."""
        return self.ENGINES[execution.engine]().get_host_ports(execution)

    def get_state(self, execution):
        """Fetch the status of a running job."""
        return self.ENGINES[execution.engine]().get_state(execution)
