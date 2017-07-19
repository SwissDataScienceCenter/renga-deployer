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
"""Nodes sub-module tests."""

import pytest

from sdsc_deployer.nodes import DockerNode, K8SNode


@pytest.mark.parametrize('node_cls', [DockerNode, K8SNode])
def test_launching_docker_container(node_cls):
    """Test launching a docker container."""
    node = node_cls(env={
        'userid': 'test-user',
        'name': 'test-job',
        'image': 'hello-world',
        'namespace': 'default'
    })

    execution = node.launch()

    assert execution.identifier

    logs = execution.logs()
    print(type(logs))
    if isinstance(logs, bytes):
        logs = logs.decode()

    assert 'Hello from Docker!' in logs
