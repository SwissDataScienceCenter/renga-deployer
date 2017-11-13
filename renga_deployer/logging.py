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
"""Renga Logging."""


from logging import DEBUG, INFO, getLogger
from logging.config import dictConfig

import yaml

from . import config

conf = config.from_env(config)

if conf.get('RENGA_LOGGING_CONFIG'):
    with open(conf['RENGA_LOGGING_CONFIG'], 'r') as fp:
        dictConfig(yaml.load(fp))
else:
    dictConfig({
        'version': 1,
        'formatters': {
            'f': {
                'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'f',
                'level': DEBUG
            },
        },
        'loggers': {
            'renga': {
                'handlers': ['console'],
                'level': INFO
            }
        }
    })

logger = getLogger('renga.deployer.logging')
logger.debug('Logging initialized.')
