#!/usr/bin/env python3

import logging
import os

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
    systemctl, configure_service,
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
    "git",
    "python3-pip",
    "net-tools"
]

RX_REPO = "https://github.com/canalplus/rx-player.git"
UE_SMART_ENTITIES_REPO = "https://github.com/5GConnect/UEDigitalEntity.git"
UERANSIM_REPO = "https://github.com/DendoD96/UERANSIM.git"
UERANSIM_SERVICE_TEMPLATE = f"./templates/open5gs-ue.yaml"

SRC_PATH_RX = "/home/ubuntu/rxplayer"
SRC_PATH_UERANSIM = "/home/ubuntu/UERANSIM"
SRC_PATH_UE_SMART_ENTITIES = "/home/ubuntu/UEDigitalEntity"

UE_SERVICE_NAME = "physicalueproxy"
UE_SERVICE_PATH = f"/etc/systemd/system/{UE_SERVICE_NAME}.service"
UE_SERVICE_TEMPLATE = f"./templates/{UE_SERVICE_NAME}.service"

UE_SMART_ENTITIES_SERVICE_NAME = "uedigitalentity"
UE_SMART_ENTITIES_SERVICE_PATH = f"/etc/systemd/system/{UE_SMART_ENTITIES_SERVICE_NAME}.service"
UE_SMART_ENTITIES_TEMPLATE = f"./templates/{UE_SMART_ENTITIES_SERVICE_NAME}.service"

RX_SERVICE_NAME = "rx"
RX_SERVICE_PATH = f"/etc/systemd/system/{RX_SERVICE_NAME}.service"
RX_SERVICE_TEMPLATE = f"./templates/{RX_SERVICE_NAME}.service"


class NativeCharmCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)

        # Listen to charm events
        self.framework.observe(self.on.install, self.on_install)
        self.framework.observe(self.on.start, self.on_start)

        self.framework.observe(self.on.configureue_action, self.configure_ue)
        self.framework.observe(self.on.startue_action, self.start_ue)
        self.framework.observe(self.on.startuede_action, self.start_uede)
        self.framework.observe(self.on.startrx_action, self.start_rx)

    def on_install(self, _):
        self.unit.status = MaintenanceStatus("Installing apt packages")
        install_apt(packages=APT_REQUIREMENTS, update=True)
        shell("sudo snap install cmake --classic")
        if not os.path.exists(SRC_PATH_RX):
            os.makedirs(SRC_PATH_RX)
        if not os.path.exists(SRC_PATH_UERANSIM):
            os.makedirs(SRC_PATH_UERANSIM)
        if not os.path.exists(SRC_PATH_UE_SMART_ENTITIES):
            os.makedirs(SRC_PATH_UE_SMART_ENTITIES)
        self.unit.status = MaintenanceStatus("Cloning UE Digital Entity repo...")
        git_clone(UE_SMART_ENTITIES_REPO, output_folder=SRC_PATH_UE_SMART_ENTITIES, branch="develop")
        shell(f"cd {SRC_PATH_UE_SMART_ENTITIES}/backend && npm install")
        shell(f"cd {SRC_PATH_UE_SMART_ENTITIES}/physical_ue_proxy && pip install -r requirements.txt")
        self.unit.status = MaintenanceStatus("Cloning RX player repo...")
        git_clone(RX_REPO, output_folder=SRC_PATH_RX, branch="master")
        shell(f"cd {SRC_PATH_RX} && npm install && npm run build")
        self.unit.status = ActiveStatus()

    def on_start(self, _):
        self.unit.status = ActiveStatus()

    def configure_ue(self, event):
        try:
            filepath = f"{SRC_PATH_UERANSIM}/config/open5gs-ue.yaml"
            edit_ue_configuration_file(UERANSIM_SERVICE_TEMPLATE, filepath, event.params)
            self.unit.status = ActiveStatus()
            event.set_results({"message": "UE configuration file edited"})
        except Exception as e:
            event.fail(message=f'Error: {str(e)}')

    def start_ue(self, event):
        command = f"python3 -m server"
        environment_variables = [f"UERANSIM_BASE_DIR={SRC_PATH_UERANSIM}", f"UE_CONFIG_FILE=open5gs-ue.yaml"]
        self.unit.status = MaintenanceStatus("Generating UE service...")
        configure_service(command=command,
                          environment_variables=" ".join(environment_variables),
                          working_directory=f"{SRC_PATH_UE_SMART_ENTITIES}/physical_ue_proxy/",
                          service_template=UE_SERVICE_TEMPLATE,
                          service_path=UE_SERVICE_PATH)
        self.unit.status = MaintenanceStatus("Starting UE service")
        systemctl(action="start", service_name=UE_SERVICE_NAME)
        event.set_results({"message": "UE start command executed"})

    def start_uede(self, event):
        all_params = event.params
        command = "npm run dev"
        environment_variables = [f"PORT={all_params['port']}", f"ADDRESS={all_params['address']}",
                                 f"PHYSICAL_UE_PROXY_ADDRESS={all_params['physicalueproxyurl']}",
                                 f"DIGITAL_ENTITY_5GS={all_params['de5gsurl']}",
                                 f"SERVICE_REGISTRY={all_params['serviceregistryurl']}",
                                 f"POLLING_STATUS_UPDATE_TIME_IN_MS={all_params['pollingtime']}",
                                 f"KEEP_ALIVE_TIME_IN_MS={all_params['keepalivetime']}"]
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

    def start_rx(self, event):
        command = "npm run start"
        self.unit.status = MaintenanceStatus("Generating Rx player service...")
        configure_service(command=command,
                          working_directory=SRC_PATH_RX,
                          service_template=RX_SERVICE_TEMPLATE,
                          service_path=RX_SERVICE_PATH)
        self.unit.status = MaintenanceStatus("Starting Rx player")
        systemctl(action="start", service_name=RX_SERVICE_NAME)
        self.unit.status = ActiveStatus()
        event.set_results({"message": "Rx player start command executed"})


if __name__ == "__main__":
    main(NativeCharmCharm)
