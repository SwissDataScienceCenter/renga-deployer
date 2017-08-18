#!/usr/bin/env bash

# Reinstalls SDSC Deployer. This is needed if the folder is mounted into the container.
if [ ! -d "sdsc_deployer.egg-info" ]; then
    # Command will fail but the needed sdsc_deployer.egg-info folder is created.
    pip install -e .[all] > /dev/null 2>&1
fi

exec $@
