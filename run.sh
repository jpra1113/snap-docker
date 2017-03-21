#!/bin/sh

/usr/local/bin/init_snap

# Start Snap daemon
snapteld --plugin-load-timeout 15 -t ${SNAP_TRUST_LEVEL} -l ${SNAP_LOG_LEVEL} -o '' &
SNAP_PID=$(pidof snapteld)

python snap_init.py --config $1

wait $SNAP_PID
