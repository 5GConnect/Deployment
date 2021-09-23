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
	edit_ue_configuration_file,
	edit_env_file, systemctl, configure_service,
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
	"iproute2",
	"npm",
	"python3-pip",
	"xfce4",
	"xfce4-goodies",
	"tightvncserver"
]

DASHJS_REPO = "https://github.com/5GConnect/dash.js"
UE_SMART_ENTITIES_REPO = "https://github.com/5GConnect/UEDigitalEntity.git"
UERANSIM_REPO = "https://github.com/DendoD96/UERANSIM.git"

SRC_PATH_DASH = "/home/ubuntu/dash.js"
SRC_PATH_UERANSIM = "/home/ubuntu/UERANSIM"
SRC_PATH_UE_SMART_ENTITIES = "/home/ubuntu/UEDigitalEntity"

UE_SERVICE_NAME = "physicalueproxy"
UE_SERVICE_PATH = f"/etc/systemd/system/{UE_SERVICE_NAME}.service"
UE_SERVICE_TEMPLATE = f"./templates/{UE_SERVICE_NAME}.service"

UE_SMART_ENTITIES_SERVICE_NAME = "uedigitalentity"
UE_SMART_ENTITIES_SERVICE_PATH = f"/etc/systemd/system/{UE_SMART_ENTITIES_SERVICE_NAME}.service"
UE_SMART_ENTITIES_TEMPLATE = f"./templates/{UE_SMART_ENTITIES_SERVICE_NAME}.service"

