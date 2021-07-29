from typing import List, NoReturn

import apt
import subprocess

processes = {}


# Original source code of following functions:
# https://github.com/charmed-osm/srs-enb-ue-operator/blob/master/src/utils.py

def install_apt(packages: List, update: bool = False):
	cache = apt.cache.Cache()
	if update:
		cache.update()
	cache.open()
	for package in packages:
		pkg = cache[package]
		if not pkg.is_installed:
			pkg.mark_install()
	cache.commit()


def git_clone(
		repo: str,
		output_folder: str = None,
		branch: str = None,
		depth: int = None,
):
	command = ["git", "clone"]
	if branch:
		command.append(f"--branch={branch}")
	if depth:
		command.append(f"--depth={depth}")
	command.append(repo)
	if output_folder:
		command.append(output_folder)
	subprocess.run(command).check_returncode()


def run_process(process_name: str, cmd: str, directory: str):
	subprocess.run(f"cd {directory}", shell=True)
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
	processes[process_name] = process
