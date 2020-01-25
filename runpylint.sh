#!/usr/bin/bash
# This script will check gnome-abrt for any pylint warning and errors using a set
# of options minimizing false positives.

# XDG_RUNTIME_DIR is "required" to be set, so make one up in case something
# actually tries to do something with it
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="$(mktemp -d)"
    trap "rm -rf \"$XDG_RUNTIME_DIR\"" EXIT
fi

python3 -m pylint $@
