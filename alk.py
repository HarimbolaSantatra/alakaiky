#!/usr/bin/env python

import subprocess
import argparse
import yaml
import logging
import os
from typing import List

CONFIG_FILE = "{}/.alk.yaml".format(os.getcwd())

def print_config_format():
    print("""
Here is the format of the yaml file:
username: santatra
ip: MY_IP_ADD
remote_home: /home/santatra/
""")

def config_invalid():
    print(f"Some configuration data is missing! Please check your config file: {CONFIG_FILE}")
    print_config_format()

def file_not_found():
    print("Config file is missing")
    print_config_format()

try:
    with open(CONFIG_FILE, 'r') as conf_file:
        conf = yaml.safe_load(conf_file)
        try:
            USERNAME = conf["username"]
            IP = conf["ip"]
            REMOTE_HOME = conf["remote_home"]
        except KeyError:
            config_invalid()
            exit(2)
except FileNotFoundError:
    file_not_found()
    exit(3)


REMOTE_REF = "{}@{}".format(USERNAME, IP)
DEFAULT_DEST_DIR = "./alk-dest/"


def exec_on_remote(
        cmds: list, 
        dry_run=False,
        debug=False,
        is_root=True
        ):
    """execute a sets of command on a remote host"""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    logging.debug("Beginning execution on remote ...")
    remote_cmd = ""
    iteration = 0
    nb_cmd = len(cmds)
    logging.debug(f"len of cmds is: {len(cmds)}")
    for cmd in cmds:
        logging.debug(f"cmd: {cmd}")
        if is_root:
            remote_cmd += "sudo "
        remote_cmd += cmd + " "
        logging.debug(f"result: {remote_cmd}")
        iteration += 1
        logging.debug(f"iteration: {iteration}")
        if iteration != nb_cmd:
            remote_cmd += " && "
    remote_cmd = "ssh -t {0} \"{1}\"".format(
            REMOTE_REF,
            remote_cmd
            )

    if dry_run:
        print("\n======== EXEC ON REMOTE")
        print("Command to run on remote:\n\t{}".format(remote_cmd))
        print("========\n")
    else:
        logging.info("Command: {}".format(remote_cmd))
        logging.info("Executing subprocess ...")
        subprocess.run(remote_cmd, shell=True, check=False)


def change_perm(pmode: str, remote_files: list):
    """Change files permission

    Parameters
    ----------
    pmode : str 
        Permission mode in GNU version mode (e.g: 777). Other format are not supported yet: +w, o-x, etc
    remote_file : list
        List of full path on the remote file
    """
    files = " ".join(remote_files)
    logging.info("PermissionFiles: {}".format(", ".join(remote_files)))
    logging.info(f"Changin permission to {pmode}")
    perm_cmd = f"sudo chmod {pmode} {files}"
    exec_on_remote([perm_cmd])


def set_own(own: str, grp: str, files: List[str]):
    """Set file owner to current user if none of own and grp is specified."""
    own = own or USERNAME
    grp = grp or USERNAME
    logging.info("Fixing permission")
    f = " ".join(files)
    perm_cmd = f"sudo chown own:grp {f}"
    exec_on_remote([perm_cmd])


def push(local_files: List[str], dests: List[str],
         dry_run=False,
         debug=False, is_root=True,
         perm=None,
         owner=None,
         group=None):
    """
    Sync local file to remote destination.
    files: local files
    dests: destination folders
    """

    logging.info("Running push")

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    if not dests:
        print("Destination file empty !")
        print("Maybe you forget to use the -s option.")
        exit(-2)

    if len(local_files) != len(dests):
        logging.critical("length of local and destination file does not match in push operation !")
        exit(-1)

    files: str = " ".join(local_files)

    logging.info("Remote files to copy: {}".format(files))

    # sync to REMOTE_HOME first
    logging.debug("Copying from local to {}:{}".format(
        REMOTE_REF, REMOTE_HOME))
    rsync_cmd = "rsync -aP {0} {1}".format(
            files,
            "{}:{}".format(REMOTE_REF, REMOTE_HOME)
            )
    if dry_run:
        print("\n======== PUSH")
        print("Command on local:\n\t{}".format(rsync_cmd))
        print("=========\n")
    subprocess.run(rsync_cmd, shell=True, check=True)

    # ... then sync to remote root folder: dest
    rsync_cmd = ""
    for i in range(len(dests)):
        rsync_cmd += "rsync -aP {0} {1}".format(
                "{}/{}".format(REMOTE_HOME, local_files[i]),
                dests[i]
                )
        if i != (len(dests) - 1):
            rsync_cmd += " && "

    logging.debug("Command to execute on remote server: {}".format(rsync_cmd))
    logging.debug("dry_run: " + str(dry_run))
    logging.debug("is_root: " + str(is_root))

    exec_on_remote(
            [rsync_cmd],
            dry_run=dry_run,
            debug=debug,
            is_root=is_root,
            )

    files_basenames = []
    for f in local_files:
        files_basenames.append(os.path.basename(f))

    base_dirs = []
    for b in dests:
        base_dirs.append(os.path.dirname(b))


    if perm:
        perm = str(perm)
        for i in range(len(files_basenames)):
            full_remote_files = files_basenames[i] + base_dirs[i]
            change_perm(perm, full_remote_files)
            if owner and group:
                set_own(owner, group, full_remote_files)
            elif owner:
                set_own(owner, owner, full_remote_files)




