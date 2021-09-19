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

DASHBOARD_REPO = "https://github.com/5GConnect/dashboard.git"
SRC_PATH = "/home/ubuntu"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)
		self.framework.observe(self.on.startdashboard_action, self.start_dashboard)

	def on_install(self, _):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS, update=True)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning Dashboard repo...")
		git_clone(DASHBOARD_REPO, output_folder=SRC_PATH, branch="develop")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def start_dashboard(self, event):
		all_params = event.params
		command = f"VUE_APP_DISCOVERY_SERVICE={all_params['discovery-service-url']} npm run build:prod && serve -s dist"
		self.unit.status = MaintenanceStatus("Starting system's dashboard")
		run_process("dashboard", command, f"{SRC_PATH}/dashboard")
		event.set_results({"message": "System's dashboard start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
