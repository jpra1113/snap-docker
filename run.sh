#!/bin/sh

/usr/local/bin/init_snap

python snap_init.py --config $1

# Start Snap daemon
snapteld --plugin-load-timeout 15 -t ${SNAP_TRUST_LEVEL} -l ${SNAP_LOG_LEVEL} -o '' &
SNAP_PID=$(pidof snapteld)

wait $SNAP_PID