DASHJS_SERVICE_NAME = "dashjs"
DASHJS_SERVICE_PATH = f"/etc/systemd/system/{DASHJS_SERVICE_NAME}.service"
DASHJS_SERVICE_TEMPLATE = f"./templates/{DASHJS_SERVICE_NAME}.service"

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
		if not os.path.exists(SRC_PATH_DASH):
			os.makedirs(SRC_PATH_DASH)
		if not os.path.exists(SRC_PATH_UERANSIM):
			os.makedirs(SRC_PATH_UERANSIM)
		if not os.path.exists(SRC_PATH_UE_SMART_ENTITIES):
			os.makedirs(SRC_PATH_UE_SMART_ENTITIES)
		self.unit.status = MaintenanceStatus("Configuring vnc server")
		configuration_lines=["#!/bin/bash", "xrdb /home/ubuntu/.Xresources", "startxfce4 &"]
		shell('mkdir -p /home/ubuntu/.vnc && touch /home/ubuntu/.vnc/xstartup')
		for line in configuration_lines:
			shell(f'echo "{line}" >> /home/ubuntu/.vnc/xstartup')
		shell('touch /home/ubuntu/.vnc/passwd')
		shell("echo demopaper123 | vncpasswd -f > /home/ubuntu/.vnc/passwd")
		shell("chmod +x /home/ubuntu/.vnc/xstartup")
		self.unit.status = MaintenanceStatus("Cloning UERANSIM repo...")
		git_clone(UERANSIM_REPO, output_folder=SRC_PATH_UERANSIM, branch="paper_demo")
		self.unit.status = MaintenanceStatus("Buildig UERANSIM...")
		shell(f"cd {SRC_PATH_UERANSIM} && make")
		self.unit.status = MaintenanceStatus("Cloning UE Digital Entity repo...")
		git_clone(UE_SMART_ENTITIES_REPO, output_folder=SRC_PATH_UE_SMART_ENTITIES, branch="develop")
		shell(f"cd {SRC_PATH_UE_SMART_ENTITIES}/backend && npm install")
		shell(f"cd {SRC_PATH_UE_SMART_ENTITIES}/physical_ue_proxy && pip install -r requirements.txt")
		self.unit.status = MaintenanceStatus("Cloning Dash js repo...")
		git_clone(DASHJS_REPO, output_folder=SRC_PATH_DASH, branch="development")
		shell(f"cd {SRC_PATH_DASH} && npm install")
		self.unit.status = ActiveStatus()

	def on_start(self, _):
		self.unit.status = MaintenanceStatus("Starting vnc server")
		shell("vncserver -geometry 1920x1080")
		self.unit.status = ActiveStatus()

	def configure_ue(self, event):
		try:
			filepath = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/open5gs-ue.yaml" \
				if self.config['testing'] \
				else f"{SRC_PATH_UERANSIM}/config/open5gs-ue.yaml"
			edit_ue_configuration_file(filepath, event.params)
			self.unit.status = ActiveStatus()
			event.set_results({"message": "UE configuration file edited"})
		except Exception as e:
			event.fail(message=f'Error: {str(e)}')

	def configure_env(self, event):
		try:
			filepath = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/.env" \
				if self.config['testing'] \
				else f"{SRC_PATH_UE_SMART_ENTITIES}/physical_ue_proxy/server/.env"
			edit_env_file(filepath, {'UERANSIM_BASE_DIR': SRC_PATH_UERANSIM, 'UE_CONFIG_FILE': 'open5gs-ue.yaml'})
			self.unit.status = ActiveStatus()
			event.set_results({"message": "UE proxy env file edited"})
		except Exception as e:
			event.fail(message=f'Error: {str(e)}')

	def start_ue(self, event):
		command = f"python3 -m {SRC_PATH_UE_SMART_ENTITIES}/physical_ue_proxy/server"
		self.unit.status = MaintenanceStatus("Generating UE service...")
		configure_service(command=command,
		                  service_template=UE_SERVICE_TEMPLATE,
		                  service_path=UE_SERVICE_PATH)
		self.unit.status = MaintenanceStatus("Starting UE service")
		systemctl(action="start", service_name=UE_SERVICE_NAME)
		event.set_results({"message": "UE start command executed"})

	def start_uede(self, event):
		all_params = event.params
		command = "npm run dev"
		environment_variables = [f"PORT={all_params['port']}", f"ADDRESS={all_params['address']}",
		                         f"PHYSICAL_UE_PROXY_ADDRESS={all_params['physical-ue-proxy-url']}",
		                         f"DIGITAL_ENTITY_5GS={all_params['de-5gs-url']}",
		                         f"SERVICE_REGISTRY={all_params['service-registry-url']}",
		                         f"POLLING_STATUS_UPDATE_TIME_IN_MS={all_params['polling-time']}",
		                         f"KEEP_ALIVE_TIME_IN_MS={all_params['keep-alive-time']}"]
		if 'loglevel' in all_params.keys():
			environment_variables.append(f"LOG_LEVEL={all_params['loglevel']}")

		self.unit.status = MaintenanceStatus("Generating UE Digital Entity service...")
		configure_service(command=command,
		                  working_directory=f"{SRC_PATH_UE_SMART_ENTITIES}/backend",
		                  environment_variables=" ".join(environment_variables),
		                  service_template=UE_SMART_ENTITIES_TEMPLATE,
		                  service_path=UE_SMART_ENTITIES_SERVICE_PATH)
		self.unit.status = MaintenanceStatus("Starting UE Digital Entity service")
		systemctl(action="start", service_name=UE_SMART_ENTITIES_SERVICE_NAME)
		self.unit.status = ActiveStatus()
		event.set_results({"message": "UE Digital Entity start command executed"})

	def start_dashjs(self, event):
		command = "npm run start"
		self.unit.status = MaintenanceStatus("Generating Dash.js service...")
		configure_service(command=command,
		                  working_directory=SRC_PATH_DASH,
		                  service_template=DASHJS_SERVICE_TEMPLATE,
		                  service_path=DASHJS_SERVICE_PATH)
		self.unit.status = MaintenanceStatus("Starting Dash.js")
		systemctl(action="start", service_name=DASHJS_SERVICE_NAME)
		self.unit.status = ActiveStatus()
		event.set_results({"message": "Dashjs start command executed"})


if __name__ == "__main__":
	main(NativeCharmCharm)
