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

UERANSIM_REPO = "https://github.com/DendoD96/UERANSIM.git"
UE_PHYSICAL_PROXY_REPO = "https://github.com/5GConnect/UEDigitalEntity.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)

		self.framework.observe(self.on.configuregnb_action, self.configure_gnb)
		self.framework.observe(self.on.configureue_action, self.configure_ue)
		self.framework.observe(self.on.configureueproxy_action, self.configure_env)
		self.framework.observe(self.on.startgnb_action, self.start_gnb)
		self.framework.observe(self.on.startue_action, self.start_ue)

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
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def configure_gnb(self, event):
		try:
			filepath = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/open5gs-gnb.yaml" \
				if self.config['testing'] \
				else f"{SRC_PATH}/UERANSIM/config/open5gs-gnb.yaml"
			edit_gnb_configuration_file(filepath, event.params)
			event.set_results({"message": "gNB configuration file edited"})
		except Exception as e:
			event.fail(message=f'Error: {str(e)}')

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

	def start_gnb(self, event):
		run_process('gnb', './nr-gnb -c ../config/open5gs-gnb.yaml', f"{SRC_PATH}/UERANSIM/build")
		event.set_results({"message": "gNB start command executed"})

	def start_ue(self, event):
		run_process('ue', 'python3 -m server', f"{SRC_PATH}/UEDigitalEntity/physical_ue_proxy")
		event.set_results({"message": "UE start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
