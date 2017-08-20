FROM ubuntu:16.04

ARG BUILD_DATE
ARG SNAP_VERSION=latest

ENV SNAP_VERSION=${SNAP_VERSION}
ENV SNAP_TRUST_LEVEL=0
ENV SNAP_LOG_LEVEL=1
ENV CI_URL=https://s3-us-west-2.amazonaws.com/snap.ci.snap-telemetry.io

LABEL vendor="Intelsdi-X" \
      name="Snap Ubuntu 16.04" \
      license="Apache 2.0" \
      build-date=$BUILD_DATE \
      io.snap-telemetry.snap.version=$SNAP_VERSION \
      io.snap-telemetry.snap.version.is-beta=

EXPOSE 8181

ADD ${CI_URL}/snap/${SNAP_VERSION}/linux/x86_64/snapteld  /opt/snap/sbin/snapteld
ADD ${CI_URL}/snap/${SNAP_VERSION}/linux/x86_64/snaptel  /opt/snap/bin/snaptel
COPY init_snap /usr/local/bin/init_snap
COPY snapteld.conf /etc/snap/snapteld.conf

COPY run.sh /usr/local/bin/run.sh
COPY snap_init.py snap_init.py
COPY requirements.txt requirements.txt

# To collect perf_events, set kernel.perf_event_paranoid to 0
# sysctl -w kernel.perf_event_paranoid=0
RUN apt-get update > /dev/null && \
    apt-get install -y curl gcc python-dev python-pip \
        jq python python-dev build-essential \
        linux-tools-common linux-tools-generic && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -r requirements.txt && mkdir -p /usr/host

ENTRYPOINT ["/usr/local/bin/run.sh"]
