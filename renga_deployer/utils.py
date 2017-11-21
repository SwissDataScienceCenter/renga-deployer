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
"""Utility functions."""

import time
import uuid
from functools import wraps
from inspect import signature

from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import BadRequest


def decode_bytes(func):
    """Function wrapper that always returns string."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func()
        if isinstance(res, str):
            return res
        else:
            return res.decode()

    return wrapper


def resource_available(func):
    """
    Function wrapper to catch that something is not available.

    Example:

    while not resource_available(get_logs()):
        # this loop continues until the logs are available
        pass

    logs = get_logs()

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            time.sleep(0.2)
            return False

    return wrapper


def join_url(*args):
    """Join together url strings."""
    return '/'.join(s.strip('/') for s in args)


def dict_from_labels(labels, separator='='):
    """Create a multidict from label string."""
    return MultiDict((
        (label[0].strip(), label[1].strip()) for label in (
            raw.split(separator, 1) for raw in labels)))


def validate_uuid(s, version=4):
    """Check that a string is a valid UUID."""
    try:
        uid = uuid.UUID(s, version=version)
    except ValueError:
        return False

    return s == str(uid)


def validate_uuid_args(*names):
    """Check that input arguments are valid UUIDs."""
    def decorator(func):
        if not all([name in signature(func).parameters for name in names]):
            raise TypeError('Argument names must match function signature')

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Check the input arguments and return."""
            uuid_check = {name: validate_uuid(kwargs[name]) for name in names}
            if all(uuid_check.values()):
                return func(*args, **kwargs)
            raise BadRequest('Argument {} is not a valid uuid'.format(
                ','.join(
                    [name for name in names if not uuid_check[name]])))
        return wrapper
    return decorator
