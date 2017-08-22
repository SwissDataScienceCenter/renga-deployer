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
"""Deployer sub-module."""

import os

from blinker import Namespace

from . import engines
from .models import Context, Execution

deployer_signals = Namespace()

context_created = deployer_signals.signal('context-created')
execution_created = deployer_signals.signal('execution-created')


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
        context_created.send(context)
        return context

    def launch(self, context=None, engine=None, **kwargs):
        """Create new execution environment for a given context."""
        execution = self.ENGINES[engine](  # FIXME use configuration
        ).launch(
            context, engine=engine, **kwargs)
        execution_created.send(execution)
        return execution

    def get_logs(self, execution):
        """Ask engine to extract logs."""
        return self.ENGINES[execution.engine](  # FIXME use configuration
        ).get_logs(execution)
