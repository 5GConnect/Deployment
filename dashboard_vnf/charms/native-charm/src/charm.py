#!/usr/bin/env python3
import logging
import os

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus

from utils import (
    install_apt,
    git_clone,
    configure_service,
    shell,
    systemctl
)

logger = logging.getLogger(__name__)

APT_REQUIREMENTS = [
    "git",
    "nodejs",
    "npm"
]
SERVICE_NAME = "dashboard"
DASHBOARD_SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}.service"
DASHBOARD_SERVICE_TEMPLATE = f"./templates/{SERVICE_NAME}.service"

DASHBOARD_REPO = "https://github.com/5GConnect/dashboard.git"
SRC_PATH = "/home/ubuntu/dashboard"


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
        shell(f"cd {SRC_PATH} && npm install")
        self.unit.status = ActiveStatus()

    def on_start(self, _):
        self.unit.status = ActiveStatus()

    def start_dashboard(self, event):
        all_params = event.params
        command = "npm run dev"
        self.unit.status = MaintenanceStatus("Generating dashboard service...")
        configure_service(command=command,
                          working_directory=SRC_PATH,
                          environment_variables=f"VUE_APP_DISCOVERY_SERVICE={all_params['discoveryserviceurl']} " \
                                                f"VUE_APP_DISCOVERY_5GS_DE={all_params['systemserviceurl']}",
                          service_template=DASHBOARD_SERVICE_TEMPLATE,
                          service_path=DASHBOARD_SERVICE_PATH)
        self.unit.status = MaintenanceStatus("Starting system's dashboard")
        systemctl(action="start", service_name=SERVICE_NAME)
        self.unit.status = ActiveStatus()
        event.set_results({"message": "System's dashboard start command executed"})


if __name__ == "__main__":
    main(NativeCharmCharm)
