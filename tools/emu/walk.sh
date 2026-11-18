#!/bin/bash
# walk.sh name "keys" "keys" ... : one screenshot after each key group (hpress keys), all joined in
# build/shots/walk/name.png (3 per row). For walking menus: walk.sh inn "X w w" "Down X w w"
D=$(cd "$(dirname "$0")" && pwd); O="$D/../../build/shots/walk"; mkdir -p "$O"
n=0; f=()
for g in "${@:2}"; do n=$((n+1)); p="$O/$1_$n.png"; "$D/hpress.sh" "$p" $g; f+=("$p"); done
"$D/../../.venv/bin/python" "$D/sheet.py" "$O/$1.png" "${f[@]}" && rm -f "${f[@]}"
