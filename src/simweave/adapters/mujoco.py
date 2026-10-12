"""Headless MuJoCo adapter using only a generated, built-in cart model."""

from simweave.contracts import Scenario


class MujocoSimulator:
    name = "mujoco"

    def __init__(self):
        import mujoco

        self.mj = mujoco
        self.version = mujoco.__version__

    def reset(self, scenario: Scenario) -> tuple[float, float]:
        r = scenario.robot
        # All interpolated values are validated numbers, never user XML or paths.
        xml = f'''<mujoco model="simweave-cart">
          <option timestep="{scenario.world.timestep}" gravity="0 0 0" integrator="Euler"/>
          <worldbody><body name="cart">
            <joint name="slide" type="slide" axis="1 0 0" damping="{r.damping}"/>
            <geom type="sphere" size="0.1" mass="{r.mass}" contype="0" conaffinity="0"/>
          </body></worldbody>
          <actuator><motor joint="slide" gear="1"/></actuator>
        </mujoco>'''
        self.model = self.mj.MjModel.from_xml_string(xml)
        self.data = self.mj.MjData(self.model)
        self.mj.mj_resetData(self.model, self.data)
        self.data.qpos[0] = r.initial_position
        self.data.qvel[0] = r.initial_velocity
        self.mj.mj_forward(self.model, self.data)
        return float(self.data.qpos[0]), float(self.data.qvel[0])

    def step(self, force: float) -> tuple[float, float]:
        self.data.ctrl[0] = force
        self.mj.mj_step(self.model, self.data)
        return float(self.data.qpos[0]), float(self.data.qvel[0])

    def close(self) -> None:
        self.data = None
        self.model = None
