"""Semi-implicit Euler reference cart, intended for contract tests and demos."""

from simweave.contracts import Scenario


class ReferenceSimulator:
    name = "reference"
    version = "1"

    def reset(self, scenario: Scenario) -> tuple[float, float]:
        self.dt = scenario.world.timestep
        self.mass = scenario.robot.mass
        self.damping = scenario.robot.damping
        self.x = scenario.robot.initial_position
        self.v = scenario.robot.initial_velocity
        return self.x, self.v

    def step(self, force: float) -> tuple[float, float]:
        self.v += self.dt * (force - self.damping * self.v) / self.mass
        self.x += self.dt * self.v
        return self.x, self.v

    def close(self) -> None:
        pass
