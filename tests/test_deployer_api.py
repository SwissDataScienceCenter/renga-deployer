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
"""Deployer sub-module tests."""

import pytest
from flask import Flask

from sdsc_deployer.deployer import Deployer
from sdsc_deployer.nodes import ExecutionEnvironment, Node


def test_deployer_env_create(monkeypatch):
    """Test creation from environment."""
    monkeypatch.setenv('DEPLOYER_ENGINE_DOCKER',
                       'docker:///var/lib/docker.sock')

    d = Deployer.from_env()

    assert 'docker' in d.engines


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_node_launch(engine, deployer):
    """Test node launching."""
    node = deployer.create(data={'image': 'hello-world'})
    execution = deployer.launch(node, engine=engine)

    assert isinstance(node, Node)
    assert isinstance(execution, ExecutionEnvironment)
    assert execution.engine == engine
