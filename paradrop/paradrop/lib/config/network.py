import ipaddress
import itertools

from paradrop.lib import settings
from paradrop.lib.config import configservice, uciutils
from paradrop.lib.config.pool import NetworkPool
from paradrop.lib.utils import addresses, uci
from pdtools.lib.output import out
from pdtools.lib import pdutils

MAX_INTERFACE_NAME_LEN = 15


# Pool of addresses available for chutes that request dynamic addressing.
networkPool = NetworkPool(settings.DYNAMIC_NETWORK_POOL)


def getNetworkConfig(update):
    """
    For the Chute provided, return the dict object of a 100% filled out
    configuration set of network configuration. This would include determining
    what the IP addresses, interfaces names, etc...
    """

    # Notes:
    #
    # Fill in the gaps of knowledge between what the dev provided us in their
    # config and what would be required to add all the config changes to get
    # the chute working By the end of this function there should be a
    # cache:networkInterfaces key containing a list of dictionary objects for
    # each interface we will need to create, including netmasks IP addresses,
    # etc.. this is important to allow all other modules to know what the IP
    # addr is for this chute, etc..
    #
    # old code under lib.internal.chs.chutelxc same function name

    interfaces = list()

    if(not hasattr(update, 'net')):
        return None

    devices = update.new.getCache('networkDevices')
    wifiIter = itertools.cycle(devices['wifi'])

    for name, cfg in update.net.iteritems():
        # First we must check the length of the name string, it cannot be
        # longer then 16-6 This is because the veth pair name for lxc cannot be
        # longer then 16, and we prepend "vc####" to that interface name
        if(len(name) > 10):
            out.warn('The network interface name ({}) cannot be longer than '
                     '10 characters.\n'.format(name))
            raise Exception("Interface name too long")

        # Check for required fields.
        res = pdutils.check(cfg, dict, ['intfName', 'type'])
        if(res):
            out.warn('Network interface definition {}\n'.format(res))
            raise Exception("Interface definition missing field(s)")

        # Claim a subnet for this interface from the pool.
        subnet = networkPool.next()
        hosts = subnet.hosts()

        # Generate internal (in the chute) and external (in the host)
        # addresses.
        #
        # Example:
        # subnet: 192.168.30.0/24
        # netmask: 255.255.255.0
        # external: 192.168.30.1
        # internal: 192.168.30.2
        netmask = str(subnet.netmask)
        externalIpaddr = str(hosts.next())
        internalIpaddr = str(hosts.next())

        # Generate a name for the new interface in the host by combining the
        # chute name and the interface name.  Note it does not really matter
        # what this name is, since the developer will not see it.  We should
        # check to make sure it is unique, though.
        prefixLen = MAX_INTERFACE_NAME_LEN - len(cfg['intfName']) - 1
        externalIntf = "{}.{}".format(update.new.name[0:prefixLen], cfg['intfName'])

        # Generate the internal IP address with prefix length (x.x.x.x/y) for
        # convenience of other code that expect that format (e.g. pipework).
        ipaddrWithPrefix = "{}/{}".format(internalIpaddr, subnet.prefixlen)

        iface = {
            'name': name,                           # Name (not used?)
            'netType': cfg['type'],                 # Type (wan, lan, wifi)
            'externalIntf': externalIntf,           # Interface name in host
            'internalIntf': cfg['intfName'],        # Interface name in chute
            'netmask': netmask,                     # Netmask in host and chute
            'externalIpaddr': externalIpaddr,       # IP address in host
            'internalIpaddr': internalIpaddr,       # IP address in chute
            'ipaddrWithPrefix': ipaddrWithPrefix    # Internal IP (x.x.x.x/y)
        }

        # Add extra fields for WiFi devices.
        if cfg['type'] == "wifi":
            # Pick a WiFi device for this interface.  Then a virtual interface
            # will be made from it.
            try:
                device = wifiIter.next()
                iface['device'] = device['name']
            except StopIteration:
                out.warn("Request for WiFi device cannot be fulfilled")
                raise Exception("Missing WiFi device(s) requested by chute")

            # Check for required fields.
            res = pdutils.check(cfg, dict, ['ssid'])
            if(res):
                out.warn('WiFi network interface definition {}\n'.format(res))
                raise Exception("Interface definition missing field(s)")

            iface['ssid'] = cfg['ssid']

            # Option encryption settings
            if 'encryption' in cfg:
                iface['encryption'] = cfg['encryption']
            if 'key' in cfg:
                iface['key'] = cfg['key']

        # Pass on DHCP configuration if it exists.
        if 'dhcp' in cfg:
            iface['dhcp'] = cfg['dhcp']

        interfaces.append(iface)

    update.new.setCache('networkInterfaces', interfaces)


def getOSNetworkConfig(update):
    """
    Takes the network interface obj created by NetworkManager.getNetworkConfiguration
    and returns a properly formatted object to be passed to the OpenWrtConfig class.
    The object returned is a list of tuples (config, options).
    """
    # Notes:
    #
    # Take the cache:networkInterfaces key and generate the UCI specific OS config we need
    # to inact the chute changes, should create a cache:osNetworkConfig key
    #
    # old code under lib.internal.chs.chutelxc same function name

    interfaces = update.new.getCache('networkInterfaces')

    osNetwork = list()

    if(interfaces is None):
        return None

    for iface in interfaces:
        # A basic set of things must exist for all interfaces
        config = {'type': 'interface', 'name': iface['externalIntf']}

        # LXC network interfaces are always bridges
        options = {
            'type': "bridge",
            'proto': 'static',
            'ipaddr': iface['externalIpaddr'],
            'netmask': iface['netmask'],
            'ifname': iface['externalIntf']
        }

        # Add to our OS Network
        osNetwork.append((config, options))

    update.new.setCache('osNetworkConfig', osNetwork)


def setOSNetworkConfig(update):
    """
    Takes a list of tuples (config, opts) and saves it to the network config file.
    """

    # Notes:
    #
    # Takes the config generated (cache:osNetworkConfig) and uses the UCI module to actually push
    # it to the disk
    #
    # old code under lib.internal.chs.chutelxc same function name

    changed = uciutils.setConfig(update.new, update.old,
                                 cacheKeys=['osNetworkConfig'], filepath=uci.getSystemPath("network"))

    # If we didn't change anything, then return the function to reloadNetwork so we can save ourselves from that call
    if(not changed):
        return configservice.reloadNetwork


def getVirtNetworkConfig(update):
    out.warn('TODO implement me\n')
    # old code under lib.internal.chs.chutelxc same function name
    # Takes any network specific config and sets up the cache:virtNetworkConfig
    # this would be the place to put anything into HostConfig or the dockerfile we need
