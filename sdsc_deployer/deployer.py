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


"""Deployer sub-module tests."""

from __future__ import absolute_import, print_function

import os


class Deployer(object):

    def __init__(self, engines=None, **kwargs):
        self.engines = engines or {}

    @classmethod
    def from_env(cls, prefix='DEPLOYER_'):
        engines = {}

        # grab engine definitions
        engine_prefix = prefix + 'ENGINE_'
        for key in os.environ:
            if key.startswith(engine_prefix):
                engine = key[len(engine_prefix):].lower()
                engines[engine] =  os.environ[key]

        return cls(engines=engines)

