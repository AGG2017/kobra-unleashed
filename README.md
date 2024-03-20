# Kobra Unleashed

This project is a step by step guide how to setup modified version of the original project Kobra Unleashed on a Raspberry Pi 4 or 5. The same can be used on almost all Debian based Linux host machines. The original project Kobra Unleashed can be found [here](https://github.com/anjomro/kobra-unleashed/)

![](https://raw.githubusercontent.com/AGG2017/kobra-unleashed/master/img/kobra-unleashed-idle.png)

## How does it work?

This web interface uses the interface of the firmware that is designed to be used with the proprietary app of the
manufacturer. This interface is not documented and not officially supported. All controls and information used in the
web interface are the result of reverse engineering. As a result you can remotely upload gcode files, start printing with local or remote files, monitor the printing process, or pause/resume the print, etc.

## Prerequisites

- Root shell access to your Printer as described in this guide... TBD
- Linux server based on Raspberry Pi 4 or 5
  - Reachable by IPv4 from the printer
  - Port 8883 has to be opened for MQTT(S)
  - Another port of your choice (default to 5000) for the Web interface
- Linux host PC for initial setup of the Raspberry Pi (optional if you don't have a monitor and a keyboard attached to the RPI)

## Setup the server

- Prepare one SD card with the Raspbian OS 64Bit Lite as described step by step in [this guide](RASPBIAN-OS.md)
- Install this SD card in the Raspberry Pi, connect the power and LAN cable (optional) and turn on the power.
- Wait until Raspberry Pi boots and from another Linux PC or from your router web interface try to find out what is its IP address.
- One example of this process can be

```
sudo apt install nmap
ip r | grep default
  default via 192.168.1.1 dev enp4s0f0 proto dhcp metric 100
sudo nmap -sP 192.168.1.0/24
  ...
  Nmap scan report for 192.168.1.253
  Host is up (0.012s latency).
  MAC Address: D8:3A:DD:DD:8E:82 (Unknown)
  Nmap scan report for 192.168.1.254
  Host is up (0.012s latency).
  MAC Address: D8:3A:DD:DD:8E:82 (Unknown)
```

For the default via 192.168.1.1 we found by searching 192.168.1.0/24 the RPI IP 192.168.1.253 and 192.168.1.254 (LAN and Wifi IPs)

- It is recommended to setup a static IP address of your RPI by setting its MAC in your router or in the RPI by following this guide... TBD
- Let say we already selected to setup a static address 192.168.1.253 for the rest of the steps
- From your Linux host PC connect by ssh to the Raspberry Pi static IP (we assume the username is rpi5 but if different use your username)

```
ssh rpi5@192.168.1.253
  The authenticity of host '192.168.1.253 (192.168.1.253)' can't be established.
  ED25519 key fingerprint is SHA256:FaKHQuGNwriQU3DsgwrwEyrMmXaL0YI8ZmfzBVJ8yFg.
  This key is not known by any other names
  Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
```

- Install Docker:
  See [the official guide](https://docs.docker.com/engine/install/debian/) for more information.
  For our purpose we just need to execute the following commands:

```
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y
```

- Install Git

```
sudo apt-get install git -y
```

- Clone the repository

```
cd ~
git clone https://github.com/AGG2017/kobra-unleashed.git
cd kobra-unleashed
```

- Generate the custom mqtt keys

```
cd certs
./generate_certs.sh
```

- Check the keys are generated

```
ls
  ca.key
  ca.pem
  client.csr
  client.key
  client.pem
  generate_certs.sh
  verification_cert.csr
  verification_cert.key
  verification_cert.pem
```

- Backup the AC mqtt keys

```
scp root@printer_ip:/user/ca.crt ac_ca.crt
scp root@printer_ip:/user/client.crt ac_client.crt
scp root@printer_ip:/user/client.key ac_client.key
```

- Set the custom mqtt keys

```
scp ca.pem root@printer_ip:/user/ca.crt
scp client.pem root@printer_ip:/user/client.crt
scp client.key root@printer_ip:/user/client.key
```

- Edit the IP address of your Raspberry Pi server inside the file `docker-compose.yml`

```
cd ..
nano docker-compose.yml
```

Replace the line `ROOT_URL=http://rpi5_static_ip:5000` with `ROOT_URL=http://192.168.1.253:5000`, press Ctrl-S to save the file and then Ctrl-X to exit.

- Build the image kobra-unleashed

```
sudo docker build . -t kobra-unleashed
```

- Run the server to see if everything is working

```
sudo docker compose up
```

You should see the log here, and no errors should be found if everything was setup correctly. Example:

```
rpi5@rpi5:~/kobra-unleashed $ sudo docker compose up
[+] Running 2/0
 ✔ Container kobra-unleashed-eclipse-mosquitto-1  Created                                                                                                                                                     0.0s
 ✔ Container kobra-unleashed                      Running                                                                                                                                                     0.0s
Attaching to kobra-unleashed, eclipse-mosquitto-1
kobra-unleashed      | Server initialized for eventlet.
eclipse-mosquitto-1  | 1710946718: mosquitto version 2.0.18 starting
eclipse-mosquitto-1  | 1710946718: Config loaded from /mosquitto/config/mosquitto.conf.
eclipse-mosquitto-1  | 1710946718: Opening ipv4 listen socket on port 8883.
eclipse-mosquitto-1  | 1710946718: Opening ipv6 listen socket on port 8883.
eclipse-mosquitto-1  | 1710946718: Opening websockets listen socket on port 8080.
eclipse-mosquitto-1  | 1710946718: mosquitto version 2.0.18 running
eclipse-mosquitto-1  | 1710946719: New connection from 172.19.0.2:57913 on port 8883.
kobra-unleashed      | Starting MQTT Client
eclipse-mosquitto-1  | 1710946719: New client connected from 172.19.0.2:57913 as kobra-unleashed-34 (p2, c1, k60).
eclipse-mosquitto-1  | 1710946719: No will message specified.
eclipse-mosquitto-1  | 1710946719: Sending CONNACK to kobra-unleashed-34 (0, 0)
kobra-unleashed      | ##### Connected to MQTT Server eclipse-mosquitto:8883
eclipse-mosquitto-1  | 1710946719: Received SUBSCRIBE from kobra-unleashed-34
eclipse-mosquitto-1  | 1710946719: 	anycubic/# (QoS 0)
eclipse-mosquitto-1  | 1710946719: kobra-unleashed-34 0 anycubic/#
```

- Run the server permanently as a daemon. First stop the previous run with Ctrl-C and then:

```
sudo docker compose up -d
```

- If you need to rebuild the image (after updating sources):

```
docker compose down
docker rmi kobra-unleashed
docker build . -t kobra-unleashed
docker compose up -d
```

- Now the server is running and it is waiting a connection from the printer (on port 8883) or from a browser (on port 5000).

## Setup the printer

The easiest way to setup the printer in order to redirect the MQTT URL from AC cloud to your Raspberry Pi URL is by using the tools to generate a custom update. Prepare a custom update with the option `modify_mqtt` enabled. Set the mqtt address as the one of the RPI server static IP. Refer to the information how to prepare a custom update... TBD

It was possible to do it manually by modifying the /app/app executable but from firmware version 3.1.0 we also need to patch the security verification for the source URL and this is no longer easy to be done by editing the app.
