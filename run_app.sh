#!/bin/sh

echo "from sdsc_deployer.nodes import db; db.create_all()" | flask shell && flask run -h 0.0.0.0
