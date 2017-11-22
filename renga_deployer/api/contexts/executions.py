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
"""Implement ``/contexts/{context_id}/executions/{execution_id}`` endpoint."""

from renga_deployer.authorization import check_token
from renga_deployer.ext import current_deployer
from renga_deployer.models import Context, Execution
from renga_deployer.serializers import ExecutionSchema
from renga_deployer.utils import validate_uuid_args

execution_schema = ExecutionSchema()
executions_schema = ExecutionSchema(many=True)


@check_token('deployer:contexts_read', 'deployer:executions_read')
@validate_uuid_args('context_id')
def search(context_id):
    """Return currently stored ``Executions`` of a given context."""
    return executions_schema.dump(
        Execution.query.filter_by(context_id=context_id).all()).data, 200


@check_token('deployer:contexts_read', 'deployer:executions_read')
@validate_uuid_args('context_id', 'execution_id')
def get(context_id, execution_id):
    """Return information about a specific ``Execution``."""
    execution = Execution.query.get_or_404(execution_id)
    assert str(execution.context_id) == context_id
    return execution_schema.dump(execution).data, 200


@check_token('deployer:contexts_read', 'deployer:executions_write')
@validate_uuid_args('context_id')
def post(context_id, data):
    """Create a new ``Execution`` for a given context."""
    context = Context.query.get_or_404(context_id)
    execution = current_deployer.deployer.launch(context=context, **data)
    return execution_schema.dump(execution).data, 201


@check_token
@validate_uuid_args('context_id', 'execution_id')
def logs(context_id, execution_id):
    """Retrieve execution logs."""
    execution = Execution.query.get_or_404(execution_id)
    assert str(execution.context_id) == context_id
    return current_deployer.deployer.get_logs(execution)


@check_token
@validate_uuid_args('context_id', 'execution_id')
def ports(context_id, execution_id):
    """Retrieve execution logs."""
    execution = Execution.query.get_or_404(execution_id)
    assert str(execution.context_id) == context_id
    return current_deployer.deployer.get_host_ports(execution)


@check_token
@validate_uuid_args('context_id', 'execution_id')
def delete(context_id, execution_id):
    """Retrieve execution logs."""
    execution = Execution.query.get_or_404(execution_id)
    assert str(execution.context_id) == context_id
    return current_deployer.deployer.stop(execution, remove=True)
