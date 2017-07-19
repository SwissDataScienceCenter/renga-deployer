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


"""Nodes sub-module."""

from collections import namedtuple

class Node(object):
    pass

class DockerNode(Node):
    """Class for deploying nodes on docker."""

    def __init__(self, env=None):
        import docker

        self.client = docker.from_env()
        self.env = env or {}

    def launch(self):
        """Launch a docker container with the Node image."""
        env = self.env
        container = self.client.containers.run(env['image'], detach=True)
        return ExecutionEnvironment(node=self, identifier=container.id, logs=container.logs)

class K8SNode(Node):
    pass

ExecutionEnvironment = namedtuple('ExecutionEnvironment', ['node', 'identifier', 'logs'])

