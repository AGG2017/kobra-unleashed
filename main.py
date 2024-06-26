import datetime
import hashlib
import os
import random
import ssl
import string
import uuid
from pathlib import Path
from typing import Dict, Union, List
import json

import eventlet

import json
from flask import Flask, render_template, send_from_directory, request
import paho.mqtt.client as mqtt
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

eventlet.monkey_patch(all=False, socket=True)

app = Flask(__name__)

# Use external http server URL, default here will be used only if ROOT_URL is missing
ROOT_URL = os.getenv("ROOT_URL", "http://192.168.1.234:5000")
# Random secret key
app.config['SECRET'] = ''.join(random.choice(string.ascii_letters) for i in range(32))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = os.getenv("MQTT_HOST")
app.config['MQTT_BROKER_PORT'] = int(os.getenv("MQTT_PORT", 8883))
app.config['MQTT_CLIENT_ID'] = f'kobra-unleashed-{random.randint(0, 1000)}'
app.config['MQTT_REFRESH_TIME'] = 0.5  # refresh time in seconds
app.config['MQTT_TLS_ENABLED'] = True  # set TLS to enabled for MQTT
app.config['MQTT_TLS_VERSION'] = ssl.PROTOCOL_TLSv1_2
app.config['MQTT_TLS_CA_CERTS'] = os.getenv("MQTT_CA", "/app/certs/ca.pem")
app.config['MQTT_TLS_CERTFILE'] = os.getenv("MQTT_CERT", "/app/certs/client.pem")
app.config['MQTT_TLS_KEYFILE'] = os.getenv("MQTT_KEY", "/app/certs/client.key")
app.config['MQTT_TLS_INSECURE'] = True


received_messages = []
printer_list: Dict[str, "Printer"] = {}

socketio = SocketIO(app, logger=True, engineio_logger=True,
                    cors_allowed_origins="*")
client = mqtt.Client()


class PrintJob:
    taskid: str
    filename: str
    filepath: str
    state: str
    remaining_time: int
    progress: int
    print_time: int
    supplies_usage: int
    total_layers: int
    curr_layer: int
    fan_speed: int
    z_offset: float
    print_speed_mode: int

    def __init__(self, taskid: str, filename: str, filepath: str):
        self.taskid = taskid
        self.filename = filename
        self.filepath = filepath
        self.state = "unknown"
        self.remaining_time = -1
        self.progress = -1
        self.print_time = -1
        self.supplies_usage = -1
        self.total_layers = -1
        self.curr_layer = -1
        self.fan_speed = -1
        self.z_offset = 0.0
        self.print_speed_mode = -1


class FileElement:
    filename: str
    size: int
    timestamp: int
    is_dir: bool
    is_local: bool


