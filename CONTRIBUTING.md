# Contributing

Thanks for wanting to contribute to this repo! This guide covers the layout of the repo and how to work on each part.

## Repo structure

```
trickfire-urc/
├── src-autonomy/    # ROS 2 workspace for high level things, more details below
├── src-platform/    # ROS 2 workspace for low level things, more details below
├── docs/            # Documentation site (Astro / Starlight)
└── pyproject.toml   # Python tooling config
```

## ROS Workspaces

There are 2 ROS source directories in this repo, and they should never directly call code on each other (method calls etc). The only way they interact is by using ROS topics. `src-autonomy` talks to either mission controll, or uses the autonomous package and then publishes data like motor commands or requests to ROS topics. `src-platform` then listens on those topics and handles the data coming through them, like moving specific motors. It can then post data to other topics, like telemetry, camera image etc., and `src-autonomy` forwards it to mission controll or autonomous handles it.

### `src-autonomy/`

The ROS 2 workspace containing high level code.

**Packages:**

- TODO: write packages as we decide on them and list their purpouse

### `src-platform/`

The ROS 2 workspace containing low level code.

**Packages:**

- TODO: write packages as we decide on them and list their purpouse

### `docs/` - Documentation site

An [Astro Starlight](https://starlight.astro.build/) site published to GitHub Pages. Make sure you add a header in the individual markdown files (`---` sections) and use proper Astro Starlight syntax (like for callout blocks or codeblocks). You can locally test the docs by running the following commands in your shell. This assumes you have `npm` installed:

```bash
cd docs
npm install
npm run dev
```

If you want to add a doc page, add a markdown file in its content folder in `docs/content/docs`. Do not forget to route it in `docs/astro.config.mjs` in the `sidebar` section.

## Formatting

All formatters run automatically on save in VS Code, using extensions installed in the devcontainer. They are:

| Language               | Formatter                                                    |
| ---------------------- | ------------------------------------------------------------ |
| Python                 | [Ruff](https://docs.astral.sh/ruff/) (`charliermarsh.ruff`)  |
| Shell (bash)           | [shfmt](https://github.com/patrickvane/shfmt) (`mkhl.shfmt`) |
| Astro                  | Astro (`astro-build.astro-vscode`)                           |
| JS / TS / JSON / JSONC | Prettier (`esbenp.prettier-vscode`)                          |
| Dockerfile             | Docker (`ms-azuretools.vscode-containers`)                   |

For Python and Shell, there is a GitHub CI, but you can also run Ruff manually before submitting. Both of these formatters are setup using CLI in the devcontainer, so you can run the following commands to check locally:

```bash
ruff check .    # To check if everything is formatted
ruff format .   # To format and fix issues
```

```bash
shfmt -w $(git ls-files '*.sh')     # To check if everything is formatted
shfmt -d $(git ls-files '*.sh')     # To format and fix issues
```

The shell command has the nested git command to ignore things in the gitignore (mainly ROS install files) that should not be checked. Ruff has a configuration in `pyproject.toml` so it does not need it.
