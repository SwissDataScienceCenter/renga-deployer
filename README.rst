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

.. image:: https://img.shields.io/travis/SwissDataScienceCenter/sdsc-deployer.svg
        :target: https://travis-ci.org/SwissDataScienceCenter/sdsc-deployer

.. image:: https://img.shields.io/coveralls/SwissDataScienceCenter/sdsc-deployer.svg
        :target: https://coveralls.io/r/SwissDataScienceCenter/sdsc-deployer

.. image:: https://img.shields.io/github/tag/SwissDataScienceCenter/sdsc-deployer.svg
        :target: https://github.com/SwissDataScienceCenter/sdsc-deployer/releases

.. image:: https://img.shields.io/pypi/dm/sdsc-deployer.svg
        :target: https://pypi.python.org/pypi/sdsc-deployer

.. image:: https://img.shields.io/github/license/SwissDataScienceCenter/sdsc-deployer.svg
        :target: https://github.com/SwissDataScienceCenter/sdsc-deployer/blob/master/LICENSE

SDSC Deployer Service.

*This is an experimental developer preview release.*

Further documentation is available on
https://sdsc-deployer.readthedocs.io/

Start locally:

::

   $ export FLASK_APP=sdsc_deployer/app.py
   $ flask run


Or with docker:

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

