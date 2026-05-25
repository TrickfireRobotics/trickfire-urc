# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# ---------- shell behavior ----------
export HISTCONTROL=ignoreboth:erasedups
export HISTSIZE=10000
export HISTFILESIZE=20000
shopt -s histappend checkwinsize

# ---------- colors ----------
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# ---------- lesspipe ----------
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# ---------- ROS environment ----------
_ros_source_env() {
    if [ -n "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]; then
        source "/opt/ros/${ROS_DISTRO}/setup.bash"
    fi
    if [ -n "${ROS_WS:-}" ] && [ -f "${ROS_WS}/install/setup.bash" ]; then
        source "${ROS_WS}/install/setup.bash"
    fi
}

if [ -z "${ROS_ENV_SOURCED:-}" ]; then
    _ros_source_env
    export ROS_ENV_SOURCED=1
fi

# ---------- prompt ----------
_tf_git_branch() {
    git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null
}

_tf_prompt() {
    local branch=""
    local reset="\[\e[0m\]"
    local pink="\[\e[38;2;233;60;171m\]"
    local green="\[\e[38;2;1;255;0m\]"
    local blue="\[\e[38;2;80;170;255m\]"

    branch="$(_tf_git_branch)"
    if [ -n "$branch" ]; then
        branch=" ${blue}(${branch})${reset}"
    fi

    PS1="${pink}\u${reset}:${green}\w${reset}${branch}\\$ "
}
PROMPT_COMMAND="_tf_prompt"

# ---------- aliases ----------
alias c='clear'
alias ll='ls -alF --color=auto'
alias la='ls -A --color=auto'
alias l='ls -CF --color=auto'
alias ..='cd ..'
alias ...='cd ../..'

# ROS
alias rtl='ros2 topic list'
alias rte='ros2 topic echo'
alias rnl='ros2 node list'
alias rni='ros2 node info'
alias rsl='ros2 service list'
alias rpe='ros2 param list'
alias rpg='ros2 param get'
alias rps='ros2 param set'
alias rs='_ros_source_env'

# colcon
alias cb='colcon build --symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON'
alias cbt='colcon build --symlink-install --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=ON --packages-select'
alias ct='colcon test --packages-select'

# Python ruff
alias rf='ruff check .'
alias rff='ruff check . --fix'
alias rfmt='ruff format .'
alias rfcheck='ruff check . && ruff format . --check'

# C++ clang
alias ctidy='clang-tidy'
alias cformat='clang-format -i'

# ---------- helper functions ----------
ros-clean() {
    if [ -z "${ROS_WS:-}" ]; then
        echo "ROS_WS not set"
        return 1
    fi
    rm -rf "${ROS_WS}/build" "${ROS_WS}/install" "${ROS_WS}/log"
    echo "Cleaned build/install/log from ${ROS_WS}"
}

cfmt-all() {
    find . \( -name "*.cpp" -o -name "*.hpp" -o -name "*.h" -o -name "*.cc" \) \
        -not -path "*/build/*" \
        -not -path "*/install/*" \
        | xargs clang-format -i
    echo "clang-format applied"
}

ctidy-all() {
    local build_dir="${ROS_WS:-$PWD}/build"
    find . \( -name "*.cpp" -o -name "*.cc" \) \
        -not -path "*/build/*" \
        -not -path "*/install/*" \
        | xargs clang-tidy -p "$build_dir"
}

# ---------- bash completion ----------
if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi
