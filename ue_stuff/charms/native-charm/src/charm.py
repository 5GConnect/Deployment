#!/usr/bin/env python3

import logging
import os
import pathlib

from ops.charm import CharmBase
from ops.model import (
	MaintenanceStatus,
	ActiveStatus,
)
from ops.main import main

from utils import (
	install_apt,
	git_clone,
	shell,
	edit_gnb_configuration_file,
	edit_ue_configuration_file,
	edit_env_file,
	run_process
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
	"git",
	"nodejs",
	"make",
	"gcc",
	"g++",
	"libsctp-dev",
	"lksctp-tools",
	"iproute2"
]

DASHJS_REPO = "https://github.com/5GConnect/dash.js"
UE_DIGITAL_ENTITY_REPO = UE_PHYSICAL_PROXY_REPO = "https://github.com/5GConnect/UEDigitalEntity.git"
UERANSIM_REPO = "https://github.com/DendoD96/UERANSIM.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)

		self.framework.observe(self.on.configureue_action, self.configure_ue)
		self.framework.observe(self.on.configureueproxy_action, self.configure_env)
		self.framework.observe(self.on.startue_action, self.start_ue)
		self.framework.observe(self.on.startuede_action, self.start_uede)
		self.framework.observe(self.on.startdashjs_action, self.start_dashjs)


	def on_install(self, _):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		shell("sudo snap install cmake --classic")
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning UERANSIM repo...")
		git_clone(UERANSIM_REPO, output_folder=SRC_PATH, branch="paper_demo")
		self.unit.status = MaintenanceStatus("Buildig UERANSIM...")
		shell(f"cd {SRC_PATH}/UERANSIM && make")
		self.unit.status = MaintenanceStatus("Cloning UEPhysicalProxy repo...")
		git_clone(UE_PHYSICAL_PROXY_REPO, output_folder=SRC_PATH, branch="develop")
		shell(f"cd {SRC_PATH}/UEDigitalEntity/physical_ue_proxy && pip install -r requirements.txt")
		self.unit.status = MaintenanceStatus("Cloning UE Digital Entity repo...")
		git_clone(UE_DIGITAL_ENTITY_REPO, output_folder=SRC_PATH, branch="develop")
		self.unit.status = MaintenanceStatus("Cloning Dash js repo...")
		git_clone(DASHJS_REPO, output_folder=SRC_PATH, branch="development")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def configure_ue(self, event):
		try:
			filepath = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/open5gs-ue.yaml" \
				if self.config['testing'] \
				else f"{SRC_PATH}/UERANSIM/config/open5gs-ue.yaml"
			edit_ue_configuration_file(filepath, event.params)
			event.set_results({"message": "UE configuration file edited"})
		except Exception as e:
			event.fail(message=f'Error: {str(e)}')

	def configure_env(self, event):
		try:
			filepath = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/.env" \
				if self.config['testing'] \
				else f"{SRC_PATH}/UEDigitalEntity/physical_ue_proxy/server/.env"
			edit_env_file(filepath, {'UERANSIM_BASE_DIR': f'{SRC_PATH}/UERANSIM', 'UE_CONFIG_FILE': 'open5gs-ue.yaml'})
			event.set_results({"message": "UE proxy env file edited"})
		except Exception as e:
			event.fail(message=f'Error: {str(e)}')

	def start_ue(self, event):
		run_process('ue', 'python3 -m server', f"{SRC_PATH}/UEDigitalEntity/physical_ue_proxy")
		event.set_results({"message": "UE start command executed"})

	def start_uede(self, event):
		all_params = event.params
		command = f"LOG_LEVEL={all_params['log-level']} PORT={all_params['port']} ADDRESS={all_params['address']} " \
		          f"PHYSICAL_UE_PROXY_ADDRESS={all_params['physical-ue-proxy-url']} " \
		          f"DIGITAL_ENTITY_5GS={all_params['de-5gs-url']}  SERVICE_REGISTRY={all_params['service-registry-url']}" \
		          f"POLLING_STATUS_UPDATE_TIME_IN_MS={all_params['polling-time']} " \
		          f"KEEP_ALIVE_TIME_IN_MS={all_params['keep-alive-time']}  npm run start" \
			if 'log-level' in all_params.keys() else f"PORT={all_params['port']} ADDRESS={all_params['address']} " \
			                                         f"PHYSICAL_UE_PROXY_ADDRESS={all_params['physical-ue-proxy-url']} " \
			                                         f"DIGITAL_ENTITY_5GS={all_params['de-5gs-url']}  SERVICE_REGISTRY={all_params['service-registry-url']}" \
			                                         f"POLLING_STATUS_UPDATE_TIME_IN_MS={all_params['polling-time']} " \
			                                         f"KEEP_ALIVE_TIME_IN_MS={all_params['keep-alive-time']} npm run start"
		self.unit.status = MaintenanceStatus("Starting UE Digital Entity service")
		run_process("ue_de", command, f"{SRC_PATH}/UEDigitalEntity/backend")
		event.set_results({"message": "UE Digital Entity start command executed"})		

	def start_dashjs(self, event):
		run_process('dashjs', 'npm run start', f"{SRC_PATH}/dash.js")
		event.set_results({"message": "Dashjs start command executed"})

if __name__ == "__main__":
	main(NativeCharmCharm)
