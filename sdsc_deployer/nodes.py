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

from .utils import decode_bytes, resource_available

node_signals = Namespace()

node_created = node_signals.signal('node-created')
clear_all_nodes = node_signals.signal('clear-all-nodes')


def storage_clear_all():
    clear_all_nodes.send(0)


ExecutionEnvironment = namedtuple('ExecutionEnvironment', ['identifier'])


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
        self.identifier = container.id

    def launch(self):
        """Launch a docker container with the Node image."""
        container = self.client.containers.get(self.identifier)
        container.start()
        return ExecutionEnvironment(identifier=container.id)

    @staticmethod
    def get_logs(identifier):
        """Extract logs for a container."""
        import docker
        client = docker.from_env()
        return decode_bytes(client.containers.get(identifier).logs)()


class K8SNode(Node):
    """Class for deploying nodes on Kubernetes."""

    def __init__(self, env=None, k8s_config=None, timeout=60):
        """Create a K8SNode instance.

        :params env: dict of Node specification.
        """
        import pykube
        super().__init__(env)
        self._pykube = pykube
        self.api = K8SNode.get_api(k8s_config)

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

        self.identifier = job.obj['metadata']['uid']

        return ExecutionEnvironment(identifier=job.obj['metadata']['uid'])

    @staticmethod
    def get_api(config=None):
        """Get API object."""
        import pykube  # TODO: Fix imports
        if config is None:
            config = os.path.join(os.path.expanduser('~'), ".kube/config")
        return pykube.HTTPClient(pykube.KubeConfig.from_file(config))

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

    @staticmethod
    def get_logs(identifier, config=None, timeout=60):
        """Extract logs for the Job from the Pod.

        :params job: Instance of ``pykube.Job``
        """
        import pykube
        api = K8SNode.get_api(config)
        pod = pykube.objects.Pod.objects(api).filter(
            namespace=pykube.all, selector={'controller-uid':
                                            identifier}).get()

        # wait for logs to be available
        timein = time.time()
        while not resource_available(pod.logs)():
            if time.time() - timein > timeout:
                raise RuntimeError("Timeout while fetching logs.")

        return pod.logs()

    @staticmethod
    def get_job(uid, config=None):
        import pykube
        api = K8SNode.get_api(config)
        job = pykube.Job.objects(api).filter(selector={'controller-uid':
                                                       uid}).get()
