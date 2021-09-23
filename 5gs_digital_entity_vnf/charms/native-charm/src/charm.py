#!/usr/bin/env python3
import logging
import os

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from utils import (
	git_clone,
	shell,
	configure_service, systemctl
)

logger = logging.getLogger(__name__)

SERVICE_NAME="fivegsdigitalentity"
FIVEGS_DIGITAL_ENTITY_SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}.service"
FIVEGS_DIGITAL_ENTITY_SERVICE_TEMPLATE = f"./templates/{SERVICE_NAME}.service"
FIVEGS_DIGITAL_ENTITY_REPO = "https://github.com/5GConnect/5GSDigitalEntity.git"
SRC_PATH = "/home/ubuntu/5GSDigitalEntity"


class NativeCharmCharm(CharmBase):

	def __init__(self, *args):
		super().__init__(*args)

		# Listen to charm events
		self.framework.observe(self.on.install, self.on_install)
		self.framework.observe(self.on.start, self.on_start)

		self.framework.observe(self.on.start5gsde_action, self.start_5gsde)

	def on_install(self, _):
		if not os.path.exists(SRC_PATH):
			os.makedirs(SRC_PATH)
		self.unit.status = MaintenanceStatus("Cloning 5GS Digital Entity repo...")
		git_clone(FIVEGS_DIGITAL_ENTITY_REPO, output_folder=SRC_PATH, branch="develop")
		shell(f"cd {SRC_PATH}/backend && sudo npm install")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = ActiveStatus()

	def start_5gsde(self, event):
		all_params = event.params
		command = "npm run dev"
		environment_variables = [f"PORT={all_params['port']}", f"NRF_URL={all_params['nrfurl']}"]
		if 'loglevel' in all_params.keys():
			environment_variables.append(f"LOG_LEVEL={all_params['loglevel']}")
		self.unit.status = MaintenanceStatus("Generating 5GS Digital Entity service...")
		configure_service(command=command,
		                  working_directory=f"{SRC_PATH}/backend",
		                  environment_variables=" ".join(environment_variables),
		                  service_template=FIVEGS_DIGITAL_ENTITY_SERVICE_TEMPLATE,
		                  service_path=FIVEGS_DIGITAL_ENTITY_SERVICE_PATH)
		self.unit.status = MaintenanceStatus("Starting 5GS Digital Entity service")
		systemctl(action="start", service_name=SERVICE_NAME)
		self.unit.status = ActiveStatus()
		event.set_results({"message": "5GS Digital Entity start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
