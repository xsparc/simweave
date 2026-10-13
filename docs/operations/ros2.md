# ROS 2 and Gazebo cart experiments

The `gazebo` adapter executes the built-in one-dimensional cart using Gazebo
Harmonic physics and ROS 2 Jazzy services. It supports the existing scenario's
mass, damping, initial state, timestep, controller, seeded position noise,
disturbances, metrics, gates, and recordings. No GPU or rendering is required.
Gazebo timesteps must be whole nanoseconds; unsupported precision is rejected
before submission instead of producing a drifting native clock.

## Isolated integration image

From the repository root, with Docker running:

```sh
docker build -f integrations/ros2/Dockerfile -t simweave:ros-cart .
docker run --rm --network none --pids-limit 256 --memory 4g --cpus 2 simweave:ros-cart
```

The default command executes live conformance tests: repeated seeded trajectories,
MuJoCo comparisons, independent worlds, native validation, CLI recordings,
API/worker execution, and offline replay. Missing dependencies fail the suite
instead of producing skips. The image uses an unprivileged user, a digest-pinned
ROS base, and the frozen Python lock. Apt packages resolve at build time; the
validation report records tested versions. This is a development/verification
image, not a hosted deployment. Initial downloads are substantial.

Run an individual example within the disposable container:

```sh
docker run --rm --network none simweave:ros-cart bash -c \
  'simweave run examples/gazebo-cart-recovery.json --output /tmp/cart && simweave replay /tmp/cart'
```

Use an explicit output volume to retain recordings after container removal.
Never mount private host directories or the Docker socket into a worker.

## Native Ubuntu 24.04 / ROS 2 Jazzy setup

In an existing ROS installation, install `ros-jazzy-gz-sim-vendor`,
`ros-jazzy-simulation-interfaces`, `python3-colcon-common-extensions`,
`python3-venv`, and `build-essential`. Then:

```sh
source /opt/ros/jazzy/setup.bash
colcon build --base-paths integrations/ros2/simweave_gazebo \
  --build-base .local/ros-build --install-base .local/ros-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release
source .local/ros-install/setup.bash
python3 -m venv --system-site-packages .venv-ros
. .venv-ros/bin/activate
python -m pip install -e '.[dev,mujoco]'
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
simweave run examples/gazebo-cart-recovery.json --output .simweave/gazebo-run
simweave replay .simweave/gazebo-run
```

Use Python compatible with the distribution's `rclpy` binaries. The wheel does
not install ROS or compile the fixture. Source the same overlay for `simweave
serve`, `simweave worker`, or `simweave demo`; the dashboard then enables Gazebo.
Linux containers are the tested route from Windows/macOS; native ROS/Gazebo on
those hosts is untested. The lightweight default Docker/Compose image has no ROS.

## Protocol and capabilities

Each adapter instance launches the fixed installed `simweave_gazebo/cart_server`
executable, using its own ROS namespace, Gazebo partition, and temporary working
directory. It constructs a prismatic cart with zero gravity and no contacts.
Scenarios cannot supply SDF, executable paths, plugins, models, or URLs.

| Capability | Reference | MuJoCo | ROS/Gazebo cart |
| --- | --- | --- | --- |
| Cart, PD control, disturbances, gates | Yes | Yes | Yes |
| Physics | Reference integrator | MuJoCo | Gazebo Harmonic / DART |
| Seeded position noise | SimWeave PRNG | SimWeave PRNG | SimWeave PRNG |
| Full reset / finite steps | Yes | Yes | Standard ROS services |
| Force / joint observation | In process | In process | Acknowledged typed ROS services |
| Offline recording replay | Yes | Yes | Yes |
| Arbitrary robots or assets | No | No | No |
| GPU required | No | No | No |

Lifecycle uses `GetSimulatorFeatures`, `ResetSimulation` (ALL/default scopes),
`SetSimulationState` (paused only), and `StepSimulation` (1–20,000 steps within
the total run limit). Full reset reconstructs the world. Partial reset scopes and
free-running play are rejected. Advertised feature IDs are 20, 25, 26, 31, 32.

Three fixture services add the robot-specific contract: `ConfigureCart`,
`SetCartForce` with an expected step index, and `GetCartState` returning step,
native simulation time, position, and velocity. Force acknowledgement precedes
physics stepping; observations must match the requested step and clock. A force
applies to the finite step batch and is then cleared. Sample zero describes the
configured initial state; later samples read Gazebo joint state after physics.
Controller and sensor noise remain in SimWeave.

Each RPC has a deadline. Timeouts have an unknown mutation outcome and abort
without retries. Closing the adapter terminates and reaps its child; Linux
parent-death signaling handles abrupt worker exit. ROS/DDS is a trusted local
transport, not a public authentication boundary. Dedicated processes prevent
accidental interference, but are not a security sandbox.

Three ROS round trips per step favor explicit ordering over throughput. No
real-time claim is made. Repeatability is scoped to the same runtime environment;
cross-engine tolerances apply only to this tested, contact-free cart.

## Generic external-simulator lifecycle CLI

These commands control an already-running simulator and affect its world:

```sh
simweave ros2 features --namespace /gzserver
simweave ros2 reset --namespace /gzserver
simweave ros2 step --namespace /gzserver --steps 10 --timeout 10
```

Reset checks support, requests ALL, and requires success; reseeding is never
assumed. Step checks pause and single/multi-step capabilities. Already-paused
responses are accepted. The generic CLI does not launch worlds or define robot I/O.

Sources: [ROS interfaces](https://github.com/ros-simulation/simulation_interfaces),
[Gazebo server API](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1Server.html).
See [executed validation](../governance/ros-gazebo-validation.md).
