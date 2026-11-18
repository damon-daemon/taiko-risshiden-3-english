#!/bin/bash
# newgame.sh [out.png] : cold boot the English build (CUE= for another image) and go to the first
# message window of a new game: title -> 最初から始める -> story choice ("物語を選択してください",
# message window, MESSAGE block of the start scene). ~45 s. Further Circle presses: Hideyoshi story
# confirm (yes/no) -> ability type menu -> type confirm with the stats panel.
# Special Tale (name entry): Right BEFORE the first Circle, Circle (confirm), Circle ("Change the name?" yes).
D=$(cd "$(dirname "$0")" && pwd)
WAIT=25 "$D/restart.sh" >/dev/null 2>&1
"$D/hpress.sh" /dev/null Return w w w w w
"$D/hpress.sh" /dev/null Return w w w w w
"$D/hpress.sh" /dev/null Up w X w w w   # one Up: the cursor starts on Continue (card has a save); the menu wraps
if [ -n "$1" ]; then "$D/hshot.sh" "$1"; fi
