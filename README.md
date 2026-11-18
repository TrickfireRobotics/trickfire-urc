<h1 align="center">TrickFire URC</h1>

> [!NOTE]
> This repo will get renamed to the name of our new rover as it is with the viator repo. The name is not yet picked out, so we are using a general temporary name, but it will change!

TrickFire's codebase for our new rover for the [University Rover Challenge](https://urc.marssociety.org/).

Two ROS 2 workspaces, [`src-autonomy`](src-autonomy) and [`src-platform`](src-platform), talking to each other only over ROS topics, built and run inside a shared Docker devcontainer.

## Documentation

**Full documentation is at [docs.trickfirerobotics.com/trickfire-urc](https://docs.trickfirerobotics.com/trickfire-urc)**

- [Getting Started](https://docs.trickfirerobotics.com/trickfire-urc) - open the devcontainer, build, and launch
- [Architecture](https://docs.trickfirerobotics.com/trickfire-urc/architecture) - how `src-autonomy` and `src-platform` divide responsibility
- [Creating a Package](https://docs.trickfirerobotics.com/trickfire-urc/creating-a-package) - scaffold a new ROS 2 package
- [Building, Launching, and Testing](https://docs.trickfirerobotics.com/trickfire-urc/building-and-testing) - the `make` workflow
- [Connecting to the Simulator](https://docs.trickfirerobotics.com/trickfire-urc/simulation) - bridge topics to Gazebo running outside the container

See [CONTRIBUTING.md](https://github.com/TrickfireRobotics/trickfire-urc?tab=contributing-ov-file) for repo layout and formatting conventions.
