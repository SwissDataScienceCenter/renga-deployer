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
"""Implement ``/nodes/{node_id}/executions(/{execution_id})`` endpoint."""

from sdsc_deployer.ext import current_deployer
from sdsc_deployer.deployer import execution_created


@execution_created.connect
def store_execution(execution):
    current_deployer.storage['executions'][execution.id] = execution
    current_deployer.storage['index'][execution.node_id].append(execution)


def search(node_id):
    return {
        'executions':
        [{
            'identifier': execution.id,
            'engine': execution.engine,
            'namespace': execution.namespace,
        }
         for execution in current_deployer.storage['index'][node_id].values()],
    }, 200


def get(node_id, execution_id):
    execution = current_deployer.storage['executions'][execution_id]
    assert execution.node_id == node_id
    return {
        'identifier': execution.id,
        'engine': execution.engine,
        'namespace': execution.namespace,
    }, 200


def post(node_id, data):
    node = current_deployer.storage['nodes'][node_id]
    execution = current_deployer.deployer.launch(node=node, **data)
    return {
        'identifier': execution.id,
        'engine': execution.engine,
        'namespace': execution.namespace,
    }, 201
