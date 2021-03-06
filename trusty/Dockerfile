FROM ubuntu:14.04

ARG BUILD_DATE
ARG SNAP_VERSION=latest

ENV SNAP_VERSION=${SNAP_VERSION}
ENV SNAP_TRUST_LEVEL=0
ENV SNAP_LOG_LEVEL=2
ENV CI_URL=https://s3-us-west-2.amazonaws.com/snap.ci.snap-telemetry.io
ENV SNAP_URL="http://127.0.0.1:8181"

LABEL vendor="Intelsdi-X" \
      name="Snap Ubuntu 14.04" \
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

RUN apt-get update && apt-get install -y curl jq python python-dev python-pip python-openssl sysstat && \
    pip install -r requirements.txt && mkdir -p /usr/host

ENTRYPOINT ["/usr/local/bin/run.sh"]