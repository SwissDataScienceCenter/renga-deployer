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
from collections import namedtuple
from functools import wraps

import docker
import pykube


class Node(object):
    """Node superclass."""

    def __init__(self, env=None):
        """Create a Node instance."""
        self.env = env or {}

def decode_bytes(func):
    """Wraps function that returns bytes to return string instead"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func().decode()
    return wrapper


class DockerNode(Node):
    """Class for deploying nodes on docker."""

    def __init__(self, env=None):
        """Create a DockerNode instance.

        Arguments:

        env: dict of Node specification.
        """
        super().__init__(env)
        self.client = docker.from_env()

    def launch(self):
        """Launch a docker container with the Node image."""
        env = self.env
        container = self.client.containers.run(env['image'], detach=True)
        print(container.logs())
        return ExecutionEnvironment(
            node=self, identifier=container.id, logs=decode_bytes(container.logs))


class K8SNode(Node):
    """Class for deploying nodes on Kubernetes."""

    def __init__(self, env=None):
        """Create a K8SNode instance.

        Arguments:

        env: dict of Node specification.
        """
        super().__init__(env)
        self.api = pykube.HTTPClient(
            pykube.KubeConfig.from_file(
                os.path.join(os.path.expanduser('~'), ".kube/config")))

    def launch(self):
        """Launch a kubernetes Job with the Node attributes."""
        env = self.env

        job = pykube.Job(self.api,
                         K8SNode._k8s_job_template(
                             namespace=env['namespace'],
                             name=env['name'],
                             image=env['image']))

        # actually submit the job to k8s
        job.create()
        time.sleep(5)

        return ExecutionEnvironment(
            node=self,
            identifier=job.obj['metadata']['uid'],
            logs=K8SNode._get_logs(self.api, job))

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
    def _get_logs(api, job):
        """Extract logs for the Job from the Pod.

        Arguments:

        api: pykube.api

        job: pykube.Job object
        """
        metadata = job.obj['metadata']
        print(metadata)
        pod = pykube.objects.Pod.objects(api).filter(
            namespace=metadata['namespace'],
            selector={'controller-uid': metadata['labels']['controller-uid']}).get()
        return pod.logs


ExecutionEnvironment = namedtuple('ExecutionEnvironment',
                                  ['node', 'identifier', 'logs'])
