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

NODE_DISCOVERY_REPO = "https://github.com/5GConnect/NodeDiscovery.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)

	def on_install(self, event):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning Node Discovery repo...")
		git_clone(NODE_DISCOVERY_REPO, output_folder=SRC_PATH, branch="develop")
		self.unit.status = ActiveStatus()

	def on_start(self, event):
		self.unit.status = MaintenanceStatus("Starting Node Discovery service")
		run_process("discovery", "npm run start", f"{SRC_PATH}/NodeDiscovery")
		self.unit.status = ActiveStatus()


if __name__ == "__main__":
	main(NativeCharmCharm)
