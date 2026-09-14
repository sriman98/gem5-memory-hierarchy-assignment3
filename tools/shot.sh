#!/bin/zsh
# usage: shot.sh <outfile.png> <rows> <cols> <settle-seconds> <command...>
OUT="$1"; ROWS="$2"; COLS="$3"; SETTLE="$4"; shift 4; CMD="$*"
ESC_CMD=${CMD//\\/\\\\}; ESC_CMD=${ESC_CMD//\"/\\\"}
WID=$(osascript <<APPLESCRIPT
tell application "Terminal"
  activate
  set w to do script "cd ~/git/gem5-memory-hierarchy-assignment3 && clear"
  set t to selected tab of front window
  set font size of t to ${FONT:-14}
  set number of columns of t to $COLS
  set number of rows of t to $ROWS
  set position of front window to {60, 60}
  delay 1.2
  do script "$ESC_CMD" in front window
  repeat with i from 1 to 600
    delay 0.5
    if not (busy of t) then exit repeat
  end repeat
  delay $SETTLE
  return id of front window
end tell
APPLESCRIPT
)
screencapture -x -o -l "$WID" "$OUT"
osascript -e "tell application \"Terminal\" to close (every window whose id is $WID)" >/dev/null 2>&1
echo "saved $OUT (window $WID)"
