#!/usr/bin/env python3
import logging
import os

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from utils import (
	install_apt,
	git_clone,
	run_process, shell
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
	"git",
	"nodejs"
]

NODE_DISCOVERY_REPO = "https://github.com/5GConnect/NodeDiscovery.git"
SRC_PATH = "/home/ubuntu/NodeDiscovery"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)
		self.framework.observe(self.on.startservicediscovery_action, self.start_service_discovery)

	def on_install(self, event):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning Node Discovery repo...")
		git_clone(NODE_DISCOVERY_REPO, output_folder=SRC_PATH, branch="develop")
		shell(f"cd {SRC_PATH} && npm install")
		self.unit.status = ActiveStatus()

	def on_start(self, event):
		self.unit.status = ActiveStatus()
	
	def start_service_discovery(self, event):
		all_params = event.params
		command = f"LOG_LEVEL={all_params['log-level']} PORT={all_params['port']} " \
			      f"KEEP_ALIVE_TIME_IN_MS={all_params['keep-alive-time']}  npm run start" \
			if 'log-level' in all_params.keys() else f"PORT={all_params['port']} " \
			                                         f"KEEP_ALIVE_TIME_IN_MS={all_params['keep-alive-time']} npm run start"
		self.unit.status = MaintenanceStatus("Starting Node Discovery service")
		run_process("discovery", command, SRC_PATH)
		self.unit.status = ActiveStatus()



if __name__ == "__main__":
	main(NativeCharmCharm)
