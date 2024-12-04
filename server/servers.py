import threading, logging
from time import sleep, strftime
import socket
from db_access import DatabaseConnection

from main_server_refactored import MainServer
from content_server_refactored import ContentServer

logfile = open(f"server/logs/{strftime('%Y%m%d-%H%M%S')}.txt", "w")

logging.basicConfig(level=logging.DEBUG, stream=logfile)

ip = socket.gethostbyname(socket.gethostname())

class ArcticServer:
    def __init__(self):
        self.db = DatabaseConnection()
        self.main_server = MainServer(ip, 6081, logfile, self.db)
        self.content_server = ContentServer(ip, 6071, ip, 6081, logfile, self.db)
        self.logger = logging.getLogger("ArcticServer")
        self.logger.info("Starting Arctic Server...")
        self.main_server_thread = threading.Thread(target=self.main_server.start)
        self.content_server_thread = threading.Thread(target=self.content_server.start)
    
    def start(self):
        self.main_server_thread.start()
        sleep(1)  # wait for server to start up before starting content server thread
        self.content_server_thread.start()
        self.logger.info("Servers started!")

if __name__ == "__main__":
    server = ArcticServer()
    server.start()