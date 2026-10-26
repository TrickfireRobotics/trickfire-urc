.PHONY: build container clean


build:
	colcon build --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
container: 
	devcontainer up
	devcontainer exec --workspace-folder . /bin/bash
clean:
	rm -rf install log build
