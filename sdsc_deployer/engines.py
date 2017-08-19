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
import shlex
import time

from werkzeug.utils import cached_property

from .models import Execution
from .utils import decode_bytes, resource_available


class Engine(object):
    """Base engine class."""

    def launch(self, context, **kwargs):
        """Create new execution environment for a given context."""
        raise NotImplemented

    def get_logs(self, execution):
        """Extract logs for a container."""
        raise NotImplemented

    def get_host_port(self, execution):
        """Retrieve the host/port where the application can be reached."""
        raise NotImplemented


class DockerEngine(Engine):
    """Class for deploying contexts on docker."""

    @cached_property
    def client(self):
        """Create a docker client from local environment."""
        import docker
        return docker.from_env()

    def launch(self, execution, **kwargs):
        """Launch a docker container with the context image."""
        context = execution.context

        if context.spec.get('ports'):
            ports = {port: None for port in context.spec.get('ports')}
        else:
            ports = None

        container = self.client.containers.run(
            image=context.spec['image'],
            ports=ports,
            command=context.spec.get('command'),
            detach=True,
            environment=execution.environment or None)

        execution.engine_id = container.id

        return execution

    def get_logs(self, execution):
        """Extract logs for a container."""
        return decode_bytes(
            self.client.containers.get(execution.engine_id).logs)()

    def get_host_ports(self, execution):
        """Returns host ip and port bindings for the running execution."""
        container = self.client.containers.get(execution.engine_id)
        port_bindings = container.attrs['NetworkSettings'].get('Ports', {})
        return {
            'ports': [{
                'specified': container_port.split('/')[0],
                'protocol': container_port.split('/')[1].upper(),
                'host': host_spec['HostIp'],
                'exposed': host_spec['HostPort'],
            }
                      for container_port, host_specs in port_bindings.items()
                      for host_spec in host_specs],
        }

    def stop(self, execution, remove=False):
        """Stop a running container, optionally removing it."""
        container = self.client.containers.get(execution.engine_id)
        container.stop()
        if remove:
            container.remove()


class K8SEngine(Engine):
    """Class for deploying contexts on Kubernetes."""

    def __init__(self, config=None, timeout=10):
        """Create a K8SNode instance."""
        # FIXME add super
        import kubernetes
        self._kubernetes = kubernetes
        self.timeout = timeout
        self.config = config

        if self.config is None:
            self.config = kubernetes.config.load_kube_config()

    def launch(self, execution, engine=None, **kwargs):
        """Launch a Kubernetes Job with the context spec."""
        context = execution.context

        batch = self._kubernetes.client.BatchV1Api()
        namespace = kwargs.pop('namespace', 'default')
        job_spec = self._k8s_job_template(namespace, context)
        job = batch.create_namespaced_job(namespace, job_spec)
        uid = job.metadata.labels['controller-uid']

        if context.spec.get('interactive'):
            # To expose an interactive job, we need to start a service.
            # We use the job controller-uid to link the service.
            api = self._kubernetes.client.CoreV1Api()
            service_spec = self._k8s_service_template(namespace, context, uid)
            service = api.create_namespaced_service(namespace, service_spec)

        execution.engine_id = uid
        execution.namespace = namespace
        return execution

    def stop(self, execution, remove=False):
        """Stop a running job."""
        api = self._kubernetes.client.CoreV1Api()
        batch = self._kubernetes.client.BatchV1Api()

        if execution.context.spec.get('interactive'):
            service = api.list_namespaced_service(
                execution.namespace,
                label_selector='job-uid={0}'.format(execution.engine_id))

            api.delete_namespaced_service(
                service.items[0].metadata.name,
                execution.namespace, )

        batch.delete_collection_namespaced_job(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))
        api.delete_collection_namespaced_pod(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))
        return execution

    @staticmethod
    def _k8s_job_template(namespace, context):
        """Return simple kubernetes job JSON."""
        # required spec
        spec = {
            "containers": [{
                "name": "{0}".format(context.id),
                "image": "{0}".format(context.spec['image'])
            }],
            "restartPolicy":
            "Never"
        }

        # optional spec
        if context.spec.get('ports'):
            spec['containers'][0]['ports'] = [{
                'containerPort': port
            } for port in context.spec['ports']]

        if context.spec.get('command'):
            command = shlex.split(context.spec['command'])
            spec['containers'][0]['command'] = [command[0]]
            if len(command) > 1:
                spec['containers'][0]['args'] = command[1:]

        # finalize job template
        template = {
            "kind": "Job",
            "metadata": {
                "namespace": "{0}".format(namespace),
                "generateName": "{0}-".format(context.id)
            },
            "spec": {
                "template": {
                    "spec": spec
                }
            }
        }

        return template

    @staticmethod
    def _k8s_service_template(namespace, context, uid):
        """Return simple kubernetes job JSON."""
        return {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'generateName': context.spec['image'],
                'namespace': namespace,
                'labels': {
                    'job-uid': "{0}".format(uid)
                }
            },
            'spec': {
                'hostNetwork': 'true',
                'ports': [{
                    'port': port
                } for port in context.spec['ports']],
                'selector': {
                    'controller-uid': "{0}".format(uid)
                },
                'type': 'NodePort'
            }
        }

    def get_logs(self, execution, timeout=None, **kwargs):
        """Extract logs for the Job from the Pod.

        :params execution: Instance of ``ExecutionEnvironment``
        """
        api = self._kubernetes.client.CoreV1Api()
        namespace = execution.namespace

        pod = api.list_namespaced_pod(
            namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))

        timein = time.time()

        while not resource_available(api.read_namespaced_pod_log)(
                pod.items[0].metadata.name, namespace):
            if time.time() - timein > (timeout or self.timeout):
                raise RuntimeError("Timeout while fetching logs.")

        return api.read_namespaced_pod_log(pod.items[0].metadata.name,
                                           namespace)

    def get_host_ports(self, execution):
        """Returns host ip and port bindings for the running execution."""
        api = self._kubernetes.client.CoreV1Api()
        service = api.list_namespaced_service(
            execution.namespace,
            label_selector='job-uid={0}'.format(execution.engine_id))

        pod = api.list_namespaced_pod(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))

        return {
            'ports': [{
                'specified': port.port,
                'host': pod.items[0].status.host_ip,
                'exposed': port.node_port,
                'protocol': port.protocol,
            } for port in service.items[0].spec.ports]
        }
