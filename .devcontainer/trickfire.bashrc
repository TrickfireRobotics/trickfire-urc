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

alias rtl='ros2 topic list'
alias rte='ros2 topic echo'

alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'




source /opt/ros/"${ROS_DISTRO}"/setup.bash
