..
    Copyright 2017 Swiss Data Science Center

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

===============
 SDSC-Deployer
===============

.. image:: https://travis-ci.com/SwissDataScienceCenter/sdsc-deployer.svg?token=AuxHLdYP4GzNgGQfyxXT&branch=master
    :target: https://travis-ci.com/SwissDataScienceCenter/sdsc-deployer

.. .. image:: https://img.shields.io/coveralls/SwissDataScienceCenter/sdsc-deployer.svg
..         :target: https://coveralls.io/r/SwissDataScienceCenter/sdsc-deployer

.. .. image:: https://img.shields.io/github/tag/SwissDataScienceCenter/sdsc-deployer.svg
..         :target: https://github.com/SwissDataScienceCenter/sdsc-deployer/releases

.. .. image:: https://img.shields.io/pypi/dm/sdsc-deployer.svg
..         :target: https://pypi.python.org/pypi/sdsc-deployer

.. .. image:: https://img.shields.io/github/license/SwissDataScienceCenter/sdsc-deployer.svg
..         :target: https://github.com/SwissDataScienceCenter/sdsc-deployer/blob/master/LICENSE

SDSC Deployer Service.

.. Further documentation is available on
.. https://sdsc-deployer.readthedocs.io/

Local
-----

::

   $ export FLASK_APP=sdsc_deployer/app.py
   $ flask run

The first time you run the app locally, you may need to build the database tables:

::

    $ flask shell
    >>> from sdsc_deployer.app import db
    >>> db.create_all()


Docker
------

::

   $ docker build --tag sdsc-deployer:latest .
   $ docker run -p 5000:5000 -v /var/run/docker.sock:/var/run/docker.sock sdsc-deployer:latest

For development, mount the code directly and enable flask debug mode:

::

   $ docker run -p 5000:5000 \
         -e FLASK_DEBUG=1 \
         -v `pwd`:/code \
         -v /var/run/docker.sock:/var/run/docker.sock \
         sdsc-deployer:latest


You can test the API by pointing your browser to http://localhost:5000/v1/ui


Configuration
-------------

These are the environment variables used by the deployer service:

::

    DEPLOYER_URL: base URL for the service
    DEPLOYER_AUTHORIZATION_URL: openid-connect authorization endpoint
    DEPLOYER_TOKEN_URL: openid-connect token endpoint
    DEPLOYER_CLIENT_ID/_SECRET: client credentials used for OIDC authentication
    DEPLOYER_APP_NAME: application name
    SQLALCHEMY_DATABASE_URI: the URI of the database to be used for preserving internal state
    PLATFORM_SERVICE_API: base URL for the platform services
    DEPLOYER_KG_PUSH: push contexts and executions to the KnowledgeGraph
    DEPLOYER_RM_AUTHORIZE: obtain and validate ResourceManager authorization tokens
    RESOURCE_MANAGER_PUBLIC_KEY: public key used to verify ResourceManager tokens
    




Platform integration
--------------------

The deployer can optionally integrate with other SDSC Platform services. To enable integration,
set the ``PLATFORM_SERVICE_API`` environment variable to point to the api URL, e.g.
``http://localhost:9000/api``. Deployment contexts and executions will automatically be added to
the knowledge graph. To use the resource manager, you will need to additionally set the ``RESOURCE_MANAGER_PUBLIC_KEY``.
