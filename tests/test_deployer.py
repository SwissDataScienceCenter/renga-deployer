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
import requests
from flask import Flask
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from renga_deployer.deployer import Deployer
from renga_deployer.models import Context, Execution, ExecutionStates


def test_deployer_env_create(monkeypatch):
    """Test creation from environment."""
    monkeypatch.setenv('DEPLOYER_ENGINE_DOCKER',
                       'docker:///var/lib/docker.sock')

    d = Deployer.from_env()

    assert 'docker' in d.engines


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
@pytest.mark.parametrize('spec', [{
    'image': 'hello-world'
}, {
    'image': 'hello-world',
    'ports': ['', '9999']
}])
def test_execution_launch(app, engine, spec, deployer):
    """Test node launching."""
    context = deployer.create(spec)
    execution = deployer.launch(context, engine=engine)

    assert isinstance(context, Context)
    assert isinstance(execution, Execution)
    assert execution.engine == engine

    while True:
        if execution.check_state(
            [ExecutionStates.RUNNING,
             ExecutionStates.EXITED], deployer.ENGINES[engine]()):
            break
    assert 'Hello from Docker!' in deployer.get_logs(execution)

    deployer.stop(execution, remove=True)


@pytest.mark.parametrize('engine', ['docker', 'k8s'])
@pytest.mark.parametrize('image', ['alpine', 'alpine:latest'])
def test_open_port(app, engine, image, deployer):
    """Test that engines make a port available."""

    context = deployer.create({
        'image':
        image,
        'command':
        'sh -c "mkfifo /tmp/f; cat /tmp/f | nc -l -p 9999 > /tmp/f"',
        'ports': [
            '9999',
        ],
    })
    execution = deployer.launch(context, engine=engine)

    # connect to the job and do send/receive
    while True:
        if execution.check_state(ExecutionStates.RUNNING,
                                 deployer.ENGINES[engine]()):
            break
    time.sleep(10)
    s = socket.socket()
    try:
        binding = deployer.get_host_ports(execution)['ports'][0]
        s.connect((binding['host'], int(binding['exposed'])))
        phrase = b'earth_calling'
        s.send(phrase)
        received = s.recv(100)
        assert received == phrase
        assert execution.check_state(ExecutionStates.RUNNING,
                                     deployer.ENGINES[engine]())
    except Exception as e:
        raise e

    finally:
        deployer.stop(execution, remove=True)
        s.close()


@pytest.mark.parametrize('engine', ['k8s'])
@pytest.mark.parametrize('image', ['nginx'])
def test_open_ingress(app, engine, image, deployer):
    """Test that k8s ingress is correctly deployed and accessible."""

    app.config['DEPLOYER_K8S_INGRESS'] = 'nginx'

    context = deployer.create({
        'image':
        image,
        'ports': [
            '80',
        ],
    })
    execution = deployer.launch(context, engine=engine)

    # connect to the job and do send/receive
    while True:
        if execution.check_state(ExecutionStates.RUNNING,
                                 deployer.ENGINES[engine]()):
            break

    s = socket.socket()
    try:

        while not deployer.get_host_ports(execution)['ports'][0]['host']:
            time.sleep(1)

        binding = deployer.get_host_ports(execution)['ports'][0]
        time.sleep(5)
        with pytest.warns(InsecureRequestWarning):
            response = requests.get("https://{}:{}{}".format(
                binding['host'],
                binding['exposed'],
                binding['path']
            ), verify=False)

        assert response.status_code == 404
        assert b'nginx' in response.content
        assert execution.check_state(ExecutionStates.RUNNING,
                                     deployer.ENGINES[engine]())
    except Exception as e:
        raise e

    finally:
        deployer.stop(execution, remove=True)
        s.close()
