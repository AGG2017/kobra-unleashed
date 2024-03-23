# How to set a Raspberry Pi with a static IP address

A static IP address, as opposed to a dynamic IP address, doesn’t change. The single-board computer Raspberry Pi always needs a static IP address if you want to access it with other devices over a long period of time. This refers to the private IP address of the Raspberry IP that is located by a computer within the local network as well as the public IP address of the network via which the Raspberry Pi is accessible on the internet (for example, if it’s being used as a server). But how do you provide Raspberry Pi with an IP address that always remains the same? This guide explains two of the options you have for linking a static IP address to your Raspberry Pi.

## Assign a static IP address to Raspberry Pi with a router

This is the easiest way to assign a static IP address to RPI but it is not universal and strongly depends on the brand and the model router you are using.

Many routers support the ability to provide individual devices within the local network with a static IP address. With a Linksys router, the Linksys app allows you to manage multiple devices and handle all of the router assignments remotely. Various other routers also support similar functions, and so can be used for linking Raspberry Pi with a static IP address.

A static IP address for Raspberry Pi is set up somewhat differently for each router. The basic principle is always the same, though: You open the user interface of the router in your browser; Link the MAC address of Raspberry Pi with your LAN’s IPv4 address via the manual IP configuration. Most of the time, a checkbox exists for this in the router interface. This enables you to always automatically use the IP address assigned to you.

## Assign a static IP address to Raspberry Pi with DHCPCD

Raspbian OS have a DHCP client daemon (DHCPCD) that can communicate with the DHCP servers from routers. The configuration file of a DHCP client daemon allows you to change the IP address of a computer and set it up in the long term. The following instructions will assign a static IPv4 address to the Raspberry Pi.

Before you begin with the assignment of a private IP address for Raspberry Pi, check whether DHCPCD is already activated using the following command:

```
sudo service dhcpcd status
```

In case it’s not, activate DHCPCD as follows:

```
sudo service dhcpcd start
sudo systemctl enable dhcpcd
```

For the editing of the activated DHCPCDs, start by opening the configuration file /etc/dhcpcd.conf and running the following command:

```
sudo nano /etc/dhcpcd.conf
```

You’ll now carry out the configuration of the static IP address. If your Raspberry Pi is connected to the internet via an Ethernet or network cable, then enter the command ‘interface eth0’; if it takes place over Wi-Fi, then use the ‘interface wlan0’ command.

To assign an IP address to Raspberry Pi, use the command ‘static ip_address=’ followed by the desired IPv4 address and the suffix ‘/24’ (an abbreviation of the subnet mak 255.255.255.0). For example, if you want to link a computer with the IPv4 address 192.168.1.253, then you need to use the command ‘static ip_address=192.168.1.253/24’. It goes without saying that the address used here is not yet used anywhere else. As such, it also can’t be located in the address pool of a DHCP server.

You still then need to specify the address of your gateway and domain name server (usually both are the router). Raspberry Pi turns to the gateway address if an IP address to which it wants to send something is outside of the subnet mask (in the example, this would mean outside of the range 192.168.1). In the following command, the IPv4 address 192.168.1.1 is used as an example as both the gateway and DNS server. The complete command looks like this in our example (where a network cable is used for the internet connection):

```
interface eth0
static ip_address=192.168.1.253/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

In case of wireless connection the upper configuration must be replaced by:

```
interface wlan0
static ip_address=192.168.1.253/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

The command lines above match the IPv4 addresses that you want to use for your Raspberry Pi, or where your router is assigned. Save the changes with ‘Ctrl + S’ and then press the enter key. Close the configuration file with ‘Ctrl + X’. Restart to adopt the newly assigned static IP address in the network:

```
sudo reboot now
```

Now you should be able to access your Raspberry Pi by using the selected static IP address.
