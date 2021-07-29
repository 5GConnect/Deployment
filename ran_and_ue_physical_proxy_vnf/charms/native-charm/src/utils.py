from typing import List, NoReturn

import apt
import subprocess
import yaml

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


def shell(command: str) -> NoReturn:
	subprocess.run(command, shell=True).check_returncode()


def run_process(process_name: str, cmd: str, directory: str):
	subprocess.run(f"cd {directory}", shell=True)
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
	processes[process_name] = process


def edit_gnb_configuration_file(filepath: str, params):
	with open(filepath) as f:
		gnb_configuration = yaml.load(f, Loader=yaml.FullLoader)

	gnb_configuration['ngapIp'] = params['ngap-ip']
	gnb_configuration['gtpIp'] = params['gtp-ip']
	gnb_configuration['amfConfigs'][0]['address'] = params['amf-ip']

	if 'amf-port' in params.keys() and params['amf-port'] != 38412:
		gnb_configuration['amfConfigs'][0]['port'] = params['amf-port']

	with open(filepath, 'w') as f:
		yaml.dump(gnb_configuration, f)


def edit_ue_configuration_file(filepath: str, params):
	with open(filepath) as f:
		ue_configuration = yaml.load(f, Loader=yaml.FullLoader)

	ue_configuration['supi'] = params['usim-imsi']
	ue_configuration['key'] = params['usim-k']
	ue_configuration['op'] = params['usim-opc']
	ue_configuration['opType'] = 'OPC'

	with open(filepath, 'w') as f:
		yaml.dump(ue_configuration, f)


def edit_env_file(filepath, params):
	with open(filepath, "w") as f:
		for key, value in params.items():
			f.write(f"{key}={value}\n")
