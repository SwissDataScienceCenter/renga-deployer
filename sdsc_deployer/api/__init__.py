"""REST API implementation for SDSC-Deployer service."""
from functools import wraps

from flask import request, current_app

from sdsc_deployer.ext import current_deployer


def deployment_authorization(function):
    """If configured, check authorization with the ResourceManager."""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if 'sdsc-resource-manager' in current_app.extensions:
            from jose import jwt
            from sdsc_deployer.contrib.resource_manager \
                import request_authorization_token

            if 'data' in kwargs:
                claims = kwargs['data']
            else:
                claims = args

            # form the resource request and get the authorization token
            resource_request = {
                'permission_holder_id': 0,
                'scope': ['contexts:write'],
                'extra_claims': {
                    'claims': claims
                }
            }
            _, token = request.headers.get('Authorization').split()

            access_token = request_authorization_token(token, resource_request)

            # verify the token and create the context
            auth = jwt.decode(
                access_token,
                key=current_app.config['RESOURCE_MANAGER_PUBLIC_KEY'])

            assert auth['iss'] == 'resource-manager'

            # TODO: validate request
        return function(*args, **kwargs)

    return wrapper
