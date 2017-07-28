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
"""Send events to Graph Mutation Service."""

import requests

from sdsc_deployer.deployer import context_created, execution_created
from sdsc_deployer.models import Context, Execution, db


class GraphContext(db.Model):
    """Represent a graph context node."""

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Graph identifier."""

    context_id = db.Column(UUIDType, db.ForeignKey(Context.id))
    """Context identifier."""

    context = db.relationship(Context, backref='graph')


class GraphExecution(db.Model):
    """Represent a graph execution node."""

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    """Graph identifier."""

    execution_id = db.Column(UUIDType, db.ForeignKey(Execution.id))
    """Context identifier."""

    execution = db.relationship(Execution, backref='graph')


class KnowledgeGraphSync(object):
    """Knowledge Graph Sync extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        app.config.setdefault(
            'DEPLOYER_GRAPH_MUTATION_URL',
            'https://testing.datascience.ch:5000/api/mutation')

        context_created.connect(create_context)
        execution_created.connect(create_execution)

        app.extensions['sdsc-knowledge-graph-sync'] = self


def create_context(context, token=None):
    """Create context node."""
    token = token or request.headers['Authentication']
    headers = {'Authentication': token}

    response = requests.post(
        current_app.config['DEPLOYER_GRAPH_MUTATION_URL'],
        context,  # TODO serialize
        headers=headers, )

    db.session.add(GraphContext(id=response.json['id'], context=context))
    db.session.commit()


def create_execution(execution, token=None):
    """Create execution node and vertex connecting context."""
    token = token or request.headers['Authentication']
    headers = {'Authentication': token}

    response = requests.post(
        current_app.config['DEPLOYER_GRAPH_MUTATION_URL'],
        execution,  # TODO serialize
        headers=headers, )

    db.session.add(GraphExecution(id=response.json['id'], execution=execution))
    db.session.commit()

    if execution.context.graph is None:
        context_created(execution.context, token=token)

    # TODO create edge
    # execution.graph.id -> execution.context.graph.id


def sync(token=None):
    """Sync all nodes with graph service."""
    raise NotImplemented()

    for context in Context.query.joined(Context.graph).filter(
            GraphContext.id.is_(None)):
        print(context, 'needs to be pushed')

    for execution in Execution.query.joined(Execution.graph).filter(
            GraphExecution.id.is_(None)):
        print(execution, 'needs to be pushed')
