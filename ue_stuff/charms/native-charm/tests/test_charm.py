# Copyright 2021 Daniele Rossi
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import pathlib
import yaml
import unittest
from unittest.mock import Mock

from src.charm import NativeCharmCharm
from ops.testing import Harness

UE_CONFIG_FILE = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/open5gs-ue.yaml"
ENV_FILE = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/.env"


def write_yaml_file(filename, content):
	with open(filename, 'w') as file:
		yaml.dump(
			content,
			file)


def get_yaml_file_content(filename):
	with open(filename, 'r') as file:
		return yaml.load(file, Loader=yaml.FullLoader)


def get_file_content(filename):
	with open(filename, 'r') as file:
		return file.read()


def files_cleanup():
	open(GNB_CONFIG_FILE, 'w').close()
	open(UE_CONFIG_FILE, 'w').close()


class TestCharm(unittest.TestCase):

	def setUp(self):
		self.harness = Harness(NativeCharmCharm, config='{"options": {"testing": {"default": True}}}')
		self.harness.begin()

	def tearDown(self):
		files_cleanup()

	# open(ENV_FILE, 'w').close()

	def test_ue_config(self):
		content = {'supi': "imsi-901700000000001", 'key': "465B5CE8B199B49FAA5F0A2EE238A6BC",
		           'op': 'E8ED289DEBA952E4283B54E88E6183CA'}
		action_event = Mock(params={'usim-imsi': "imsi-901700000000002", 'usim-k': "465B5CE8B199B49FAA5F0A2EE238A6BD",
		                            'usim-opc': 'E8ED289DEBA952E4283B54E88E6183CB'})
		write_yaml_file(UE_CONFIG_FILE, content)
		self.harness.charm.configure_ue(action_event)
		self.assertTrue(action_event.set_results.called)
		self.assertEqual(get_yaml_file_content(UE_CONFIG_FILE),
		                 {'supi': "imsi-901700000000002", 'key': "465B5CE8B199B49FAA5F0A2EE238A6BD",
		                  'op': 'E8ED289DEBA952E4283B54E88E6183CB', 'opType': 'OPC'})

	def test_ue_proxy_config(self):
		action_event = Mock(params={})
		self.harness.charm.configure_env(action_event)
		self.assertTrue(action_event.set_results.called)
		self.assertEqual("UERANSIM_BASE_DIR=/home/ubuntu/UERANSIM\nUE_CONFIG_FILE=open5gs-ue.yaml\n",
		                 get_file_content(ENV_FILE))
