import socket
import threading
import os
import logging
import json
from sys import stdout
from time import sleep



class ContentServer:
    def __init__(self, host, port, main_server_ip, main_server_port, logfile, database):

        self.host = host
        self.port = port
        self.database = database  # Placeholder for database connection
        logging.basicConfig(stream=logfile, encoding='utf-8', level=logging.DEBUG)
        self.logger = logging.getLogger("ContentServer")
        self.logger.info(f"Starting content server on {host}:{port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with open("server/settings.json") as setting:
            self.settings = json.load(setting)
        self.logger.info("Settings loaded successfully!")

        with open("server/whitelist.encrypted") as whl:
            self.whitelist = whl.read().splitlines()
        self.logger.info("Whitelist loaded successfully!")
        with open("server/admins.json") as admin_json:
            self.admins:list[str] = json.load(admin_json)
        self.logger.info("Admins loaded successfully!")
        self.clients = {}
        self.packet_delay = 0.01
        self.main_server_ip = main_server_ip
        self.main_server_port = main_server_port
    
    def start(self):
        if self.settings["connect_to_main_server"] == "True":
            self.main_server_ip = self.main_server_ip
            self.main_server_port = self.main_server_port
            self.main_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.main_server.connect((self.main_server_ip, self.main_server_port))
            self.main_server.settimeout(None)
            self.main_server.send("1".encode("utf-8"))
            self.main_server.send(self.settings["names"]["label"].encode())
            self.logger.info("Connected to main server!")

        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.logger.info("Waiting for connections!")
        self.logger.warning("Maximum 10 concurrent users allowed!")
        while True:
            client_socket, client_address = self.socket.accept()
            self.logger.info(f"Connection from {client_address[0]} established!")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket: socket.socket, client_address: socket.socket):
        # Send config to client
        self.logger.info("Sending settings...")
        client_socket.send((self.settings["rules"]["rules"]+";").encode("utf-8"))

        with open("server/version") as version_file:
            version = version_file.read()
            client_socket.send((version + ";").encode("utf-8"))
            self.logger.info(f"Sent version {version} to {client_address}")

        self.logger.info("Done!")

        self.clients[client_socket] = {
            "nickname": None,
            "admin": False,
            "whitelisted": False,
            "socket": client_socket,
        }

        # Transition to command processing
        command_handlers = {
            "JOIN": self.user_join,
            "RECV": self.serve_site,
            "WRIT": self.create_site,
            "LIST": self.list_sites,
            "EXIT": self.disconnect_user,
            "SUDO": self.attempt_promotion,
            "WHTL": self.attempt_whitelist_addition,
            "UPGD": self.send_upgrade,
            "PROF": self.serve_user_profile,
            "": self.nop
        }

        while True:
            if client_socket not in self.clients.keys():
                # user had disconnected
                return
            sleep(0.01)
            message = client_socket.recv(65535).decode()
            command_handlers.get(message[:4], self.unknown_command)(message, client_socket)
    
    def nop(*a):
        pass
    
    def user_join(self, message: str, client: socket.socket):
        nickname = message[message.index(";")+1:]
        self.clients[client]["nickname"] = nickname
        if nickname in self.admins:
            self.clients[client]["admin"] = True
            client.send(b'YES')
        else:
            client.send(b"NOO")
        sleep(self.packet_delay)
        if nickname in self.whitelist or self.whitelist == ["open"]:
            self.clients[client]["whitelisted"] = True
        else:
            client.send(b"403")
            # Not whitelisted -> disconnect
            self.disconnect_user(message, client)
            return
        self.logger.info(f"{nickname} joined!")
    
    def serve_site(self, message: str, client: socket.socket):
        site_name = message[5:]
        sites = os.listdir("server/sites")
        sites.remove("websites.list") # we don't need to include the list file
        if site_name in sites:
            with open(f"server/sites/{site_name}") as site:
                client.send(site.read().encode())
        else:
            client.send(self.settings["messages"]["not_found"].encode())
        self.logger.info(f"{self.clients[client]['nickname']} requested {site_name}!")
    
    def create_site(self, message: str, client: socket.socket):
        site_name = message[5:message.index(";", 6)]
        site_file = open(f"server/sites/{site_name}", "w")
        site_file.write(message[message.index(";", 6)+1:]+"\n")
        site_file.write(f"Created by: {self.clients[client]['nickname']}")
        self.logger.info(f"{self.clients[client]['nickname']} created {site_name}!")
        site_file.close()
    
    def list_sites(self, message: str, client: socket.socket):
        sites = os.listdir("server/sites")
        sites.remove("websites.list") # we don't need to include the list file
        client.send(",".join(sites).encode())
    
    def disconnect_user(self, message: str, client: socket.socket):
        self.logger.info(f"{self.clients[client]['nickname']} has left.")
        del self.clients[client]
        client.close()
    
    def attempt_promotion(self, message: str, client: socket.socket):
        username = message[5:]
        if self.clients[client]["admin"]:
            if username in self.admins:
                self.logger.info(f"{username} is already an admin.")
                client.send(self.settings["messages"]["failed_to_add_someone_to_admins"].encode())
            else:
                self.admins.append(username)
                self.logger.info(f"{self.clients[client]['nickname']} promoted {username} to admin.")
                client.send(self.settings["messages"]["added_someone_to_admins"].replace("{user}", username).encode())
                with open("server/admins.json", "w") as adminfile:
                    json.dump(self.admins, adminfile)
        else:
            client.send(self.settings["messages"]["command_disabled"].encode())
    
    def attempt_whitelist_addition(self, message: str, client: socket.socket):
        username = message[5:]
        if "open" in self.whitelist:
            client.send(self.settings["messages"]["command_disabled"].encode())
            return
        if self.clients[client]["admin"]:
            if username in self.whitelist:
                self.logger.info(f"{username} is already whitelisted.")
                client.send(self.settings["messages"]["failed_to_add_someone_to_whitelist"].encode())
            else:
                self.whitelist.append(username)
                self.logger.info(f"{self.clients[client]['nickname']} whitelisted {username}.")
                client.send(self.settings["messages"]["added_someone_to_whitelist"].replace("{user}", username).encode())
        else:
            client.send(self.settings["messages"]["command_disabled"].encode())
    
    def send_upgrade(self, message: str, client: socket.socket):
        from base64 import b64encode as b64e
        from zipfile import ZipFile
        with ZipFile("clientupdate.zip", "w") as zipf:
            for file in os.listdir("client"):
                zipf.write(f"client/{file}", arcname=file)
        client.send(b64e(open("clientupdate.zip", "rb").read()))
        self.logger.info(f"Sent client update to {self.clients[client]['nickname']}.")
        os.remove("clientupdate.zip")
    
    def unknown_command(self, message: str, client: socket.socket):
        self.logger.info(f"Unknown command in {message}.")
    
    def serve_user_profile(self, message: str, client: socket.socket):
        pass
    
if __name__ == "__main__":
    server = ContentServer("127.0.0.1", 6071)
    server.start()