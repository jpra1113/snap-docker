#!/usr/bin/env python

import json
import time
import os
import sys
import urllib

from subprocess import check_output, CalledProcessError

from tempfile import TemporaryFile

from optparse import OptionParser

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

    def wait_until_plugin_loaded(self, plugin):
        retries = 5
        while retries > 0:
            loaded_plugins = self.get_loaded_plugins()
            if plugin in loaded_plugins:
                return
            else:
                retries -= 1
                time.sleep(5)
        print("Unable to wait for plugin '" + plugin + "' to be loaded. exiting...")
        sys.exit(1)

    def load_plugin(self, plugin, plugin_path):
        print("Loading plugin " + plugin + " from " + plugin_path)
        retries = 5
        while retries > 0:
            out, err = self._run_command(["snaptel", "plugin", "load", plugin_path])
            if err is not None:
               print("Unable to load plugin " + plugin + ", error: " + err)
               retries -= 1
            else:
               self.wait_until_plugin_loaded(plugin)
               print("Plugin " + plugin_path + " loaded successfully")
               return True
            print("Retrying in 5 seconds")
            time.sleep(5)
        return False

    def run_task(self, task_path):
        print("Running task " + task_path)
        out, err = self._run_command(["snaptel", "task", "create", "-t", task_path])
        if err is not None:
            print("Unable to run task " + task_path + ", error: " + err)
            return False
        else:
            return True

    # Returns either output, or error message in a tuple
    def _run_command(self, args):
        with TemporaryFile() as t:
            try:
                out = check_output(args, stderr=t)
                return out, None
            except OSError as e:
                print("Unexpected OS error running command '" + str(args) + "': " + str(e))
                sys.exit(1)
            except CalledProcessError as e:
                print("Check output called received error: " + str(e))
                return None, t.read()

def download_urls(urls):
    files = []
    for url in urls:
        local_path = url.split("/")[-1]
        print("Downloading file " + url + " to " + local_path)
        urllib.urlretrieve(url, local_path)
        os.chmod(local_path, 0755)
        files.append(local_path)
    return files

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

    with open(config_path) as json_data:
        j = json.load(json_data)

    snaptel = Snaptel()

    plugin_list = j["plugins"]
    print("Loading plugins...")
    for plugin in plugin_list.keys():
        plugin_url = plugin_list[plugin]
        plugin_path = download_urls([plugin_url])[0]
        if not snaptel.load_plugin(plugin, plugin_path):
            print("Unable to load plugin " + plugin + ", exiting...")
            sys.exit(1)

    task_list = j["tasks"]
    downloaded_tasks = download_urls(task_list)
    count = 0
    for task in downloaded_tasks:

            # Replace snap tag value with the enviroment var
            # XXX: This kind of thing will probably be done several times in the
            # future, it'll be better to generalize with things like Jinja2
            conf = json.load(open(task))
            tag = conf["workflow"]["collect"].get("tags", {}).get("/intel", {})
            if "nodename" in tag:
                tag["nodename"] = tag["nodename"].format(**os.environ)
            json.dump(conf, open(task, "w"))

            snaptel.run_task(task)
            count += 1
            # Snap might be running the task although it didn't exit correctly
            running_tasks = snaptel.get_running_tasks()
            if len(running_tasks) != count:
                print("Wasn't able to find task in running tasks '" + str(running_tasks) + "', exiting...")
                sys.exit(1)
            else:
                print("Task '" + task + "' started")

    print("Snap init finished")

if __name__ == '__main__':
    main()