class Printer:
    id: str
    name: str
    model_id: str
    fwver: int
    online: bool
    state: str
    nozzle_temp: str
    target_nozzle_temp: str
    hotbed_temp: str
    target_hotbed_temp: str
    print_job: Union[PrintJob, None]
    files: List[List[FileElement]]

    def __init__(self, id: str):
        self.id = id
        self.name = ""
        self.model_id = "20021"
        self.fwver = 0
        self.online = False
        self.state = "offline"
        self.nozzle_temp = "---"
        self.target_nozzle_temp = "---"
        self.hotbed_temp = "---"
        self.target_hotbed_temp = "---"
        self.print_job = None
        self.files = [[], []]

    def get_command_topic(self, cmd_type: str, action: str) -> str:
        if self.fwver >= 310:
            topic = f"anycubic/anycubicCloud/v1/server/printer/{self.model_id}/{self.id}/{cmd_type}"
        else:
            topic = f"anycubic/anycubicCloud/v1/server/printer/{self.model_id}/{self.id}/{cmd_type}/{action}"
        return topic

    def send_command(self, cmd_type: str, action: str, payload: dict):
        payload["msgid"] = str(uuid.uuid4())
        payload["timestamp"] = int(datetime.datetime.now().timestamp() * 1000)
        payload["type"] = cmd_type
        payload["action"] = action
        client.publish(self.get_command_topic(cmd_type, action),
                       json.dumps(payload).replace('/', r'\/').encode("utf-8"))

    def get_files(self, local: bool = True):
        action = "listLocal" if local else "listUdisk"
        self.send_command(
            "file",
            action,
            {
                "data": {
                    "task_mode": 2
                },
                "path": "/"
            })

    def print(self, filename: str, file_path: str = f"/"):
        self.send_command(
            "print",
            "start",
            {
                "data": {
                    "filename": filename,
                    "filepath": file_path,
                    "taskid": str(random.randint(0, 1000000)),
                    "task_mode": 1,
                    "filetype": 1,
                },
            })

    def print_remote_file(self, path: Path, url: str, file_name: str):
        # Prints a file that is uploaded to the server and needs to be printed from there

        # Calculate md5 hash of file
        md5_lib = hashlib.md5()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_lib.update(byte_block)
        file_md5 = md5_lib.hexdigest()
        file_size = os.path.getsize(path)
        task_id = str(random.randint(0, 1000000))
        self.send_command(
            "print",
            "start",
            {
                "data": {
                    "md5": file_md5,
                    "url": url,
                    "filesize": file_size,
                    "filename": file_name,
                    "filetype": 0,
                    "taskid": task_id,
                    "task_mode": 1
                },
            }
        )
        self.print_job = PrintJob(
            task_id,
            file_name,
            url
        )

    def set_fan(self, speed: int):
        self.send_command(
            "set",
            "update",
            {
                "data": {
                    "fan_speed_pct": speed,
                    "settings": {
                        "fan_speed_pct": speed
                    }
                },
            })

    def serialized(self):
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "online": self.online,
            "nozzle_temp": self.nozzle_temp,
            "target_nozzle_temp": self.target_nozzle_temp,
            "hotbed_temp": self.hotbed_temp,
            "target_hotbed_temp": self.target_hotbed_temp,
            "print_job": self.print_job.__dict__ if self.print_job is not None else None,
            "files": self.files
        }


def status_message(printer: Printer, state):
    # Update printer status
    printer.state = state
    if state == "offline":
        printer.nozzle_temp = "---"
        printer.target_nozzle_temp = "---"
        printer.hotbed_temp = "---"
        printer.target_hotbed_temp = "---"
        printer.files = [[], []]


def temperature_message(printer: Printer, payload):
    # Update printer temperature
    printer.nozzle_temp = str(payload["data"]["curr_nozzle_temp"])
    printer.target_nozzle_temp = str(payload["data"]["target_nozzle_temp"])
    printer.hotbed_temp = str(payload["data"]["curr_hotbed_temp"])
    printer.target_hotbed_temp = str(payload["data"]["target_hotbed_temp"])
    print(f"+++ Printer {printer.id} temperature: {printer.nozzle_temp}/{printer.target_nozzle_temp}°C Nozzle, "
          f"{printer.hotbed_temp}/{printer.target_hotbed_temp}°C Hotbed")


def file_message(printer: Printer, payload):
    action = payload["action"]
    if action in ["listLocal", "listUdisk"]:
        is_local = True if action == "listLocal" else False
        records = payload["data"]["records"]
        printer.files[int(is_local)] = records
        socketio.emit("files_updated", {"id": printer.id, "printer": printer.serialized()})
    else:
        print(f"+++ Other file action: {action}")


def print_message(printer: Printer, payload):
    if printer is None:
        return
    print(f"+++ Printer {printer.id} printreport: {payload}")
    action = payload["action"]
    status_message(printer, payload["state"])
    if (action == "start" or action == "stop") and printer.state not in ["failed", "downloading", "checking"]:
        printer.print_job = PrintJob(
            payload["data"]["taskid"],
            payload["data"]["filename"],
            "",
        )
        printer.print_job.progress = payload["data"]["progress"]
        printer.print_job.remaining_time = payload["data"]["remain_time"]
        printer.print_job.print_time = payload["data"]["print_time"]
        printer.print_job.supplies_usage = payload["data"]["supplies_usage"]
        printer.print_job.total_layers = payload["data"]["total_layers"]
        printer.print_job.curr_layer = payload["data"]["curr_layer"]
    elif action == "update":
        printer.nozzle_temp = str(payload["data"]["curr_nozzle_temp"])
        printer.target_nozzle_temp = str(payload["data"]["settings"]["target_nozzle_temp"])
        printer.hotbed_temp = str(payload["data"]["curr_hotbed_temp"])
        printer.target_hotbed_temp = str(payload["data"]["settings"]["target_hotbed_temp"])
        printer.print_job.fan_speed = payload["data"]["settings"]["fan_speed_pct"]
        printer.print_job.z_offset = payload["data"]["settings"]["z_comp"]
        printer.print_job.print_speed_mode = payload["data"]["settings"]["print_speed_mode"]
    elif action == "done":
        printer.print_job.state = "done"
    else:
        print(f"+++ Other print action: {action} / State: {printer.state}")
    return

