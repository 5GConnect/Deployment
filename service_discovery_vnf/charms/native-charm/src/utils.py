from typing import List, NoReturn

import apt
import subprocess
from jinja2 import Template

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


def shell(command: str) -> NoReturn:
	subprocess.run(command, shell=True).check_returncode()


def configure_service(command: str, working_directory: str, environment_variables: str,
                      service_template: str, service_path: str):
	with open(service_template, "r") as template:
		service_content = Template(template.read()).render(command=command, directory=working_directory,
		                                                   environment=environment_variables)
		with open(service_path, "w") as service:
			service.write(service_content)
		systemctl_daemon_reload()


def systemctl_daemon_reload():
	subprocess.run(["systemctl", "daemon-reload"]).check_returncode()


def systemctl(action: str, service_name: str) -> NoReturn:
	subprocess.run(["systemctl", action, service_name]).check_returncode()
