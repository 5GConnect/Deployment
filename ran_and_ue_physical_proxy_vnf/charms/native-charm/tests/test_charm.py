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

GNB_CONFIG_FILE = f"{pathlib.Path(__file__).parent.parent.absolute()}/tests/mocked_config_files/open5gs-gnb.yaml"
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

	def test_gnb_basic_config(self):
		content = {'ngapIp': "127.0.0.1", 'gtpIp': "127.0.0.1", 'amfConfigs': [{'address': "127.0.0.5", 'port': 38412}]}
		action_event = Mock(params={"ngap-ip": "192.168.1.1", "gtp-ip": "192.168.1.1", "amf-ip": "192.168.1.1"})
		write_yaml_file(GNB_CONFIG_FILE, content)
		self.harness.charm.configure_gnb(action_event)
		self.assertTrue(action_event.set_results.called)
		self.assertEqual(get_yaml_file_content(GNB_CONFIG_FILE),
		                 {'ngapIp': "192.168.1.1", 'gtpIp': "192.168.1.1",
		                  'amfConfigs': [
			                  {'address': "192.168.1.1", 'port': 38412}]})

	def test_gnb_config_with_port(self):
		content = {'ngapIp': "127.0.0.1", 'gtpIp': "127.0.0.1", 'amfConfigs': [{'address': "127.0.0.5", 'port': 38412}]}
		action_event = Mock(
			params={"ngap-ip": "192.168.1.1", "gtp-ip": "192.168.1.1", "amf-ip": "192.168.1.1", "amf-port": 23456})
		write_yaml_file(GNB_CONFIG_FILE, content)
		self.harness.charm.configure_gnb(action_event)
		self.assertTrue(action_event.set_results.called)
		self.assertEqual(get_yaml_file_content(GNB_CONFIG_FILE),
		                 {'ngapIp': "192.168.1.1", 'gtpIp': "192.168.1.1",
		                  'amfConfigs': [
			                  {'address': "192.168.1.1", 'port': 23456}]})

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
