#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source /opt/simweave_ws/install/setup.bash
exec "$@"
