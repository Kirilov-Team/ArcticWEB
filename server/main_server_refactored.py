import socket
import threading
import os
import logging
from sys import stdout
from db_access import DatabaseConnection


class MainServer:
    def __init__(self, host, port, logfile, database: DatabaseConnection):
        self.host = host
        self.port = port
        self.database = database
        logging.basicConfig(stream=logfile, encoding='utf-8', level=logging.DEBUG)
        self.logger = logging.getLogger("MainServer")
        #self.logger.info("""
            #__  _____  ___    __    _
            #( (`  | |  | |_)  / /\  \ \_/
            #_)_)  |_|  |_| \ /_/--\  |_|  """)

        self.logger.info(f"Starting main server on {host}:{port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(None)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(10)
        self.logger.info("Waiting for connections!")
        self.logger.warning("Maximum 10 concurrent users allowed!")
        while True:
            client_socket, client_address = self.socket.accept()
            self.logger.info(f"Connection from {client_address[0]} established!")
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()
        
    def handle_client(self, client_socket: socket.socket, client_address:socket.AddressInfo):
        is_server = client_socket.recv(1).decode() == "1"
        if is_server:
            servername = client_socket.recv(1024).decode().strip()
            self.logger.info(f"Got server connection from {servername}!")
            saved_servers = self.database.query("SELECT servername,server_ip FROM connected_servers")
            servernames = [server[0] for server in saved_servers]
            if servername not in servernames:
                self.database.query(f"INSERT INTO connected_servers (servername, server_ip) VALUES ('{servername}', '{client_address[0]}')")
        else:
            # send back list of available servers
            servers = self.database.query("SELECT servername FROM connected_servers")
            servernames = [server[0] for server in servers]
            serverlist_message = "\n".join(servernames)
            client_socket.send(serverlist_message.encode())
            # receive server selection
            selected_server = client_socket.recv(1024).decode()
            # connect to selected server
            ip = self.database.query(f"SELECT server_ip FROM connected_servers WHERE servername='{selected_server}'")[0]
            client_socket.send(ip.encode())
            # My work here is done
            client_socket.close()

if __name__ == "__main__":
    main_server = MainServer("127.0.0.1", 6081)
    main_server.start()
