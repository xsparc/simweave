"""Explicit adapters; scenarios cannot import executable code."""

from typing import Protocol

from simweave.contracts import Scenario


class Simulator(Protocol):
    name: str
    version: str

    def reset(self, scenario: Scenario) -> tuple[float, float]: ...
    def step(self, force: float) -> tuple[float, float]: ...
    def close(self) -> None: ...


def create_adapter(name: str) -> Simulator:
    if name == "reference":
        from simweave.adapters.reference import ReferenceSimulator

        return ReferenceSimulator()
    if name == "mujoco":
        from simweave.adapters.mujoco import MujocoSimulator

        return MujocoSimulator()
    if name == "gazebo":
        from simweave.adapters.gazebo import GazeboSimulator

        return GazeboSimulator()
    raise ValueError("unsupported simulator adapter")
