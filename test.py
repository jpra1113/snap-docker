#!/usr/bin/env python

import json
import time
import os
import sys
import urllib
import ssl
import errno
import subprocess

from tempfile import TemporaryFile
from optparse import OptionParser
from jinja2 import Template

from kubernetes import client, config

from influxdb import InfluxDBClient, exceptions as influxdbExceptions

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_deployment_id():
    """Call kubernetes api container to retrieve the deployment id"""
    return "test_deployment_id"


class Accessor(object):
    def env(self, env_name):
        return os.environ[env_name]

    def deployment_id(self):
        """Call kubernetes api container to retrieve the deployment id"""
        try:
            config.load_incluster_config()
            nodes = client.CoreV1Api().list_node(watch=False)
            if len(nodes.items) > 0:
                return nodes.items[0].metadata.labels.get("hyperpilot/deployment", "")
        except config.ConfigException:
            print("Failed to load configuration. This container cannot run outside k8s.")
            sys.exit(errno.EPERM)

    def k8s_service(self, service_name, namespace='default'):
        """Call kubernetes api service to get service cluster ip"""
        return "http://%s:ok" % service_name


def main():

    task_path_list = [
        "/tmp/jpra1113-tech-demo-snap/snap-k8s-docker-cgroups.json"]

    for task in task_path_list:
        with open(task, "r") as f:
            # Double curly braces appears in json too often,
            # so use <%= VAR => expression here instead
            template = Template(f.read(),
                                variable_start_string="<%=",
                                variable_end_string="=>")
            with open(task, "w") as f:
                template_values = {
                    'a': Accessor(),
                }
                f.write(template.render(template_values))

    print("Tasks created\n")

    # Success
    sys.exit(0)


if __name__ == '__main__':
    os.environ["INFLUXSRV_SERVICE_HOST"] = "11111111"
    main()