def ota_message(printer: Printer, payload):
    print(f"OTA {printer.id} printreport: {payload}")
    action = payload["action"]
    if action == "reportVersion":
        version = str(payload["data"]["firmware_version"]).replace('.','')
        try:
            printer.fwver = int(version)
        except:
            print("Invalid Firmware Version")
        print(f"+++ Firmware Version: {printer.fwver}")

def lastwill_message(printer: Printer, payload):
    print(f"LastWill {printer.id} printreport: {payload}")
    action = payload["action"]
    if action == "onlineReport":
        state = payload["state"]
        if state=="online":
            printer.online = True
        else:
            status_message(printer, "offline")
            printer.online = False
        print(f"+++ Printer state: {state}")

def parse_message(mqtt_client, userdata, message):
    # process all incoming messages for the topic 'anycubic/#'
    topic = message.topic
    payload = message.payload.decode()
    try:
        payload = json.loads(payload)
    except json.JSONDecodeError:
        print("Invalid JSON")
        return
    # Example topic: anycubic/anycubicCloud/v1/printer/public/20021/9347a110c5423fe412ce45533bfc10e6/tempature/report
    topic_list = topic.split("/")
    # Get model id from topic
    model_id = topic_list[5]
    # Get printer id from topic
    printer_id = topic_list[6]
    # Example message:
    '''
    {
      "type": "tempature",
      "action": "auto",
      "msgid": "c548672e-7b80-4759-ad1b-96078491fcfb",
      "state": "done",
      "timestamp": 1705245340137,
      "code": 200,
      "msg": "",
      "data": {
        "curr_hotbed_temp": 20,
        "curr_nozzle_temp": 20,
        "target_hotbed_temp": 0,
        "target_nozzle_temp": 0
      }
    }
    '''
    type = topic_list[7]
    action = topic_list[-1]    	
    # Check if printer already exists, if not create it
    this_printer: Printer = printer_list.get(printer_id, None)
    printer_updated = False
    if this_printer is None:
        this_printer = Printer(printer_id)
        this_printer.state = "free"
        this_printer.online = True
        this_printer.model_id = model_id
        printer_list[printer_id] = this_printer
        printer_updated = True
    # Parse message
    if action == "report":
        printer_updated = True
        if type == "status":
            status_message(this_printer, payload["state"])
        elif type == "tempature":  # tempature is not a typo, it's how the API spells it
            temperature_message(this_printer, payload)
        elif type == "file":
            file_message(this_printer, payload)
        elif type == "print":
            print_message(this_printer, payload)
        elif type == "ota":
            ota_message(this_printer, payload)
        elif type == "lastWill":
            lastwill_message(this_printer, payload)
        else:
            print(f"Unknown message type: {type}/{action}")
    else:
        print(f"Unknown message action: {type}/{action}; payload: {payload}")
    if printer_updated:
        print(f"Printer {printer_id} updated to {this_printer.serialized()}")
        socketio.emit("printer_updated", {"id": printer_id, "printer": this_printer.serialized()})
    print(f"+++ Received message: {type}/{action}")


@app.route('/')
def index():
    # Return vue app
    return send_from_directory('kobra-client/dist', "index.html")


@app.route('/assets/<path:path>')
def assets(path):
    return send_from_directory('kobra-client/dist/assets', path)


# @app.route('/api/printer')
@socketio.on('get_printer_list')
def list_printer():
    printer_dict: Dict[str, dict] = {}
    for printer in printer_list.values():
        printer_dict[printer.id] = printer.serialized()
    print(f"Printer list: {printer_dict}")
    emit('printer_list', printer_dict)


@app.route('/api/printer/<printer_id>/files')
def get_printer_files(printer_id: str, local: bool = True):
    printer: Printer = printer_list.get(printer_id, None)
    if printer is None:
        return []
    if not printer.online:
        return []
    printer.get_files(local)
    return printer.files[int(local)]


