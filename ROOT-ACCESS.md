# Root Access for Anycubic Kobra 2 Series 3D Printers

The easiest way to create root access to these printers is to use the serial console. The signals needed to connect to the serial console are available on the 4 pin header on the mainboard.

![](https://raw.githubusercontent.com/AGG2017/kobra-unleashed/master/img/mainboard_uart.jpg)

Connect the 3 signals RX, TX and GND to the signals TX, RX and GND of one 3/5V USB to serial adapter as shown on the following wiring diagram:

![](https://raw.githubusercontent.com/AGG2017/kobra-unleashed/master/img/usb2serial.png)

Use Putty or other serial communication terminal software to connect to your USB to serial adapter by using the following setup:

![](https://raw.githubusercontent.com/AGG2017/kobra-unleashed/master/img/putty.png)

When you start your terminal software and turn on you printer, if you cannot see anything on the serial console it's probably because you run newer firmware. You need to downgrade to firmware version 2.3.9 first before you can continue. This is due to disabling the serial console in the newer firmware versions.

Once basic serial communication is established:

1. Hold down the `s` key while powering on the printer.

2. When the booting process stop and you have access to the console, enter these commands:

```sh
setenv init /bin/sh
saveenv
bootd
```

Now you have a root shell from the serial console.

3. Now you need to override the root password. To do this, you need to mount the overlay partition:

```sh
mount -t proc p /proc

. /lib/functions/preinit.sh

. /lib/preinit/80_mount_root

do_mount_root

. /etc/init.d/boot

link_by_name

. /lib/preinit/81_initramfs_config

do_initramfs_config
```

4. Then you can override the root password:

```sh
cp /etc/shadow /overlay/upper/etc/shadow
```

5. Set a new user password by:

```sh
passwd root
```

6. Then you need to reboot into U-Boot again:

```sh
reboot
```

7. And change back the boot to normal:

```sh
setenv init /sbin/init
setenv bootdelay 3
saveenv
reset
```

Now you have root access and can login with the password you set.

To install SSH server that permits remote access, you can do the following from the serial console:

```sh
wget http://bin.entware.net/armv7sf-k3.2/installer/generic.sh
chmod 755 generic.sh
./generic.sh
sed -i '$i\/opt/etc/init.d/rc.unslung start' /etc/rc.local
echo 'export PATH="$PATH:/opt/sbin:/opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' >> /etc/profile
reboot

opkg update
opkg install dropbear
reboot
```

Now you have permanent ssh access from the network by:

```sh
ssh root@printer_ip
```

You no longer need of the serial console, USB to serial adapter and the wire connections you made.
