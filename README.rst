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

The first time you run the app locally, you may need to build the database
tables:

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


Orchestration with Postgres and load-balancer
---------------------------------------------

The packages includes two simple orchestration setup files:
``docker-compose.yml`` and ``docker-compose.full.yml``.

The first includes only the deployer container linked to a postgres database.
To use the deployer with postgres:

::

    $ docker-compose up

As before, the service is available on port ``5000``.

The second can be used as a template to define your own production deployment
environment including the `Traefik <http://traefik.io>`_ load balancer and
(self-signed) SSL certificates.

::

    $ docker-compose -f docker-compose.full.yml up

The service is available on ``https://localhost/api/deployer``. You can access the
traefik dashboard on http://localhost:8080/.


Platform integration
--------------------

The deployer can optionally integrate with other SDSC Platform services.
To enable integration, set the appropriate environment variables in the
form of ``<SERVICE_NAME_URL>`` to point to the api URL. For example,
setting ``KNOWLEDGE_GRAPH_URL`` will ensure that deployment contexts and
executions are automatically added to the knowledge graph. Note that to
use the resource manager, you will need to additionally set the
``DEPLOYER_JWT_KEY``.
