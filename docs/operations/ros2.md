# ROS 2 lifecycle bridge

Use a ROS-supported environment with `rclpy` and `simulation_interfaces` installed
and its setup script sourced. The simulator must already be running. This bridge
uses standard ROS services, discovered under a configurable namespace.

```sh
simweave ros2 features --namespace /gzserver
simweave ros2 reset --namespace /gzserver
simweave ros2 step --namespace /gzserver --steps 10 --timeout 10
```

Reset requires advertised support for all reset scopes. Step requires pause and
single/multi-step capabilities, requests the paused state, then performs a
bounded step call. An already-paused response is accepted. Other unsuccessful
results and timeouts fail the command; a timeout has an unknown operation outcome
and is never automatically retried. Reset affects the simulator's entire world.

The bridge does not launch simulators, load worlds, control a robot, collect its
sensors, or guarantee seeded resets. It is intentionally not selectable as a
complete cart experiment adapter. Gazebo/Isaac/Webots integrations need their own
model and controller mappings plus real conformance runs.

Reference: [ROS simulation interfaces](https://github.com/ros-simulation/simulation_interfaces).
Local verification uses fake transport tests. A real ROS simulator was not
available for the initial implementation; that remains an explicit validation gap.
