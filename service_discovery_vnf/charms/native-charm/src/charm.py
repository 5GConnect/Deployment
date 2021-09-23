#!/usr/bin/env python3
import logging
import os

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from utils import (
	install_apt,
	git_clone,
	shell,
	configure_service, systemctl
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
	"git",
	"nodejs",
	"npm"
]

SERVICE_NAME="nodediscovery"
NODE_DISCOVERY_SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}.service"
NODE_DISCOVERY_SERVICE_TEMPLATE = f"./templates/{SERVICE_NAME}.service"
NODE_DISCOVERY_REPO = "https://github.com/5GConnect/NodeDiscovery.git"
SRC_PATH = "/home/ubuntu/NodeDiscovery"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)
		self.framework.observe(self.on.startservicediscovery_action, self.start_service_discovery)

	def on_install(self, _):
		self.unit.status = MaintenanceStatus("Installing apt packages")
		install_apt(packages=APT_REQUIREMENTS)
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning Node Discovery repo...")
		git_clone(NODE_DISCOVERY_REPO, output_folder=SRC_PATH, branch="develop")
		shell(f"cd {SRC_PATH} && npm install")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def start_service_discovery(self, event):
		all_params = event.params
		command = "npm run dev"
		environment_variables = [f"PORT={all_params['port']}", f"KEEP_ALIVE_TIME_IN_MS={all_params['keepalivetime']}"]
		if 'loglevel' in all_params.keys():
			environment_variables.append(f"LOG_LEVEL={all_params['loglevel']}")
		self.unit.status = MaintenanceStatus("Generating Node Discovery service")
		configure_service(command=command,
		                  working_directory=SRC_PATH,
		                  environment_variables=" ".join(environment_variables),
		                  service_template=NODE_DISCOVERY_SERVICE_TEMPLATE,
		                  service_path=NODE_DISCOVERY_SERVICE_PATH)
		systemctl(action="start", service_name=SERVICE_NAME)
		self.unit.status = ActiveStatus()
		event.set_results({"message": "Discovery service start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
