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
"""Engine sub-module."""

import logging
import os
import re
import shlex
import time

from flask import current_app
from werkzeug.utils import cached_property

from renga_deployer.serializers import ContextSchema, ExecutionSchema

from .models import Execution
from .utils import decode_bytes, resource_available

context_schema = ContextSchema()
execution_schema = ExecutionSchema()


class Engine(object):
    """Base engine class."""

    def launch(self, context, **kwargs):
        """Create new execution environment for a given context."""
        raise NotImplemented

    def stop(self, execution, remove=False):
        """Stop an execution."""
        raise NotImplemented

    def get_logs(self, execution):
        """Extract logs for a container."""
        raise NotImplemented

    def get_host_port(self, execution):
        """Retrieve the host/port where the application can be reached."""
        raise NotImplemented

    def get_execution_environment(self, execution) -> dict:
        """Retrieve the environment specified for an execution container."""
        raise NotImplemented


class DockerEngine(Engine):
    """Class for deploying contexts on docker."""

    @cached_property
    def logger(self):
        """Create a logger instance."""
        return logging.getLogger('renga.deployer.engines.docker')

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

        # Fix an unexpected behaviour of the python docker client which
        # leads to all images being downloaded when no tag is specified.
        image = context.spec['image']
        if ':' not in image:
            image += ':latest'

        container = self.client.containers.run(
            image=image,
            ports=ports,
            command=context.spec.get('command'),
            detach=True,
            environment=execution.environment or None)

        self.logger.info(
            'Launched container for execution {1} of context {0}'.format(
                execution.id, context.id),
            extra={'container_attrs': container.attrs,
                   'execution': execution_schema.dump(execution).data,
                   'context': context_schema.dump(execution.context).data})

        execution.engine_id = container.id

        return execution

    def stop(self, execution, remove=False):
        """Stop a running container, optionally removing it."""
        container = self.client.containers.get(execution.engine_id)
        container.stop()
        if remove:
            container.remove()

        self.logger.info(
            'Stopped execution {0} of context {1}'.format(
                execution.id, execution.context.id),
            extra={'container_attrs': container.attrs,
                   'execution': execution_schema.dump(execution).data,
                   'context': context_schema.dump(execution.context).data})

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
                'specified':
                container_port.split('/')[0],
                'protocol':
                container_port.split('/')[1].upper(),
                'host':
                current_app.config[
                    'DEPLOYER_DOCKER_CONTAINER_IP'] or host_spec['HostIp'],
                'exposed':
                host_spec['HostPort'],
            }
                for container_port, host_specs in port_bindings.items()
                for host_spec in host_specs],
        }

    def get_execution_environment(self, execution) -> dict:
        """Retrieve the environment specified for an execution container."""
        container = self.client.containers.get(execution.engine_id)
        return {
            k: v
            for (
                k,
                v) in [e.split('=') for e in container.attrs['Config']['Env']]
        }

    def get_state(self, execution):
        """Return the status of an execution."""
        import docker
        try:
            return self.client.containers.get(execution.engine_id).status
        except docker.errors.NotFound:
            return 'unavailable'


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
            kubernetes.config.load_kube_config()
            self.config = kubernetes.config.kube_config.Configuration()
            self.logger.debug(
                'Loaded k8s configuration.', extra=self.config.__dict__)

    @cached_property
    def logger(self):
        """Create a logger instance."""
        return logging.getLogger('renga.deployer.engines.k8s')

    def launch(self, execution, engine=None, **kwargs):
        """Launch a Kubernetes Job with the context spec."""
        context = execution.context

        batch = self._kubernetes.client.BatchV1Api()
        namespace = kwargs.pop('namespace', 'default')
        job_spec = self._k8s_job_template(namespace, execution)
        job = batch.create_namespaced_job(namespace, job_spec)
        uid = job.metadata.labels['controller-uid']

        self.logger.info(
            'Created job for execution {0} of context {1}'.format(
                execution.id, execution.context.id),
            extra={'job': job.to_dict(),
                   'execution': execution_schema.dump(execution).data,
                   'context': context_schema.dump(execution.context).data})

        # assume that if the user specified a port to open, they want
        # it available from the outside
        if context.spec.get('ports'):
            # To expose an interactive job, we need to start a service.
            # We use the job controller-uid to link the service.
            api = self._kubernetes.client.CoreV1Api()
            service_spec = self._k8s_service_template(namespace, context, uid)
            service = api.create_namespaced_service(namespace, service_spec)

            self.logger.info(
                'Created service for namespaced job {}'.format(uid),
                extra={'service': service.to_dict()})

            # if using an ingress, need to make an additional object
            if current_app.config.get(
                    'DEPLOYER_K8S_USE_INGRESS'):  # pragma no cover
                beta_api = self._kubernetes.client.ExtensionsV1beta1Api()
                ingress = beta_api.create_namespaced_ingress(
                    namespace,
                    self._k8s_ingress_template(uid, service.metadata.name,
                                               context.spec['ports'][0]))
                self.logger.info(
                    'Created ingress for service {}'.format(
                        service.metadata.name),
                    extra={'ingress': ingress.to_dict()})

        execution.engine_id = uid
        execution.namespace = namespace
        return execution

    def stop(self, execution, remove=False):
        """Stop a running job."""
        api = self._kubernetes.client.CoreV1Api()
        batch = self._kubernetes.client.BatchV1Api()

        if execution.context.spec.get('ports'):
            service = api.list_namespaced_service(
                execution.namespace,
                label_selector='job-uid={0}'.format(
                    execution.engine_id)).items[0]

            api.delete_namespaced_service(
                service.metadata.name,
                execution.namespace, )

            self.logger.info(
                'Deleted namespaced service {}'.format(service.metadata.name),
                extra={'service': service.to_dict()})

            if current_app.config.get(
                    'DEPLOYER_K8S_USE_INGRESS'):  # pragma no cover
                beta_api = self._kubernetes.client.ExtensionsV1beta1Api()
                ingress = beta_api.list_namespaced_ingress(
                    execution.namespace,
                    label_selector='job-uid={0}'.format(
                        execution.engine_id)).items[0]
                beta_api.delete_namespaced_ingress(
                    ingress.metadata.name, execution.namespace,
                    self._kubernetes.client.V1DeleteOptions())

                self.logger.info(
                    'Deleted namespaced ingress {0} for service {1}'.format(
                        ingress.metadata.uid, service.metadata.name),
                    extra={'ingress': ingress.to_dict()})

        batch.delete_collection_namespaced_job(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))

        self.logger.info('Deleted namespaced job for execution {}'.format(
            execution.engine_id), extra={
                'execution': execution_schema.dump(execution).data,
                'context': context_schema.dump(execution.context).data})

        api.delete_collection_namespaced_pod(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))

        self.logger.info('Deleted namespaced pod for execution {}'.format(
            execution.engine_id))

        return execution

    def get_state(self, execution):
        """Get status of a running job."""
        api = self._kubernetes.client.CoreV1Api()
        pod = api.list_namespaced_pod(
            execution.namespace,
            label_selector='controller-uid={}'.format(
                execution.engine_id)).items[0]
        status = list(
            filter(lambda c: c.name == str(execution.context.id),
                   pod.status.container_statuses))[0]

        return list(
            filter(lambda x: x[1], status.state.to_dict().items()))[0][0]

    @staticmethod
    def _k8s_job_template(namespace, execution):
        """Return simple kubernetes job JSON."""
        # required spec
        context = execution.context

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
                'containerPort': int(port)
            } for port in context.spec['ports']]

        if context.spec.get('command'):
            command = shlex.split(context.spec['command'])
            spec['containers'][0]['command'] = [command[0]]
            if len(command) > 1:
                spec['containers'][0]['args'] = command[1:]

        spec['containers'][0]['env'] = [{
            'name': k,
            'value': str(v)
        } for k, v in execution.environment.items()]

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
        """Return simple kubernetes service JSON."""
        return {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'generateName': re.sub('[^\w]+', '-', context.spec['image']),
                'namespace': namespace,
                'labels': {
                    'job-uid': "{0}".format(uid)
                }
            },
            'spec': {
                'hostNetwork': 'true',
                'ports': [{
                    'port': int(port)
                } for port in context.spec['ports']],
                'selector': {
                    'controller-uid': "{0}".format(uid)
                },
                'type': 'NodePort'
            }
        }

    @staticmethod
    def _k8s_ingress_template(
            uid, service_name, service_port):  # pragma no cover
        """Return kubernetes ingress JSON."""
        return {
            'apiVersion': 'extensions/v1beta1',
            'kind': 'Ingress',
            'metadata': {
                'generateName': 'interactive',
                'labels': {
                    'job-uid': "{0}".format(uid)
                }
            },
            'spec': {
                'backend': {
                    'serviceName': service_name,
                    'servicePort': int(service_port)
                }
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

        if not service.items:
            # this service doesn't exist
            return {'ports': []}

        else:
            return {
                'ports': [{
                    'specified':
                    port.port,
                    'host':
                    current_app.config[
                        'DEPLOYER_K8S_CONTAINER_IP'] or pod.items[
                            0].status.host_ip,
                    'exposed':
                    port.node_port,
                    'protocol':
                    port.protocol,
                } for port in service.items[0].spec.ports]
            }

    def get_execution_environment(self, execution) -> dict:
        """Retrieve the environment specified for an execution container."""
        client = self._kubernetes.client.BatchV1Api()
        job = client.list_namespaced_job(
            execution.namespace,
            label_selector='controller-uid={0}'.format(execution.engine_id))
        return {
            e.name: e.value
            for e in job.items[0].spec.template.spec.containers[0].env
        }
