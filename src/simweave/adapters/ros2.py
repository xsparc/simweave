"""Optional ROS 2 lifecycle bridge; never pretends to be a cart experiment adapter."""

from __future__ import annotations

import re
from typing import Protocol


class RosTransport(Protocol):
    def call(self, service: str, fields: dict, timeout: float) -> dict: ...
    def close(self) -> None: ...


class RosControl:
    def __init__(self, transport: RosTransport, timeout: float = 5.0):
        if not 0 < timeout <= 60:
            raise ValueError("timeout must be between zero and 60 seconds")
        self.transport = transport
        self.timeout = timeout

    def features(self) -> set[int]:
        response = self.transport.call("get_simulator_features", {}, self.timeout)
        return set(response["features"])

    def _require(self, features: set[int]) -> None:
        if not features <= self.features():
            raise ValueError("ROS simulator does not advertise required capabilities")

    def _checked(self, service: str, fields: dict) -> None:
        allowed = {1, 101} if service == "set_simulation_state" else {1}
        if self.transport.call(service, fields, self.timeout).get("result") not in allowed:
            raise RuntimeError("ROS simulator rejected the operation")

    def reset(self) -> None:
        # Scope ALL requires all reset scopes; never assume a reset re-seeds the simulator.
        self._require({20, 21, 22, 23})
        self._checked("reset_simulation", {"scope": 255})

    def step(self, steps: int = 1) -> None:
        if type(steps) is not int or not 1 <= steps <= 20_000:
            raise ValueError("steps must be an integer from 1 to 20000")
        self._require({25, 26, 31 if steps == 1 else 32})
        self._checked("set_simulation_state", {"state": 2})
        self._checked("step_simulation", {"steps": steps})


class RclpyTransport:
    def __init__(self, namespace: str = "/gzserver"):
        if not re.fullmatch(r"/(?:[A-Za-z_][A-Za-z0-9_]*(?:/[A-Za-z_][A-Za-z0-9_]*)*)?", namespace):
            raise ValueError("invalid ROS service namespace")
        import rclpy
        from rclpy.context import Context
        from simulation_interfaces.srv import (
            GetSimulatorFeatures,
            ResetSimulation,
            SetSimulationState,
            StepSimulation,
        )

        self.rclpy = rclpy
        self.context = Context()
        rclpy.init(context=self.context)
        self.node = rclpy.create_node("simweave_control", context=self.context)
        self.namespace = namespace.rstrip("/")
        self.types = {
            "get_simulator_features": GetSimulatorFeatures,
            "reset_simulation": ResetSimulation,
            "set_simulation_state": SetSimulationState,
            "step_simulation": StepSimulation,
        }

    def call(self, service: str, fields: dict, timeout: float) -> dict:
        import time

        deadline = time.monotonic() + timeout
        kind = self.types[service]
        client = self.node.create_client(kind, f"{self.namespace}/{service}")
        try:
            if not client.wait_for_service(timeout_sec=timeout):
                raise TimeoutError("ROS service unavailable")
            request = kind.Request()
            for key, value in fields.items():
                if service == "set_simulation_state" and key == "state":
                    request.state.state = value
                else:
                    setattr(request, key, value)
            future = client.call_async(request)
            self.rclpy.spin_until_future_complete(
                self.node, future, timeout_sec=max(0.0, deadline - time.monotonic())
            )
            if not future.done():
                future.cancel()
                raise TimeoutError("ROS service timed out; operation outcome is unknown")
            response = future.result()
            if service == "get_simulator_features":
                return {"features": list(response.features.features)}
            return {"result": response.result.result}
        finally:
            self.node.destroy_client(client)

    def close(self) -> None:
        self.node.destroy_node()
        self.context.shutdown()
