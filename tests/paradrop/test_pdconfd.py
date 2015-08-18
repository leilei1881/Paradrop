import os

from nose.tools import raises

from paradrop.backend.pdconfd.config.command import Command
from paradrop.backend.pdconfd.config.manager import ConfigManager
from paradrop.backend.pdconfd.config.wireless import ConfigWifiDevice, ConfigWifiIface

CONFIG_FILE = "/tmp/test-config"
WRITE_DIR = "/tmp"


DNSMASQ_CONFIG = """
config interface lan
    option ifname 'eth0'
    option proto 'static'
    option ipaddr '192.168.33.66'
    option netmask '255.255.255.0'

config dnsmasq lan
    list interface 'lan'

config dhcp lan
    option interface 'lan'
    option start '100'
    option limit '100'
    option leasetime '12h'
    list dhcp_option 'option:router,192.168.33.66'
"""


DEFAULT_DNSMASQ_CONFIG = """
config interface lan
    option ifname 'eth0'
    option proto 'static'
    option ipaddr '192.168.33.66'
    option netmask '255.255.255.0'

config dnsmasq lan
    option noresolv '1'
    list server '8.8.8.8'

config dhcp lan
    option interface 'lan'
    option start '100'
    option limit '100'
    option leasetime '12h'
    list dhcp_option 'option:router,192.168.33.66'
"""


FIREWALL_ZONE_CONFIG = """
config interface wan
    option ifname 'eth0'
    option proto 'dhcp'

config zone
    option network 'wan'
    option masq '1'
    option output 'ACCEPT'
    option forward 'REJECT'
    option input 'ACCEPT'
    option name 'wan'
"""

FIREWALL_REDIRECT_CONFIG = """
config interface wan
    option ifname 'eth0'
    option proto 'dhcp'

config zone
    option network 'wan'
    option masq '0'
    option output 'ACCEPT'
    option forward 'REJECT'
    option input 'ACCEPT'
    option name 'wan'

config redirect
    option src 'wan'
    option src_port '6000'
    option proto 'any'
    option dest_ip '192.168.33.66'
    option dest_port '60'

config redirect
    option src 'wan'
    option src_port '7000'
    option proto 'tcp'
    option dest_ip '192.168.33.66'
    option dest_port '70'

config redirect
    option src 'wan'
    option src_ip '1.2.3.4'
    option proto 'tcpudp'
    option dest_ip '192.168.33.66'

config redirect
    option dest 'wan'
    option src_dip '1.2.3.4'
    option proto 'any'
    option target 'SNAT'
"""


NETWORK_WAN_CONFIG = """
config interface eth0
    option ifname 'eth0'
    option proto 'static'
    option ipaddr '192.168.33.66'
    option netmask '255.255.255.0'
    option gateway '192.168.33.1'
"""


NETWORK_BRIDGE_CONFIG = """
config interface lan
    list ifname 'eth1'
    list ifname 'eth2'
    option type 'bridge'
    option proto 'static'
    option ipaddr '192.168.33.66'
    option netmask '255.255.255.0'
"""


WIRELESS_AP_CONFIG = """
config interface wifi
    option ifname 'wlan0'
    option proto 'static'
    option ipaddr '192.168.33.66'
    option netmask '255.255.255.0'

config wifi-device radio
    option type 'auto'
    option channel '1'

config wifi-iface ap1
    option device 'radio'
    option mode 'ap'
    option ssid 'Paradrop1'
    option network 'wifi'
    option encryption 'psk2'
    option key 'password'

config wifi-iface ap2
    option device 'radio'
    option mode 'ap'
    option ssid 'Paradrop2'
    option network 'wifi'
    option encryption 'psk2'
    option key '0000111122223333444455556666777788889999aaaabbbbccccddddeeeeffff'

config wifi-iface ap3
    option device 'radio'
    option mode 'ap'
    option ssid 'Paradrop3'
    option network 'wifi'
    option encryption 'none'
"""

WIRELESS_STA_CONFIG = """
config interface wifi
    option ifname 'wlan0'
    option proto 'dhcp'

config wifi-device radio
    option type 'auto'
    option channel '1'

config wifi-iface sta1
    option device 'radio'
    option mode 'sta'
    option ssid 'Paradrop1'
    option network 'wifi'
    option encryption 'psk2'
    option key 'password'
"""


def write_file(path, data):
    with open(path, "w") as output:
        output.write(data)


def in_commands(substr, commands):
    """
    Test that a string is in the command list
    """
    return any(substr in cmd for cmd in commands)


def test_base():
    """
    Test ConfigObject base class
    """
    wifi_dev1 = ConfigWifiDevice()
    wifi_dev2 = ConfigWifiDevice()
    wifi_iface = ConfigWifiIface()

    # Sections of different type should not match.
    assert not wifi_dev1.optionsMatch(wifi_iface)

    # Sections with different values should not match.
    wifi_dev1.channel = 1
    wifi_dev2.channel = 6
    assert not wifi_dev1.optionsMatch(wifi_dev2)

    # But now they should match.
    wifi_dev2.channel = 1
    assert wifi_dev1.optionsMatch(wifi_dev2)