def pull(
        remote_files: list,
        dry_run=False,
        debug=False,
        is_root=True,
        dest_dir=None
        ):
    """ 
    Retrieve files on remote server and put it into the DEFAULT_DEST_DIR directory
    remote_files: a list of full files path
    """
    logging.info("Running pull")

    # sync to root folder -> REMOTE_HOME first

    if not dest_dir:
        dest_dir = DEFAULT_DEST_DIR
    logging.info(f"Setting destination dir to {dest_dir}")

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    logging.info("Remote file to copy: {}".format(
        ", ".join(remote_files)))

    rsync_cmd = []
    for i in range(len(remote_files)):
        rsync_cmd.append("rsync -aP {0} {1}".format(
            remote_files[i],
            REMOTE_HOME))

    exec_on_remote(rsync_cmd,
                   dry_run=dry_run,
                   debug=debug,
                   is_root=is_root)

    set_own()

    # ... then sync to REMOTE_HOME -> local
    rsync_cmd = "rsync ".format(REMOTE_REF)

    remote_home_files = []
    for files in remote_files:
        remote_home_files.append(os.path.basename(files))

    for i in range(len(remote_home_files)):
        rsync_cmd += "{}:{}/{} ".format(REMOTE_REF, REMOTE_HOME, remote_home_files[i])
    rsync_cmd += dest_dir
    logging.info(f"Copying to {dest_dir}")
    if dry_run:
        print("\n======== PULL")
        print("Remote files to copy: {}".format(
            ", ".join(remote_home_files)
            ))
        print("Command on local host: {}".format(rsync_cmd))
        print("========\n")
    else:
        subprocess.run(rsync_cmd, shell=True, check=True)


def bad_test():
    root_location = "/var/ossec"
    # /var/ossec is not readable for non-root user
    cmds = [
            f"ls -lh {root_location}"
            ]
    exec_on_remote(cmds,
                   is_root=True)
    exec_on_remote(cmds,
                   is_root=False)


def map_log_level(level: str):
    """
    handle log level. Map a 'level' string to a log level
    """
    level = level.lower()
    if level == "debug":
        return logging.DEBUG
    elif level == "info":
        return logging.INFO
    elif level == "warning":
        return logging.WARNING
    elif level == "error":
        return logging.ERROR
    elif level == "critical":
        return logging.CRITICAL
    elif level == "debug":
        return logging.WARNING
    else:
        return logging.WARNING


def main():

    # Set parser
    parser = argparse.ArgumentParser(description="Copy files between remote and local environment")

    # Main positional argument
    parser.add_argument("operation",
                        help="Main operation: push | pull")

    parser.add_argument("-f", "--file",
                        dest="files",
                        help=f"Specify files for the main operation. (file to push or to pull). Can be multiple.",
                        metavar="FILE",
                        action="append",
                        required=True)
    parser.add_argument("-n", "--dry-run",
                        dest="dry_run",
                        help=f"Do not execute. Instead, execute a dry-run",
                        action="store_true")
    parser.add_argument("-l", "--log",
                        default="warning",
                        dest="log_level",
                        metavar="LOG",
                        help=f"Set log level: CRITICAL | DEBUG | INFO | WARNING (default)")
    parser.add_argument("-o", "--no-root",
                        dest="is_root",
                        help="Execute remote command without sudo privileges. Default to false.",
                        action="store_false")
    parser.add_argument("-d", "--dest-pull",
                        type=str,
                        dest="dest",
                        help="Specify destination directory for pull command. Ignored if command is not 'pull'",
                        action="store")
    parser.add_argument("-s", "--dest-push",
                        help="Specify destination directory on the remote server for push command.  Ignored if command is not 'push'",
                        action="append",
                        dest="remote_dests"
                        )

    # Permission and owner related arguments
    parser.add_argument("-p", "--perm",
                        help="Set permission for all the file after the copy."
                        )

    args = parser.parse_args()

    log_level = map_log_level(args.log_level)
    logging.basicConfig(level=log_level)
    logging.debug("Configuration done.")
    logging.debug("REMOTE_HOME is " + REMOTE_HOME)
    logging.debug("IP is " + IP)
    logging.debug("USERNAME is " + USERNAME)

    operation = args.operation.lower()

    if operation == 'push':
        push(
                args.files,
                args.remote_dests,
                dry_run=args.dry_run,
                is_root=args.is_root,
                perm="640",
                owner="root",
                group="wazuh"
                )
    elif operation == 'pull':
        pull(args.files,
             debug=args.log_level, 
             dry_run=args.dry_run,
             is_root=args.is_root,
             dest_dir=args.dest
             )
    else:
        print("Unknown operation!")
        exit(1)




if __name__ == '__main__':
    main()
