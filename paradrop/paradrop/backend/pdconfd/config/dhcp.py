import ipaddress

from pdtools.lib.output import out

from .base import ConfigObject
from .command import Command


class ConfigDhcp(ConfigObject):
    typename = "dhcp"

    options = [
        {"name": "interface", "type": str, "required": True, "default": None},
        {"name": "leasetime", "type": str, "required": True, "default": "12h"},
        {"name": "limit", "type": int, "required": True, "default": 150},
        {"name": "start", "type": int, "required": True, "default": 100},
        {"name": "dhcp_option", "type": list, "required": False, "default": ""}
    ]

    def commands(self, allConfigs):
        commands = list()

        # Look up the interface - may fail.
        interface = self.lookup(allConfigs, "interface", self.interface)

        # Look up dnsmasq settings.  This should not fail because we have
        # defined a default dnsmasq object.
        dnsmasq = self.lookup(allConfigs, "dnsmasq", self.interface,
                              tryDefault=True)

        network = ipaddress.IPv4Network(u"{}/{}".format(
            interface.ipaddr, interface.netmask), strict=False)

        # TODO: Error checking!
        firstAddress = network.network_address + self.start
        lastAddress = firstAddress + self.limit

        leaseFile = "{}/dnsmasq-{}.leases".format(
            self.manager.writeDir, self.interface)
        pidFile = "{}/dnsmasq-{}.pid".format(
            self.manager.writeDir, self.interface)
        outputPath = "{}/dnsmasq-{}.conf".format(
            self.manager.writeDir, self.interface)

        with open(outputPath, "w") as outputFile:
            outputFile.write("#" * 80 + "\n")
            outputFile.write("# dnsmasq configuration file generated by pdconfd\n")
            outputFile.write("# Source: {}\n".format(self.source))
            outputFile.write("# Section: config {} {}\n".format(
                ConfigDhcp.typename, self.name))
            outputFile.write("#" * 80 + "\n")
            outputFile.write("interface={}\n".format(interface.ifname))
            outputFile.write("dhcp-range={},{},{}\n".format(
                str(firstAddress), str(lastAddress), self.leasetime))
            outputFile.write("dhcp-leasefile={}\n".format(leaseFile))

            # Write options sections to the config file.
            if self.dhcp_option:
                for option in self.dhcp_option:
                    outputFile.write("dhcp-option={}\n".format(option))

            if dnsmasq.noresolv:
                outputFile.write("no-resolv\n")

            if dnsmasq.server:
                for server in dnsmasq.server:
                    outputFile.write("server={}\n".format(server))

            # TODO: Bind interfaces allows us to have multiple instances of
            # dnsmasq running, but it would probably be better to have one
            # running and reconfigure it when we want to add or remove
            # interfaces.  It is not very disruptive to reconfigure and restart
            # dnsmasq.
            outputFile.write("except-interface=lo\n")
            outputFile.write("bind-interfaces\n")

        cmd = ["/apps/bin/dnsmasq", "--conf-file={}".format(outputPath),
               "--pid-file={}".format(pidFile)]
        commands.append((Command.PRIO_START_DAEMON, cmd))

        self.pidFile = pidFile
        return commands

    def undoCommands(self, allConfigs):
        commands = list()
        try:
            with open(self.pidFile, "r") as inputFile:
                pid = inputFile.read().strip()
            cmd = ["kill", pid]
            commands.append((Command.PRIO_START_DAEMON, cmd))
        except:
            # No pid file --- maybe dnsmasq was not running?
            out.warn("File not found: {}\n".format(
                self.pidFile))
            return []

        return commands


class ConfigDnsmasq(ConfigObject):
    typename = "dnsmasq"

    options = [
        {"name": "interface", "type": list, "required": False, "default": None},
        {"name": "noresolv", "type": bool, "required": False, "default": False},
        {"name": "server", "type": list, "required": False, "default": None}
    ]


# Lookups will return this default object if no named object is found.
ConfigDnsmasq.default = ConfigDnsmasq()
