# Third-party packages

Upstream packages built from source in this workspace, because the RoboStack binaries are broken for
us. Each overlays the RoboStack package of the same name.

## nav2_mppi_controller 1.3.11

Source: tag `release/jazzy/nav2_mppi_controller/1.3.11-1` of
https://github.com/SteveMacenski/navigation2-release, the same source RoboStack builds. Its `test/`,
`benchmark/`, `media/` and `README.md` are left out.

**Why:** RoboStack's linux-aarch64 build of MPPI is broken on arm64, which covers the sim on Apple
Silicon and the Jetson Orin.

- It's compiled by GCC with xsimd and `-ffast-math`. `-ffast-math` includes `-fno-signed-zeros`,
  which lets GCC treat `-0.0` and `+0.0` as the same constant.
- xsimd's `sin`/`cos` set the sign of their result by XOR with `select(cond, -0.0f, 0.0f)`. GCC folds
  that select away, so for angles beyond ±45° the result has the wrong sign.
- MPPI integrates its candidate trajectories with those functions. Once the rover's heading is far
  from 0 in odom, the critics score trajectories that point the wrong way. The rover then drives away
  from the goal at full speed or stands still.
- Removing either xsimd or `-fno-signed-zeros` fixes it. Clang isn't affected.
- Upstream issue: [navigation2#4380](https://github.com/ros-navigation/navigation2/issues/4380). It
  was only fixed by the Eigen rewrite of MPPI in Kilted.

**Changes to `CMakeLists.txt`:**

- Removed xsimd: `XTENSOR_USE_XSIMD`, `XTENSOR_ENABLE_XSIMD` and `xtensor::use_xsimd`. The pixi
  env's xtensor 0.23.9 can't build against its xsimd 14 anyway.
- Removed `-ffast-math`.
- Removed the `BUILD_TESTING` block, since the tests aren't included.

In a benchmark on an M-series Mac, this costs about 0.3 ms per controller cycle.

**Remove this package** once RoboStack's build is fixed, or once we move to a Nav2 release with the
Eigen MPPI. To check a build, turn the rover about 140° from its starting heading and send a goal
behind it. With the bug, it drives away from the goal.
