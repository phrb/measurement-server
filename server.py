#!/usr/bin/env python

import socket
import argparse

parser = argparse.ArgumentParser(description="Process server options.")

parser.add_argument("--tcp-port",
                    dest    = "tcp_port",
                    type    = int,
                    default = 8080,
                    help    = "The port to listen to.")
parser.add_argument("--buffer-size",
                    dest    = "buffer_size",
                    type    = int,
                    default = 1024,
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

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((TCP_IP, TCP_PORT))
    s.listen(1)

    conn, addr = s.accept()

    while 1:
        data = conn.recv(BUFFER_SIZE)
        if not data: break
        conn.send(data)
        command = (data.strip()).split(" ")

        if command[0] == "CLONE":
            conn.send("Cloning repository " + command[1] + "\n")
        elif command[0] == "START":
            conn.send("Starting the Measurement Server..." + "\n")
        elif command[0] == "MEASURE":
            conn.send("Measuring Configuration: " + command[1] + "\n")
