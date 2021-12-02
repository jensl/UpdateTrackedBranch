#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2020 Alexander Poole, Opera Software ASA
#
# The UpdateTrackedBranch extensions to the Critic code review system is
# licensed under the Apache License, version 2.0.  You may obtain a copy of the
# License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#

"""
Python script that notifies a Critic system about updated refs

Description
-----------

This script is useful when a Critic system tracks branches from other (remote)
Git repositories.  When it does that, it polls the other repository for updates
on a timer, but rather infrequently.  For a more immediate tracking, this script
tells the Critic system about updated refs in the other repository, so that the
Critic system can schedule an immediate update of its tracking branch.

This script uses the 'Requests' Python package to make HTTP requests.  On a
Debian/Ubuntu system, this can be installed by running the command

  # apt-get install python-requests

or it can be installed using pip by running the command

  # pip install requests

Installation
------------

Look at the gitlab_ci.template for an idea of how to integrate this in your
continous integration pipeline.

Configuration
-------------

This script requires command line input.

usage: updateTrackedBranch.py [-h] [--critic_url CRITIC_URL] [--repository_url REPOSITORY_URL] [--username USERNAME] [--password PASSWORD] [--branch BRANCH] [--debug DEBUG] [--verify VERIFY]

Update tracked critic branch.

Required settings:optional arguments:
  -h, --help            show this help message and exit
  --critic_url CRITIC_URL, -c CRITIC_URL
                        The base URL ("http://<hostname>/") of the Critic system
                        that should be notified about updates.
  --repository_url REPOSITORY_URL, -r REPOSITORY_URL
                        The repository URL ("git@gitlab.com:username/repo.git")
                        that would be used as the remote repository URL in
                        Critic's UI. This value is used by the Critic server-side
                        code to identify the branch being updated and map it to a
                        tracking branch to update.
  --username USERNAME, -u USERNAME
                        Critic username
  --password PASSWORD, -p PASSWORD
                        If username and password are set, they are supplied as
                        HTTP authorization credentials when accessing the Critic
                        system. Since they have to be stored in plain text, it is
                        typically recommended to instead allow anonymous access
                        to the Critic system, at least for the URL accessed by
                        this script. In theory, each user pushing to the
                        repository could set these in their per user Git
                        settings, thus accessing the Critic system as their own
                        Critic user. However, they would still be stored in plain
                        text, so this is not a recommended solution either.
  --ref REF             Git ref to update
  --sha SHA             Git commit sha
  --debug DEBUG         Enable debug prints.
  --verify VERIFY       If set to true, certificate validation is disabled when
                        accessing the Critic system. This is only relevant if the
                        Critic system is accessed over HTTPS.

Note: All these settings need to be configured in the ci pipeline.
"""

import json
import os
import pwd
import sys
import subprocess
import time
import traceback
import argparse

import requests

debug = False

local_username = pwd.getpwuid(os.getuid()).pw_name

log = ["User: " + local_username,
       "Path: " + os.getcwd(),
       "Args: " + " ".join(sys.argv[1:]),
       ""]

hostname = subprocess.check_output(["hostname", "--fqdn"], text=True).strip()

def print_and_log(line, do_print=True):
    log.append(line)
    if do_print:
        sys.stdout.write(line + "\n")

def print_debug(message):
    for line in message.splitlines():
        print_and_log("[critic:debug] %s" % line.encode("utf-8"), debug)
    sys.stdout.flush()

def print_debug_json(data):
    print_debug(json.dumps(data, indent=4, sort_keys=True))

def print_progress(message):
    for line in message.splitlines():
        print_and_log("[critic] %s" % line.encode("utf-8"))
    sys.stdout.flush()

def print_hook(message):
    print_and_log("[critic] %s" % ("-" * 60))
    for line in message.splitlines():
        print_and_log("[critic] %s" % line.encode("utf-8"))
    print_and_log("[critic] %s" % ("-" * 60))
    sys.stdout.flush()

def print_error(message):
    for line in message.splitlines():
        print_and_log("[critic:error] %s" % line.encode("utf-8"))
    sys.stdout.flush()