# @app.route('/api/printer/<printer_id>/print/local/<file_index>')
@socketio.on('print_file')
def print_file(data):
    printer_id = data["printerId"]
    filename = data["file"]
    printer: Printer = printer_list.get(printer_id, None)
    if printer is None:
        return []
    if not printer.online:
        return []
    if printer.state != 'free':
        return []
    printer.print(filename)


# @app.route('/api/printer/<printer_id>/print')
def get_print_job(printer_id: str):
    printer: Printer = printer_list.get(printer_id, None)
    if printer is None:
        return []
    return printer.print_job.__dict__ if printer.print_job is not None else None


def send_print_action(printer: Printer, action: str):
    printer.send_command("print", action, {"data": {"taskid": printer.print_job.taskid}})


@socketio.on('stop_print')
def stop_print(printer_id: Dict[str, str]):
    printer: Printer = printer_list.get(printer_id.get("id"), None)
    print(f"Stopping print on printer {printer_id.get('id')}")
    if printer is None:
        return []
    send_print_action(printer, "stop")


@socketio.on('pause_print')
def pause_print(printer_id: Dict[str, str]):
    printer: Printer = printer_list.get(printer_id.get("id"), None)
    print(f"Stopping print on printer {printer_id.get('id')}")
    if printer is None:
        return []
    send_print_action(printer, "pause")


@socketio.on('resume_print')
def resume_print(printer_id: Dict[str, str]):
    printer: Printer = printer_list.get(printer_id.get("id"), None)
    print(f"Stopping print on printer {printer_id.get('id')}")
    if printer is None:
        return []
    send_print_action(printer, "resume")


@socketio.on('set_fan')
def set_fan(data):
    printer_id = data["id"]
    speed = data["speed"]
    printer: Printer = printer_list.get(printer_id, None)
    if printer is None:
        return []
    print(f"Setting fan speed on printer {printer_id} to {speed}")
    printer.set_fan(speed)


@app.route('/api/print', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    printer_id = request.form['printer_id']
    if file.filename == '':
        return 'No selected file', 400
    if Path(file.filename).suffix != ".gcode":
        return 'Invalid file type; Currently Only gcode allowed', 400
    printer: Printer = printer_list.get(printer_id, None)
    if printer is None:
        return 'Printer not found', 400
    if not printer.online:
        return 'Printer is offline', 400
    if printer.state != 'free':
        return 'Printer is busy', 400
    if file:
        filename = secure_filename(file.filename)
        upload_file_name = str(uuid.uuid4()) + filename
        file_path = Path(app.config['UPLOAD_FOLDER']) / upload_file_name
        file.save(file_path)
        url_file = ROOT_URL + "/uploads/" + upload_file_name
        printer.print_remote_file(file_path, url_file, filename)
        return f'File uploaded successfully for printer {printer_id}', 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


def configure_mqtt(mqtt_client, userdata, flags, rc):
    # subscribe to receive all anycubic messages
    mqtt_client.subscribe("anycubic/#")
    print(f"##### Connected to MQTT Server {app.config['MQTT_BROKER_URL']}:{app.config['MQTT_BROKER_PORT']}")


def initialize_mqtt():
    client.reinitialise(app.config['MQTT_CLIENT_ID'], clean_session=True)
    client.on_connect = configure_mqtt
    client.on_message = parse_message
    client.tls_set(
        ca_certs=app.config['MQTT_TLS_CA_CERTS'],
        certfile=app.config['MQTT_TLS_CERTFILE'],
        keyfile=app.config['MQTT_TLS_KEYFILE'],
        tls_version=app.config['MQTT_TLS_VERSION'],
        ciphers=None
    )
    client.tls_insecure_set(app.config['MQTT_TLS_INSECURE'])
    client.connect(app.config['MQTT_BROKER_URL'], app.config['MQTT_BROKER_PORT'], keepalive=60)

    print("Starting MQTT Client")
    client.loop_start()


def initialize_socketio_server():
    print("Starting Flask SocketIO")
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, debug=True)


if __name__ == '__main__':
    initialize_mqtt()
    initialize_socketio_server()
else:
    initialize_mqtt()