def test_command():
    """
    Test command execution

    The true and false commands should reliably succeed and fail in most Linux
    environments.
    """
    cmd = ["true"]
    command = Command(0, cmd)
    command.execute()
    assert command.success()

    # Specifying the command as a string instead of a list.
    cmd = "true"
    command = Command(0, cmd)
    command.execute()
    assert command.success()

    cmd = ["false"]
    command = Command(0, cmd)
    command.execute()
    assert not command.success()


def test_config_default_dnsmasq():
    """
    Test configuration of dnsmasq using default (all interfaces)
    """
    write_file(CONFIG_FILE, DEFAULT_DNSMASQ_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    assert len(commands) > 0

    # Should have generated a dnsmasq config file.
    dnsmasq_conf = os.path.join(WRITE_DIR, "dnsmasq-lan.conf")
    assert os.path.exists(dnsmasq_conf)
    os.remove(dnsmasq_conf)


def test_config_dnsmasq():
    """
    Test configuration of dnsmasq where we specify an interface
    """
    write_file(CONFIG_FILE, DNSMASQ_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    assert len(commands) > 0

    # Should have generated a dnsmasq config file.
    dnsmasq_conf = os.path.join(WRITE_DIR, "dnsmasq-lan.conf")
    assert os.path.exists(dnsmasq_conf)
    os.remove(dnsmasq_conf)

    # Write a fake pid file, so we can test the kill command.
    pidFile = os.path.join(WRITE_DIR, "dnsmasq-lan.pid")
    with open(pidFile, 'w') as output:
        output.write("12345")

    manager.unload(execute=False)
    commands = manager.previousCommands

    # Unload should generate a kill command for the fake pid.
    assert in_commands("kill 12345", commands)
    os.remove(pidFile)


def test_config_firewall_zone():
    """
    Test loading a firewall config with WAN zone
    """
    write_file(CONFIG_FILE, FIREWALL_ZONE_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    assert len(commands) == 2

    # Should generate a masquerade rule.
    assert in_commands("MASQUERADE", commands)

    manager.unload(execute=False)
    commands = manager.previousCommands

    assert len(commands) == 2


def test_config_firewall_redirect():
    """
    Test loading a firewall config with redirect rules
    """
    write_file(CONFIG_FILE, FIREWALL_REDIRECT_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    assert len(commands) == 5

    # Should generate a DNAT rule.
    assert in_commands("DNAT", commands)

    # TODO Check for SNAT rule when implemented.
    assert not in_commands("SNAT", commands)

    manager.unload(execute=False)
    commands = manager.previousCommands
    assert len(commands) == 5


def test_config_network_wan():
    """
    Test loading a configuration file that specifies an WAN interface
    """
    write_file(CONFIG_FILE, NETWORK_WAN_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 4

    # One of the commands should assign the given IP address.
    assert in_commands("192.168.33.66", commands)

    # Should add a default route via the gateway.
    assert in_commands("default via 192.168.33.1", commands)

    manager.unload(execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 2


def test_config_network_bridge():
    """
    Test loading a bridge interface config
    """
    write_file(CONFIG_FILE, NETWORK_BRIDGE_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 10

    # Should generate a command to create bridge interface.
    assert in_commands("ip link add name br-lan type bridge", commands)

    # Should assign eth1 and eth2 to bridge.
    assert in_commands("ip link set dev eth1 master br-lan", commands)
    assert in_commands("ip link set dev eth2 master br-lan", commands)

    manager.unload(execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 8

    # Should delete bridge interface.
    assert in_commands("ip link delete br-lan", commands)


def test_config_wireless_ap():
    """
    Test loading a wireless AP config
    """
    write_file(CONFIG_FILE, WIRELESS_AP_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 9

    # Check for command to add ap mode interface.
    assert in_commands("add wlan0 type __ap", commands)

    # Check that one command starts hostapd.
    assert in_commands("hostapd", commands)

    # Should have generated a hostapd config file.
    hostapd_conf = os.path.join(WRITE_DIR, "hostapd-ap1.conf")
    assert os.path.exists(hostapd_conf)
    os.remove(hostapd_conf)

    # Write a fake pid file, so we can test the kill command.
    pidFile = os.path.join(WRITE_DIR, "hostapd-ap1.pid")
    with open(pidFile, 'w') as output:
        output.write("12345")

    manager.unload(execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
    assert len(commands) == 5

    # Unload should generate a kill command for the fake pid.
    assert in_commands("kill 12345", commands)
    os.remove(pidFile)


@raises(Exception)
def test_config_wireless_sta():
    """
    Test loading a wireless sta config

    TODO: Flesh this out after implementing sta mode.
    """
    write_file(CONFIG_FILE, WIRELESS_STA_CONFIG)
    manager = ConfigManager(WRITE_DIR)
    manager.loadConfig(search=CONFIG_FILE, execute=False)
    commands = manager.previousCommands
    for cmd in commands:
        print(cmd)
