"""Constants for the OpenWrt (ubus) integration."""

DOMAIN = "ubus"

CONF_DHCP_SOFTWARE = "dhcp_software"
DEFAULT_DHCP_SOFTWARE = "dnsmasq"
DHCP_SOFTWARES = ["dnsmasq", "odhcpd", "none"]

# Default ASU (Attended Sysupgrade) server, matching the router's
# `attendedsysupgrade` UCI default when no custom server is configured.
DEFAULT_ASU_SERVER = "https://sysupgrade.openwrt.org"
# LuCI page used to inspect and install a firmware update manually.
ASU_LUCI_PATH = "/cgi-luci/admin/system/attendedsysupgrade"
