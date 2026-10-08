.PHONY: build container clean


build:
	colcon build
container: 
	devcontainer up
	devcontainer exec --workspace-folder . /bin/bash
clean:
	rm -rf install log build
