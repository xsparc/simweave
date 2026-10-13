# DirectionBriefV1: ROS/Gazebo cart implementation

- schema_version: 1
- baseline_commit: 0a6e84b64482226cb2d14d343ca0b2107335ff68
- scanned_at: 2026-10-13
- coverage: repository integration state, ROS standard services, Gazebo physics
  embedding, command ordering, portability, and verification.

| Finding and citation | Source event date | Confidence / relevance | Alignment; opportunity or risk | Cost | Disposition / roadmap delta / verification needed |
| --- | --- | --- | --- | --- | --- |
| [ROS simulation_interfaces](https://github.com/ros-simulation/simulation_interfaces) separates feature discovery, reset, pause, and finite stepping | Undated interface, checked 2026-10-13 | High / high | Supports neutral lifecycle semantics; actuator mapping is fixture-specific | Medium | adopt; SW004 lifecycle services; real request/response tests |
| [Gazebo Server](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1Server.html) supports blocking RunOnce and adding systems | Undated API, checked 2026-10-13 | High / high | Enables an isolated headless world with an explicit physics boundary | Medium | adopt; dedicated native fixture; verify time and cleanup |
| [Gazebo Joint](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1Joint.html) exposes forces, reset state, and position/velocity checks | Undated API, checked 2026-10-13 | High / high | Provides real cart actuation and observations without asynchronous topic races | Medium | adopt; acknowledge forces before stepping; verify analytical first step and native observations |
| [MuJoCo reproducibility](https://mujoco.readthedocs.io/en/stable/computation/index.html) is scoped by runtime version and architecture | Undated documentation, checked 2026-10-13 | High / high | Repeatability and cross-engine agreement require distinct assertions | Low | adopt; repeated seeded runs and tolerance-based comparison |

Overall recommendation: implement the bounded cart integration approved by the
maintainer, using standard lifecycle services plus typed fixture-specific I/O.
Include PR3's already-reviewed dashboard commit as a separate prerequisite because
its original squash merge targeted the feature branch rather than main.

Evidence gaps at design time: live physics initialization and clock semantics,
service round-trip costs, and repeatability must be established by execution.
Results belong in `docs/governance/ros-gazebo-validation.md`.
