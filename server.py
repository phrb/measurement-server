#!/usr/bin/env python

import socket, argparse, opentuner, sys, threading

from commands import *
from status_codes import *

from time import sleep

parser = argparse.ArgumentParser(description="Process server options.")

parser.add_argument("--tcp-port",
                    dest    = "tcp_port",
                    type    = int,
                    default = 8080,
                    help    = "The port to listen to.")
parser.add_argument("--buffer-size",
                    dest    = "buffer_size",
                    type    = int,
                    default = 4096,
                    help    = "The message buffer size.")
parser.add_argument("--tcp-ip",
                    dest    = "tcp_ip",
                    type    = str,
                    default = '',
                    help    = "The message buffer size.")


if __name__ == "__main__":
    args        = parser.parse_args()
    TCP_IP      = args.tcp_ip
    TCP_PORT    = args.tcp_port
    BUFFER_SIZE = args.buffer_size

    sock        = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((TCP_IP, TCP_PORT))
    sock.listen(1)

    conn, addr = sock.accept()

    while 1:
        data = conn.recv(BUFFER_SIZE)
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
