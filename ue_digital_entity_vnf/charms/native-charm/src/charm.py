#!/usr/bin/env python3
import logging
import os

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from utils import (
	install_apt,
	git_clone,
	run_process
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
	"git",
	"nodejs"
]

UE_DIGITAL_ENTITY_REPO = "https://github.com/5GConnect/UEDigitalEntity.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)

		self.framework.observe(self.on.startuede_action, self.start_uede)

	def on_install(self, event):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning UE Digital Entity repo...")
		git_clone(UE_DIGITAL_ENTITY_REPO, output_folder=SRC_PATH, branch="develop")
		self.unit.status = ActiveStatus()

	def on_start(self, event):
		self.unit.status = ActiveStatus()

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


if __name__ == "__main__":
	main(NativeCharmCharm)
