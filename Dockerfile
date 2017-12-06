FROM jpra1113/snap:xenial

COPY snap_init.py snap_init.py

ENTRYPOINT ["/usr/local/bin/run.sh"]
