#!/usr/bin/env python

import socket, argparse, opentuner, sys, threading, logging

from status_codes import *
from commands import *

from time import sleep

parser = argparse.ArgumentParser(description = "Process server options.")

parser.add_argument("--port",
                    dest    = "tcp_port",
                    type    = int,
                    default = 8080,
                    help    = "The port to listen to.")
parser.add_argument("--buffer",
                    dest    = "buffer_size",
                    type    = int,
                    default = 8192,
                    help    = "The message buffer size.")
parser.add_argument("--ip",
                    dest    = "tcp_ip",
                    type    = str,
                    default = '',
                    help    = "The IP to listen to.")

buffer = ""

def recv_message(sock, size = 8192, delim = "\n"):
    global buffer
    while True:
        buffer += sock.recv(size)
        if buffer.find(delim) != -1:
            line, buffer = buffer.split("\n", 1)
            return line

if __name__ == "__main__":

    logging.basicConfig(filename = "server.log",
                        level = logging.DEBUG,
                        filemode = "w",
                        format = "%(asctime)s %(message)s",
                        datefmt = "%d/%m/%Y %I:%M:%S %p")

    logging.info("Starting server.")

    args        = parser.parse_args()
    TCP_IP      = args.tcp_ip
    TCP_PORT    = args.tcp_port
    BUFFER_SIZE = args.buffer_size

    sock        = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((TCP_IP, TCP_PORT))
    sock.listen(1)

    logging.info("Done. Waiting for connections...")

    conn, addr = sock.accept()

    logging.info("Got a connection, entering server loop.")

    while True:
        logging.info("Waiting message.")
        data = recv_message(conn, size = BUFFER_SIZE)
        logging.info("Received message.")
        if not data: break
        command = (data.strip()).split(" ")

        while len(command) != 0:
            keyword = command[0].upper()

            if keyword == CLONE:
                command = clone(conn, command)
            elif keyword == START:
                command = start(conn, command)
            elif keyword == MEASURE:
                command = measure(conn, command)
            elif keyword == STOP:
                command = stop(conn, command)
            elif keyword == STATUS:
                command = status(conn, command)
            elif keyword == GET:
                command = get_result(conn, command)
            elif keyword == LOAD:
                command = load_interface(conn, command)
            elif keyword == SHUTDOWN:
                command = shutdown(conn, command)
            elif keyword == DISCONNECT:
                command = disconnect(conn, command)
                conn, addr = sock.accept()
            else:
                command = unknown(conn, command)
