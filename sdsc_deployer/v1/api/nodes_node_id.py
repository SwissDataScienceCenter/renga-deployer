# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from flask import g, request

from . import Resource
from .. import schemas


class NodesNodeId(Resource):
    def get(self, node_id):

        return {}, 200, None
