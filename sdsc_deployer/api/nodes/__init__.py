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
"""Implement ``/nodes`` endpoint."""

from sdsc_deployer.ext import current_deployer
from sdsc_deployer.nodes import Node


def search():
    """Return a listing of currently known nodes."""
    return {
        'nodes': [{
            'identifier': node.id,
            'image': node.data['image'],
            'ports': node.data.get('ports', {}),
        } for node in Node.query.all()]
    }, 200


def get(node_id):
    """Return information about a specific node."""
    node = Node.query.get_or_404(node_id)
    return {
        'identifier': node.id,
        'image': node.data['image'],
        'ports': node.data.get('ports', {}),
    }, 200


def post(data):
    """Create a new node."""
    node = current_deployer.deployer.create(data=data)
    return {
        'identifier': node.id,
        'image': node.data['image'],
        'ports': node.data.get('ports', {}),
    }, 201
