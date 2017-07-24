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

from .utils import decode_bytes, resource_available

ExecutionMixin = namedtuple('ExecutionMixin',
                            ['id', 'node_id', 'engine', 'engine_id'])


class ExecutionEnvironment(ExecutionMixin):
    @classmethod
    def from_node(cls, node, engine, engine_id):
        return cls(
            id=uuid.uuid4().hex,
            node_id=node.id,
            engine=engine,
            engine_id=engine_id, )


class Node(object):
    """Node superclass."""

    def __init__(self, data=None):
        """Create a Node instance."""
        self.id = uuid.uuid4().hex
        self.data = data or {}
        self.spec = self.data.get('spec', {})

    @classmethod
    def create(cls, data=None):
        return cls(data=data)
