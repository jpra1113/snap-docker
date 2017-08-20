#!/bin/sh

# To install perf tool on Ubuntu 16.04
echo "Install perf tool ..."
apt-get update > /dev/null && apt-get install -y linux-tools-`uname -r`

/usr/local/bin/init_snap

echo "args: $@"

# Start Snapteld in background job
echo "Starting snaptel deamon in background"
snapteld -t ${SNAP_TRUST_LEVEL} -l ${SNAP_LOG_LEVEL} -o '' &

# Start Snap_init.py in foreground job
echo "Starting python in foreground"
python snap_init.py --config $1 
exit_status=$?
echo "exit status: $exit_status"

# Check exit status
if [ $exit_status -ne "0" ]
	then
	exit 1 # Unable to load plugin OR create tasks after trialsche. Let k8s to restart this pod
fi
echo "Plugins are sucessfully loaded"
echo "Tasks are sucessfully created"

wait $(pidof snapteld)
