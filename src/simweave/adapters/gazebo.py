"""ROS 2 adapter for the isolated, built-in Gazebo cart fixture.

Lifecycle calls use simulation_interfaces; acknowledged force commands and
joint observations use the small, typed simweave_gazebo fixture protocol.
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from simweave.adapters.ros2 import RosTransport
from simweave.contracts import Scenario


def available() -> bool:
    """Check operator installation without importing ROS or starting a simulator."""
    import importlib.util

    if any(importlib.util.find_spec(name) is None for name in ("rclpy", "simweave_gazebo")):
        return False
    try:
        from ament_index_python.packages import get_package_prefix

        binary = Path(get_package_prefix("simweave_gazebo")) / "lib/simweave_gazebo/cart_server"
        return binary.is_file() and os.access(binary, os.X_OK)
    except (ImportError, LookupError):
        return False


class GazeboSimulator:
    name = "gazebo"
    version = "unconfigured"

    def __init__(self, transport: RosTransport | None = None, timeout: float = 10):
        if not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("timeout must be between zero and 60 seconds")
        self.transport = transport
        self.timeout = timeout
        self.ready = False
        self.closed = False

    def _call(self, service: str, fields: dict) -> dict:
        try:
            response = self.transport.call(service, fields, self.timeout)
            if response.get("result") not in (
                {1, 101} if service == "set_simulation_state" else {1}
            ):
                raise RuntimeError("Gazebo fixture rejected the operation")
            return response
        except Exception:
            # A timed-out mutation has an unknown outcome. Never retry or continue the run.
            self.ready = False
            raise

    def _state(self) -> tuple[float, float]:
        state = self._call("get_cart_state", {})
        if (
            state["step"] != self.step_index
            or not math.isfinite(state["time"])
            or not math.isclose(state["time"], self.step_index * self.dt, rel_tol=0, abs_tol=1e-8)
            or not all(math.isfinite(state[k]) for k in ("position", "velocity"))
        ):
            self.ready = False
            raise RuntimeError("Gazebo observation does not match the requested step")
        return state["position"], state["velocity"]

    def reset(self, scenario: Scenario) -> tuple[float, float]:
        if self.closed:
            raise RuntimeError("adapter is closed")
        self.ready = False
        if self.transport is None:
            self.transport = GazeboTransport()
        features = self._call("get_simulator_features", {})["features"]
        if not {20, 25, 26, 31, 32} <= set(features):
            raise ValueError("Gazebo fixture lacks required lifecycle capabilities")
        r = scenario.robot
        self.version = self._call(
            "configure_cart",
            {
                "timestep": scenario.world.timestep,
                "mass": r.mass,
                "damping": r.damping,
                "initial_position": r.initial_position,
                "initial_velocity": r.initial_velocity,
            },
        )["adapter_version"]
        self._call("reset_simulation", {"scope": 255})
        self._call("set_simulation_state", {"state": 2})
        self.dt, self.limit, self.step_index = scenario.world.timestep, scenario.world.steps, 0
        state = self._state()
        if not all(
            math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
            for a, b in zip(state, (r.initial_position, r.initial_velocity), strict=True)
        ):
            raise RuntimeError("Gazebo initial state mismatch")
        self.ready = True
        return state

    def step(self, force: float) -> tuple[float, float]:
        if not self.ready or self.closed or self.step_index >= self.limit:
            raise RuntimeError("adapter is not ready or horizon is exhausted")
        if not math.isfinite(force) or abs(force) > 650000:
            raise ValueError("force is outside the scenario bounds")
        self._call("set_cart_force", {"expected_step": self.step_index, "force": force})
        self._call("step_simulation", {"steps": 1})
        self.step_index += 1
        return self._state()

    def close(self) -> None:
        self.ready, self.closed = False, True
        if self.transport is not None:
            self.transport.close()
            self.transport = None


class GazeboTransport:
    """Own one ROS context and one fixed native fixture process; no shell or user assets."""

    def __init__(self):
        import rclpy
        from ament_index_python.packages import get_package_prefix
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        from simulation_interfaces.srv import (
            GetSimulatorFeatures,
            ResetSimulation,
            SetSimulationState,
            StepSimulation,
        )
        from simweave_gazebo.srv import ConfigureCart, GetCartState, SetCartForce

        executable = Path(get_package_prefix("simweave_gazebo")) / "lib/simweave_gazebo/cart_server"
        self.rclpy, self.context = rclpy, Context()
        self.node = self.process = self.directory = self.executor = None
        self.clients = {}
        self.types = {
            "get_simulator_features": GetSimulatorFeatures,
            "reset_simulation": ResetSimulation,
            "set_simulation_state": SetSimulationState,
            "step_simulation": StepSimulation,
            "configure_cart": ConfigureCart,
            "set_cart_force": SetCartForce,
            "get_cart_state": GetCartState,
        }
        try:
            rclpy.init(context=self.context)
            self.executor = SingleThreadedExecutor(context=self.context)
            namespace = f"/simweave_{uuid.uuid4().hex}"
            self.node = rclpy.create_node("experiment", namespace=namespace, context=self.context)
            self.clients = {
                name: self.node.create_client(kind, f"{namespace}/{name}")
                for name, kind in self.types.items()
            }
            self.directory = tempfile.TemporaryDirectory(prefix="simweave-gazebo-")
            # Only runtime search paths and ROS transport selections reach the child.
            env = {
                key: os.environ[key]
                for key in (
                    "PATH",
                    "LD_LIBRARY_PATH",
                    "AMENT_PREFIX_PATH",
                    "RMW_IMPLEMENTATION",
                    "ROS_DOMAIN_ID",
                    "ROS_LOCALHOST_ONLY",
                    "ROS_AUTOMATIC_DISCOVERY_RANGE",
                    "GZ_SIM_SYSTEM_PLUGIN_PATH",
                    "GZ_SIM_PHYSICS_ENGINE_PATH",
                )
                if key in os.environ
            }
            env.update(HOME=self.directory.name, GZ_PARTITION=namespace[1:])
            self.process = subprocess.Popen(
                [str(executable), "--ros-args", "-r", f"__ns:={namespace}"],
                env=env,
                cwd=self.directory.name,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            self.close()
            raise

    def call(self, service: str, fields: dict, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError("Gazebo fixture is not running")
        client = self.clients[service]
        while not client.wait_for_service(
            timeout_sec=min(0.1, max(0, deadline - time.monotonic()))
        ):
            if self.process.poll() is not None:
                raise RuntimeError("Gazebo fixture exited during startup")
            if time.monotonic() >= deadline:
                raise TimeoutError("Gazebo fixture service unavailable")
        request = self.types[service].Request()
        for key, value in fields.items():
            if service == "set_simulation_state" and key == "state":
                request.state.state = value
            else:
                setattr(request, key, value)
        while True:
            future = client.call_async(request)
            remaining = max(0, deadline - time.monotonic())
            # Initial DDS discovery can lose a read-only feature query even after
            # wait_for_service succeeds. Retry only this side-effect-free query,
            # within the original deadline. Never retry configuration or stepping.
            read_only = service == "get_simulator_features"
            self.rclpy.spin_until_future_complete(
                self.node,
                future,
                executor=self.executor,
                timeout_sec=min(1.0, remaining) if read_only else remaining,
            )
            if future.done():
                break
            future.cancel()
            if not read_only or time.monotonic() >= deadline:
                raise TimeoutError("Gazebo call timed out; operation outcome is unknown")
            if self.process.poll() is not None:
                raise RuntimeError("Gazebo fixture exited during discovery")
        response = future.result()
        if service == "get_simulator_features":
            return {"result": 1, "features": list(response.features.features)}
        result = {"result": response.result.result}
        if service == "configure_cart":
            result["adapter_version"] = response.adapter_version
        elif service == "get_cart_state":
            result.update(
                {k: getattr(response, k) for k in ("step", "time", "position", "velocity")}
            )
        return result

    def close(self) -> None:
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self.process = None
        if self.executor is not None:
            self.executor.shutdown(timeout_sec=0)
            self.executor = None
        if self.node is not None:
            self.node.destroy_node()
            self.node = None
        if self.context.ok():
            self.context.shutdown()
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None
