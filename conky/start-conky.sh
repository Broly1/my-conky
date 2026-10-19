#!/bin/bash
# Conky's Wayland backend can't request a specific output, so KWin puts the
# layer surface on the active output. Make the target output active first.
TARGET=${CONKY_OUTPUT:-DP-1}
QDBUS=$(command -v qdbus6 || command -v qdbus)

pkill -x conky

for _ in 1 2 3 4; do
    [ "$($QDBUS org.kde.KWin /KWin org.kde.KWin.activeOutputName)" = "$TARGET" ] && break
    $QDBUS org.kde.kglobalaccel /component/kwin \
        org.kde.kglobalaccel.Component.invokeShortcut "Switch to Next Screen"
    sleep 0.2
done

exec ${CONKY_BIN:-conky} -c "$HOME/.config/conky/conky.conf"
