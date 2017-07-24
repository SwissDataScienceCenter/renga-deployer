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
node_removed = node_signals.signal('node-removed')
execution_created = node_signals.signal('execution-created')

ExecutionMixin = namedtuple('ExecutionMixin', ['id', 'node_id', 'engine_id'])


class ExecutionEnvironment(ExecutionMixin):
    def __init__(self, *args, **kwargs):
        execution_created.send(self)

    @classmethod
    def from_node(cls, node, engine_id):
        return cls(
            id=uuid.uuid4().hex,
            node_id=node.id,
            engine_id=engine_id, )


class Node(object):
    """Node superclass."""

    def __init__(self, env=None):
        """Create a Node instance."""
        self.id = uuid.uuid4().hex
        self.env = env or {}
        node_created.send(self)

    def remove(self, force=False):
        """Remove the node."""
        node_removed.send(self, force=force)


class DockerNode(Node):
    """Class for deploying nodes on docker."""

    def __init__(self, env=None):
        """Create a DockerNode instance.

        :params env: dict of Node specification.
        """
        import docker

        super().__init__(env)
        self.client = docker.from_env()

    def launch(self):
        """Launch a docker container with the Node image."""
        container = self.client.containers.run(self.env['image'], detach=True)
        return ExecutionEnvironment.from_node(self, engine_id=container.id)

    def get_logs(self, execution):
        """Extract logs for a container."""
        return decode_bytes(
            self.client.containers.get(execution.engine_id).logs)()


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
        self.timeout = timeout

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
        return ExecutionEnvironment.from_node(
            self, engine_id=job.obj['metadata']['uid'])

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

    def get_logs(self, execution, timeout=None):
        """Extract logs for the Job from the Pod.

        :params execution: Instance of ``ExecutionEnvironment``
        """
        api = self.api
        pykube = self._pykube
        pod = pykube.objects.Pod.objects(api).filter(
            namespace=pykube.all,
            selector={'controller-uid': execution.engine_id}).get()

        # wait for logs to be available
        timein = time.time()
        while not resource_available(pod.logs)():
            if time.time() - timein > (timeout or self.timeout):
                raise RuntimeError("Timeout while fetching logs.")

        return pod.logs()

    @staticmethod
    def get_job(uid, config=None):
        import pykube
        api = K8SNode.get_api(config)
        job = pykube.Job.objects(api).filter(selector={'controller-uid':
                                                       uid}).get()
