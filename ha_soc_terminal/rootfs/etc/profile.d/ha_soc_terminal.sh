# shellcheck shell=bash
# HA SOC Terminal: the shell's readability and history rules. Sourced by every login bash.

# History: one line per command with a timestamp, appended as it happens so a
# killed session loses nothing, persisted under /data when the option is on.
if [ "${HA_SOC_TERM_HISTORY:-true}" = "true" ]; then
    HISTFILE="${HA_SOC_TERM_HISTORY_FILE:-/data/.bash_history}"
else
    HISTFILE=/dev/null
fi
export HISTFILE
export HISTSIZE=50000
export HISTFILESIZE=50000
export HISTTIMEFORMAT='%Y-%m-%d %H:%M:%S  '
export HISTCONTROL=ignoredups
shopt -s histappend
shopt -s checkwinsize
PROMPT_COMMAND="history -a${PROMPT_COMMAND:+; ${PROMPT_COMMAND}}"

# Idle timeout: a courtesy for a forgotten tab, not a control; a running
# program does not honour it.
if [ "${HA_SOC_TERM_IDLE_MINUTES:-0}" -gt 0 ] 2>/dev/null; then
    TMOUT=$(( HA_SOC_TERM_IDLE_MINUTES * 60 ))
    export TMOUT
fi

# Prompt: user, host, directory, and the last exit status in red when non-zero.
# OSC 133;A marks "a new prompt is about to be drawn": the panel's "copy last
# output" feature (terminal-view.ts) uses it, together with the OSC 133;C mark
# below, to bound exactly the previous command's output in the scrollback.
__ha_soc_prompt() {
    local status=$?
    local red='\[\e[31m\]' green='\[\e[32m\]' blue='\[\e[34m\]' dim='\[\e[2m\]' reset='\[\e[0m\]'
    local mark="${green}\$${reset}"
    if [ "${status}" -ne 0 ]; then
        mark="${red}${status} \$${reset}"
    fi
    printf '\e]133;A\a'
    PS1="${dim}soc${reset} ${blue}\w${reset} ${mark} "
}
# OSC 133;C marks "output is about to start": bash runs PS0 after reading a
# command, before running it (bash 4.4+, present in this image's bash).
PS0='\e]133;C\a'
PROMPT_COMMAND="__ha_soc_prompt${PROMPT_COMMAND:+; ${PROMPT_COMMAND}}"

# Colour for the readers.
if command -v dircolors >/dev/null 2>&1; then
    eval "$(dircolors -b)"
fi
alias ls='ls --color=auto'
alias grep='grep --color=auto'
alias ll='ls -la --color=auto'
export EDITOR=nano
# Read-only colourised view of a file: nano in view mode with the syntax files.
alias view='nano -v'
export LESS="-R"
export PAGER="less"

# jq (JSON) and less (paging, used above as PAGER) are both already in this
# image; DOCS.md did not say so, which made them look like they had to be
# piped through nano or cat -A to be usable. See DOCS.md.

# CDPATH so `cd config` (or `cd homeassistant`) works from anywhere, not
# just /root; a courtesy for whichever name ends up real (see the /config
# symlink attempt in the start script).
export CDPATH=".:/homeassistant:/root"

# Log-tail helpers, thin wraps over the `ha` CLI's own logs subcommands so a
# pasted command from an assistant does not have to be a full `ha` invocation
# to be recognisable. Each takes the same arguments `ha ... logs` does.
corelog() { ha core logs "$@"; }
suplog() { ha supervisor logs "$@"; }
hostlog() { ha host logs "$@"; }
applog() {
    if [ -z "${1:-}" ]; then
        echo "usage: applog <slug>" >&2
        return 2
    fi
    local slug="$1"
    shift
    ha apps logs "${slug}" "$@"
}

# Where to start.
cd /homeassistant 2>/dev/null || cd /root || true

if [ -n "${HA_SOC_TERM_SESSION_ID:-}" ]; then
    if [ "${HA_SOC_TERM_RECORD:-true}" = "true" ]; then
        printf 'HA SOC Terminal %s  session %s  recorded\n' "${HA_SOC_TERM_VERSION:-}" "${HA_SOC_TERM_SESSION_ID}"
    else
        printf 'HA SOC Terminal %s  session %s  not recorded\n' "${HA_SOC_TERM_VERSION:-}" "${HA_SOC_TERM_SESSION_ID}"
    fi
    if [ -e /config ]; then
        printf 'view <file> reads YAML in colour; nano edits it. This shell reaches /homeassistant (also /config, also ~/config) and nothing beyond this server.\n'
    else
        printf 'view <file> reads YAML in colour; nano edits it. This shell reaches /homeassistant (also ~/config, also the HA_CONFIG variable; /config could not be created here) and nothing beyond this server.\n'
    fi
    printf 'corelog, suplog, hostlog, applog <slug> tail the Supervisor logs; supervisor-api <path> is a GET-only wrapper over the Supervisor API.\n'
fi
