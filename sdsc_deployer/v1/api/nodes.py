# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from flask import current_app, g, request
from werkzeug.local import LocalProxy

from . import Resource
from .. import schemas

current_deployer = LocalProxy(lambda: current_app.extensions['sdsc-deployer'])


class Nodes(Resource):
    def get(self):

        return [], 200, None

    def post(self):
        """Create a new node"""
        data = request.get_json()
        node = current_deployer.deployer.create(data={
            'env': {
                'engine': 'docker',
                'image': data['docker_image']
            }
        })
        exec_env = node.launch()
        print(exec_env.identifier)
        return {'identifier':exec_env.identifier, 'logs':exec_env.logs()}, 201
