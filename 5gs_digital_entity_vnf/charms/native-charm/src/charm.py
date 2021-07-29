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

FIVEGS_DIGITAL_ENTITY_REPO = "https://github.com/5GConnect/5GSDigitalEntity.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)
		
		self.framework.observe(self.on.start5gsde_action, self.start_5gsde)

	def on_install(self, _):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning 5GS Digital Entity repo...")
		git_clone(FIVEGS_DIGITAL_ENTITY_REPO, output_folder=SRC_PATH, branch="develop")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def start_5gsde(self, event):
		all_params = event.params
		command = f"LOG_LEVEL={all_params['log-level']} PORT={all_params['port']} NRF_URL={all_params['nrf-url']} npm " \
		          f"run start" if 'log-level' in all_params.keys() else f"PORT={all_params['port']} " \
		                                                                f"NRF_URL={all_params['nrf-url']} npm run start"
		self.unit.status = MaintenanceStatus("Starting 5GS Digital Entity service")
		run_process("5gs_de", command, f"{SRC_PATH}/NodeDiscovery")
		event.set_results({"message": "5GS Digital Entity start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
