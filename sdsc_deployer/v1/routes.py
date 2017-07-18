# -*- coding: utf-8 -*-

"""Define API routes."""

from __future__ import absolute_import

from .api.nodes import Nodes
from .api.nodes_node_id import NodesNodeId

routes = [
    dict(resource=Nodes, urls=['/nodes'], endpoint='nodes'),
    dict(
        resource=NodesNodeId,
        urls=['/nodes/<int:node_id>'],
        endpoint='nodes_node_id'),
]
