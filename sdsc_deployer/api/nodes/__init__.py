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

from sdsc_deployer.deployer import current_deployer


def search():
    return 'Hello'


def get():
    pass


def post(data):
    node = current_deployer.deployer.create(data={
        'env': {
            'engine': 'docker',
            'image': data['docker_image']
        }
    })
    exec_env = node.launch()
    return {'identifier':exec_env.identifier}, 201
