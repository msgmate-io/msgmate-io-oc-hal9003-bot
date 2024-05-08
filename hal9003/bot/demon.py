# will create a simple system.d service so the bot can be re-started
# this is especially usefull for local bot e.g.: hosting a gpu in your house, 
# then the bot can reconnect to a open-chat server and process queryies using the gpu
import os
import base64
from bot import config as bc
import time
import glob

SERVICE = """
[Unit]
Description=Hal9003 Service
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/home/{username}/.hal9003/bot
WorkingDirectory=/home/{username}/.hal9003

[Install]
WantedBy=multi-user.target
"""

def demonize_self_linux():
    pwd = os.getcwd() + "/bot"
    print("Current working directory:", pwd)
    # 0 - get the username
    username = os.environ.get("USER", "hal9003")

    users = glob.glob("/home/*")
    first_user = users[0].split("/")[-1]
    username = first_user

    destination = f"/home/{username}/.hal9003"
    if os.path.exists(f"{destination}/.setup_complete_{bc.DEMON_VERSION}"):
        return True
    
    # 0.5 - check that pwd isn't already in the right place
    if pwd.startswith(destination):
        print("Demon already set up")
        return True

    # 1 - create the directory and move self to it
    os.makedirs(f"/home/{username}/.hal9003", exist_ok=True)
    
    # 2 - move the bot to the right place
    os.system(f"mv {pwd} {destination}/bot")
    
    # 2.5 with **sudo** check if the service exists

    exists = os.system(f"sudo vim /etc/systemd/system/hal9003.service")
    # /etc/systemd/system/hal9003.service
    
    if exists == 0:
        print("Service already exists, overwriting...")
    # 3 - request sudo to create the service
    base_64_service = base64.b64encode(SERVICE.format(username=username).encode()).decode()
    os.system(f"sudo touch /etc/systemd/system/hal9003.service")
    os.system(f"echo {base_64_service} | base64 -d | sudo tee /etc/systemd/system/hal9003.service")
    
    # 4 - start the service
    os.system("sudo systemctl enable hal9003")
    os.system("sudo systemctl reload hal9003")
    os.system("sudo systemctl daemon-reload")
    os.system("sudo systemctl start hal9003")
    os.system(f"touch {destination}/.setup_complete_{bc.DEMON_VERSION}")
    time.sleep(5)
    os.system("sudo systemctl status hal9003")
    