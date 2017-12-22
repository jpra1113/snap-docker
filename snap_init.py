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


def createInfluxdbDataBase(dbHost='localhost', dbPort=8086, dbUser='root', dbPassword='root', dbName='default'):
    """Initialize db"""
    client = InfluxDBClient(dbHost, dbPort, dbUser, dbPassword, dbName)
    dbList = list(map(lambda x: x['name'], client.get_list_database()))
    if dbName not in dbList:
        try:
            client.create_database(dbName)
        except influxdbExceptions.InfluxDBClientError as e:
            print("[Warn] Failed to create db {}\nException: {}".format(dbName, e))
    else:
        print("List of existing DB")
        print(dbList)


def create_publish_influxdb(publish_obj):
    for i in publish_obj:
        if i['plugin_name'] != 'influxdb':
            continue
        configObj = i['config']
        # NOTE Ignore https case
        createInfluxdbDataBase(configObj['host'],
                               configObj['port'],
                               configObj['user'],
                               configObj['password'],
                               configObj['database'])


def get_deployment_id():
    """Call kubernetes api container to retrieve the deployment id"""
    try:
        config.load_incluster_config()
        nodes = client.CoreV1Api().list_node(watch=False)
        if len(nodes.items) > 0:
            return nodes.items[0].metadata.labels.get("hyperpilot/deployment", "")
    except config.ConfigException:
        print("Failed to load configuration. This container cannot run outside k8s.")
        sys.exit(errno.EPERM)


