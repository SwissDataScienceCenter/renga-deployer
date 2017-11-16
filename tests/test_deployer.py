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
"""Deployer sub-module tests."""

import socket
import time

import pytest
from flask import Flask

from renga_deployer.deployer import Deployer
from renga_deployer.models import Context, Execution


def test_deployer_env_create(monkeypatch):
    """Test creation from environment."""
    monkeypatch.setenv('DEPLOYER_ENGINE_DOCKER',
                       'docker:///var/lib/docker.sock')

    d = Deployer.from_env()

    assert 'docker' in d.engines


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
@pytest.mark.parametrize('spec', [
    {'image': 'hello-world'},
    {'image': 'hello-world', 'ports': ['', '9999']},
])
def test_execution_launch(app, engine, spec, deployer):
    """Test node launching."""
    context = deployer.create(spec)
    execution = deployer.launch(context, engine=engine)

    assert isinstance(context, Context)
    assert isinstance(execution, Execution)
    assert execution.engine == engine
    assert 'Hello from Docker!' in deployer.get_logs(execution)

    deployer.stop(execution, remove=True)


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
def test_open_port(app, engine, deployer):
    """Test that engines make a port available."""
    from renga_deployer.utils import resource_available

    context = deployer.create({
        'image':
        'alpine',
        'command':
        'sh -c "mkfifo /tmp/f; cat /tmp/f | nc -l -p 9999 > /tmp/f"',
        'ports': [
            '9999',
        ],
    })
    execution = deployer.launch(context, engine=engine)

    # connect to the job and do send/receive
    time.sleep(20)  # FIXME
    binding = deployer.get_host_ports(execution)['ports'][0]
    timein = time.time()
    s = socket.socket()
    s.connect((binding['host'], int(binding['exposed'])))
    phrase = b'earth_calling'
    s.send(phrase)
    received = s.recv(100)
    assert received == phrase
    deployer.stop(execution, remove=True)
    s.close()
