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

import os
import time
import uuid
from collections import namedtuple

from blinker import Namespace

from .utils import decode_bytes

node_signals = Namespace()

node_created = node_signals.signal('node-created')
clear_all_nodes = node_signals.signal('clear-all-nodes')


def storage_clear_all():
    clear_all_nodes.send(0)


class Node(object):
    """Node superclass."""

    def __init__(self, env=None):
        """Create a Node instance."""
        self.id = uuid.uuid4().hex
        self.env = env or {}
        node_created.send(self)


class DockerNode(Node):
    """Class for deploying nodes on docker."""

    def __init__(self, env=None):
        """Create a DockerNode instance.

        :params env: dict of Node specification.
        """
        import docker

        super().__init__(env)
        self.client = docker.from_env()
        container = self.client.containers.create(env['image'], detach=True)
        self.container_id = container.id

    def launch(self):
        """Launch a docker container with the Node image."""
        container = self.client.containers.get(self.container_id)
        container.start()
        return ExecutionEnvironment(
            node=self,
            identifier=container.id,
            logs=decode_bytes(container.logs))


class K8SNode(Node):
    """Class for deploying nodes on Kubernetes."""

    def __init__(self, env=None):
        """Create a K8SNode instance.

        :params env: dict of Node specification.
        """
        import pykube
        super().__init__(env)
        self._pykube = pykube
        self.api = self._pykube.HTTPClient(
            self._pykube.KubeConfig.from_file(
                os.path.join(os.path.expanduser('~'), ".kube/config")))

    def launch(self):
        """Launch a kubernetes Job with the Node attributes."""
        env = self.env

        job = self._pykube.Job(self.api,
                               self._k8s_job_template(
                                   namespace=env['namespace'],
                                   name=self.id,
                                   image=env['image']))

        # actually submit the job to k8s
        job.create()
        time.sleep(5)

        return ExecutionEnvironment(
            node=self,
            identifier=job.obj['metadata']['uid'],
            logs=self._get_logs(job))

    @staticmethod
    def _k8s_job_template(namespace, name, image):
        """Return simple kubernetes job JSON."""
        return {
            "kind": "Job",
            "metadata": {
                "namespace": "{0}".format(namespace),
                "generateName": "{0}-".format(name)
            },
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "{0}".format(name),
                            "image": "{0}".format(image)
                        }],
                        "restartPolicy":
                        "Never"
                    }
                }
            }
        }

    def _get_logs(self, job):
        """Extract logs for the Job from the Pod.

        :params job: Instance of ``pykube.Job``
        """
        metadata = job.obj['metadata']
        pod = self._pykube.objects.Pod.objects(self.api).filter(
            namespace=metadata['namespace'],
            selector={'controller-uid':
                      metadata['labels']['controller-uid']}).get()
        return pod.logs


ExecutionEnvironment = namedtuple('ExecutionEnvironment',
                                  ['node', 'identifier', 'logs'])