def pars_arguments():
    parser = argparse.ArgumentParser(description="Update tracked critic branch.")
    parser.add_argument('--critic_url', '-c', type=str, help="""
    The base URL (\"http://<hostname>/\") of the Critic system
    that should be notified about updates.""", required=True)

    parser.add_argument('--repository_url', '-r', type=str, help="""
    The repository URL (\"git@gitlab.com:username/repo.git\")
    that would be used as the remote repository URL in Critic's UI.
    This value is used by the Critic server-side code to identify
    the branch being updated and map it to a tracking branch to update.""", required=True)

    parser.add_argument('--ref', type=str, help="Git ref to update", required=True)
    parser.add_argument('--sha', type=str, help="Git commit sha", required=False)

    parser.add_argument('--username', '-u', type=str, help="Critic username")
    parser.add_argument('--password', '-p', type=str, help="""
    If username and password are set, they are supplied as HTTP authorization credentials
    when accessing the Critic system.  Since they have to be stored in plain text, it
    is typically recommended to instead allow anonymous access to the Critic
    system, at least for the URL accessed by this script.

    In theory, each user pushing to the repository could set these in their per
    user Git settings, thus accessing the Critic system as their own Critic
    user.  However, they would still be stored in plain text, so this is not a
    recommended solution either.
    """)

    parser.add_argument('--debug', help="Enable debug prints.", default=False, required=False, action='store_true')
    parser.add_argument('--verify', help="""
    If set to true, certificate validation is disabled when accessing
    the Critic system.  This is only relevant if the Critic system is accessed
    over HTTPS.
    """, default=False, required=False, action='store_true')

    args = parser.parse_args()
    print_debug(str(args))

    return args

def main(args):

    global debug
    debug = args.debug

    critic_url = args.critic_url
    if not critic_url:
        print_error("No Critic URL set!")
        sys.exit(1)

    if not critic_url.endswith("/"):
        critic_url += "/"

    critic_url += "UpdateTrackedBranch/githook"

    repository_url = args.repository_url

    connection_timeout = 5
    update_timeout = 30

    kwargs = {}

    critic_username = args.username
    critic_password = args.password
    if critic_username and critic_password:
        kwargs["auth"] = (critic_username, critic_password)

    kwargs["verify"] = args.verify

    ref = args.ref

    try:
        # List of (ref, value) tuples.
        refs = []

        try:
            if args.sha:
                value = args.sha
            else:
                value = subprocess.check_output(["git", "rev-parse", ref], text=True).strip()
        except subprocess.CalledProcessError as error:
            value = "0" * 40
        refs.append((ref, value))

        print_debug(f"{refs}")

        for ref, value in refs:
            start = time.time()
            deadline = start + connection_timeout

            def issue_request(trigger=False):
                data = { "remote": repository_url,
                         "name": ref,
                         "value": value,
                         "disable_remote_transform": True }
                if trigger:
                    data["trigger"] = True

                print_debug_json(data)

                response = requests.post(
                    critic_url,
                    data=json.dumps(data),
                    timeout=(deadline - time.time()) + 0.5,
                    **kwargs)
                response.raise_for_status()
                data = json.loads(response.content)
                if data["status"] != "ok":
                    raise Exception("Request failed: " + data["error"])
                return data

            try:
                data = issue_request(trigger=True)
            except requests.exceptions.Timeout:
                print_error("Timeout (%ds) while notifying Critic!"
                            % connection_timeout)
                raise

            print_debug_json(data)

            if "review" in data:
                print_progress("Review: %s" % data["review"])
            elif "branch" in data:
                print_progress("Tracked branch: %s" % data["branch"])
            else:
                print_debug("Nothing to update!")
                continue

            if "disabled" in data:
                print_progress("Tracking is disabled!")
            elif "update_ongoing" in data:
                print_progress("Update already in progress.")
            elif "update_pending" in data:
                print_progress("Update already scheduled.")
            elif "update_triggered" in data:
                if "review" not in data:
                    print_progress("Update scheduled.")
                    continue

                print_progress("Update triggered; waiting for it to complete...")

                deadline = start + update_timeout
                time.sleep(0.5)

                while time.time() < deadline:
                    try:
                        data = issue_request()
                    except requests.exceptions.Timeout:
                        # The loop condition will be false now, so this effectively
                        # breaks out of the loop.  We don't use 'break' since we
                        # want the loop's else branch to execute.
                        continue

                    if "hook_output" in data:
                        if not data["update_successful"]:
                            print_error("Critic rejected the update!")
                        print_hook(data["hook_output"])
                        break
                    elif not ("update_ongoing" in data or
                              "update_pending" in data):
                        print_progress("Update completed without output.")
                        break

                    remaining = deadline - time.time()

                    if remaining > 0:
                        time.sleep(min(0.5, remaining))
                else:
                    print_progress("Timeout while waiting for update to complete.")
    except Exception as e:
        print_debug("Exception:")
        print_debug(traceback.format_exc())
        # We want to make sure that any CI running this fails on exception
        raise e

if __name__ == '__main__':
    main(pars_arguments())