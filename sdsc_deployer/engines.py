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
"""Engine sub-module."""

import os
import time

from werkzeug.utils import cached_property

from .nodes import ExecutionEnvironment
from .utils import decode_bytes, resource_available


class Engine(object):
    """Base engine class."""

    def launch(self, node, **kwargs):
        """Create new execution environment for a given node."""
        raise NotImplemented


class DockerEngine(Engine):
    """Class for deploying nodes on docker."""

    @cached_property
    def client(self):
        import docker
        return docker.from_env()

    def launch(self, node, engine=None, **kwargs):
        """Launch a docker container with the Node image."""
        container = self.client.containers.run(node.data['image'], detach=True)
        return ExecutionEnvironment.from_node(
            node, engine=engine, engine_id=container.id)

    def get_logs(self, execution):
        """Extract logs for a container."""
        return decode_bytes(
            self.client.containers.get(execution.engine_id).logs)()


class K8SEngine(Engine):
    """Class for deploying nodes on Kubernetes."""

    def __init__(self, config=None, timeout=60):
        """Create a K8SNode instance."""
        # FIXME add super
        import pykube
        self._pykube = pykube
        self.config = config
        self.timeout = timeout

    @cached_property
    def api(self):
        import pykube  # TODO: Fix imports
        if self.config is None:
            self.config = pykube.KubeConfig.from_file(
                os.path.join(os.path.expanduser('~'), '.kube/config'))
        return pykube.HTTPClient(self.config)

    def launch(self, node, engine=None, **kwargs):
        """Launch a kubernetes Job with the Node attributes."""
        import pykube
        job = pykube.Job(self.api,
                         self._k8s_job_template(
                             namespace=kwargs.get('namespace', 'default'),
                             name=node.id,
                             image=node.data['image']))

        # actually submit the job to k8s
        job.create()
        return ExecutionEnvironment.from_node(
            node, engine=engine, engine_id=job.obj['metadata']['uid'])

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