class Snaptel(object):
    def get_running_tasks(self):
        out, err = self._run_command(["snaptel", "task", "list"])
        if err is not None:
            print("Unable to get running tasks, error: " + err)
            sys.exit(1)
        else:
            task_ids = []
            lines = out.split("\n")
            lines.pop(0)
            for line in lines:
                task_id = line.split(" ")[0]
                if task_id is not '':
                    task_ids.append(task_id)
            return task_ids

    def get_loaded_plugins(self):
        out, err = self._run_command(["snaptel", "plugin", "list"])
        print(out)
        if err is not None:
            print("Unable to get loaded plugins, error: " + err)
            sys.exit(1)
        else:
            loaded_plugins = []
            lines = out.split("\n")
            lines.pop(0)
            for line in lines:
                if 'loaded' in line:
                    loaded_plugins.append(line.split(" ")[0])
            return loaded_plugins

    def wait_until_plugin_loaded(self, plugin, curr_num_plugin):
        retries = 5
        while retries > 0:
            loaded_plugins = self.get_loaded_plugins()
            if len(loaded_plugins) == curr_num_plugin + 1:
                return
            else:
                retries -= 1
                time.sleep(5)
        print("Unable to wait for plugin '" +
              plugin + "' to be loaded. exiting...")
        sys.exit(1)

    def load_plugin(self, plugin, plugin_path):
        print("Loading plugin " + plugin + " from " + plugin_path)
        curr_num_plugin = len(self.get_loaded_plugins())
        retries = 20
        while retries > 0:
            out, err = self._run_command(
                ["snaptel", "plugin", "load", plugin_path])
            if err is not None:
                print("Unable to load plugin " + plugin + ", error: " + err)
                retries -= 1
            else:
                self.wait_until_plugin_loaded(plugin, curr_num_plugin)
                print("Plugin " + plugin_path + " loaded successfully")
                return True
            print("Retrying in 5 seconds")
            time.sleep(5)
        return False

    def run_task(self, task_path):
        print("Running task " + task_path)
        out, err = self._run_command(
            ["snaptel", "task", "create", "-t", task_path])
        if err is not None:
            print("Unable to run task " + task_path + ", error: " + err)
            return False
        else:
            return True

    # Returns either output, or error message in a tuple
    def _run_command(self, args):
        process = subprocess.Popen(
            args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # wait for the process to terminate
        out, err = process.communicate()
        errcode = process.returncode
        if errcode != 0:
            return out, err
        else:
            return out, None


def download_urls(urls, dest_folder=None):
    files = []
    for url in urls:
        local_path = url.split("/")[-1]
        print("Downloading file " + url + " to " + local_path)
        urllib.urlretrieve(url, local_path, context=ctx)
        os.chmod(local_path, 0o755)
        if dest_folder is not None:
            dest_path = os.path.join(dest_folder, local_path)
            os.rename(local_path, dest_path)
            files.append(dest_path)
        else:
            files.append(local_path)
    return files


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
        try:
            config.load_incluster_config()
            pod_service = client.CoreV1Api().read_namespaced_service(service_name, namespace)
            cluster_ip = pod_service.spec.cluster_ip
            port = pod_service.spec.ports[0].port
            url = "http://%s:%s" % (cluster_ip, port)
            print("Replacing k8s service %s to url %s" % (service_name, url))
            return url
        except config.ConfigException:
            print("Failed to load configuration. This container cannot run outside k8s.")
            sys.exit(errno.EPERM)

    def pod_ip_label_selector(self, label_selector, namespace='default'):
        """Call kubernetes api service to get pod ip"""
        try:
            config.load_incluster_config()
            result = client.CoreV1Api().list_namespaced_pod(namespace, label_selector=label_selector)
            pod_name = result.items[0].metadata.name
            pod = client.CoreV1Api().read_namespaced_pod(pod_name, namespace)
            return pod.status.pod_ip
        except config.ConfigException:
            print("Failed to load configuration. This container cannot run outside k8s.")
            sys.exit(errno.EPERM)

    def pod_ip_env_name(self, pod_env_name, namespace='default'):
        """Call kubernetes api service to get pod ip"""
        try:
            config.load_incluster_config()
            return self.pod_ip_label_selector("app=%s" % os.environ[pod_env_name])
        except config.ConfigException:
            print("Failed to load configuration. This container cannot run outside k8s.")
            sys.exit(errno.EPERM)


def main():
    # Initialize
    parser = OptionParser(usage="snap_init [options]")

    parser.add_option(
        '--config',
        action='store',
        type='str',
        dest='config',
        help="Configuration file for snap init"
    )

    opts, args = parser.parse_args()

    if not opts.config:
        print("Config file is required")
        sys.exit(1)

    config_path = opts.config
    if "://" in opts.config:
        config_path = download_urls([opts.config])[0]

    os.environ["DEPLOYMENT_ID"] = get_deployment_id()

    with open(config_path) as json_data:
        j = json.load(json_data)

    snaptel = Snaptel()

    plugins_directory = None
    if "pluginsPath" in j:
        plugins_directory = j["pluginsPath"]
        if not os.path.exists(plugins_directory):
            os.makedirs(plugins_directory)

    tasks_directory = None
    if "tasksPath" in j:
        tasks_directory = j["tasksPath"]
        if not os.path.exists(tasks_directory):
            os.makedirs(tasks_directory)

    if "configsPath" in j:
        configs_directory = j["configsPath"]
        if not os.path.exists(configs_directory):
            os.makedirs(configs_directory)

    plugin_list = j["plugins"]
    plugin_path_list = download_urls(plugin_list.values(), plugins_directory)
    task_list = j["tasks"]
    task_path_list = download_urls(task_list, tasks_directory)
    if "configs" in j:
        configs_list = j["configs"]
        download_urls(configs_list, configs_directory)

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

        # Load Data from JSON file
        # Configure Influxdb
        with open(task, "r") as f:
            j = json.load(f)
            if 'publish' in j.get("workflow", {}).get("collect", {}):
                create_publish_influxdb(
                    j['workflow']['collect']['publish'])
            for process_obj in j.get("workflow", {}).get("collect", {}).get("process", []):
                if 'publish' in process_obj:
                    create_publish_influxdb(process_obj['publish'])

    print("Snap plugins and tasks prepared")

    print("Loading plugins...", plugin_list)
    for plugin, plugin_path in zip(plugin_list, plugin_path_list):
        success = snaptel.load_plugin(plugin, plugin_path)
        if not success:
            print("Timeout when loading plugins")
            sys.exit(1)
    print("Plugins are loaded\n")

    print("Creating tasks...", task_path_list)
    for task_path in task_path_list:
        success = snaptel.run_task(task_path)
        if not success:
            sys.exit(1)
    print("Tasks created\n")

    # Success
    sys.exit(0)


if __name__ == '__main__':
    main()
