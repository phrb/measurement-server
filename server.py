#!/usr/bin/env python

import socket, argparse, opentuner, sys, threading
from time import sleep

parser = argparse.ArgumentParser(description="Process server options.")

AVAILABLE    = 0
MEASURING    = 1
RESULT_READY = 2
STOPPED      = 3

STATUS       = STOPPED

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

def run(time):
    global STATUS, RESULT_READY
    sleep(time)
    STATUS = RESULT_READY

def get_result(conn, command):
    global STATUS, AVAILABLE, RESULT_READY

    if STATUS == STOPPED:
        conn.send("GET " + str(STATUS) + " The server is not available.\n")
        command = []
    elif STATUS != RESULT_READY:
        conn.send("GET " + str(STATUS) + " No results available.\n")
        command = command[1:]
    else:
        conn.send("GET " + str(STATUS) + " PICKLED_RESULT\n")
        command = command[1:]
        STATUS = AVAILABLE

    return command

def clone(conn, command):
    global STATUS, AVAILABLE

    if len(command) < 3:
        conn.send("CLONE 4 \"CLONE\" takes two arguments:\n\t\"CLONE REPO DIST_DIR\"\n")
        command = []
    elif STATUS == STOPPED:
        conn.send("CLONE " + str(STATUS) + " The server is not available.\n")
        command = []
    else:
        conn.send("CLONE " + str(STATUS) + " Cloning repository \"" +
                  command[1] + "\" to: \"" + command[2] + "\"\n")
        # Cloning
        command = command[3:]

    return command

def start(conn, command):
    global STATUS, STOPPED, AVAILABLE

    if STATUS != STOPPED:
        conn.send("START " + str(STATUS) + " The server was already started.\n")
    else:
        conn.send("START " + str(STATUS) + " Starting measurement server...\n")
        # Initialization...
        STATUS = AVAILABLE

    command = command[1:]

    return command

def measure(conn, command):
    global STATUS, AVAILABLE, MEASURING

    if len(command) < 4:
        conn.send("MEASURE 4 \"MEASURE\" takes three arguments:\n\t\"")
        conn.send("MEASURE PICKLED_CONFIG PICKLED_INPUT LIMIT\"\n")
        command = []
    elif STATUS != AVAILABLE:
        conn.send("MEASURE " + str(STATUS) + " The server is not available.\n")
        command = []
    else:
        STATUS = MEASURING
        conn.send("MEASURE " + str(STATUS) + " Measuring...\n")
        thread = threading.Thread(target=run, args=(16, ))
        thread.daemon = True
        thread.start()
        command = command[4:]

    return command

def disconnect(conn, command):
    conn.send("DISCONNECT " + str(STATUS) + " Closing Connection.\n")
    conn.close()
    command = []

    return command

def stop(conn, command):
    global STATUS, AVAILABLE, STOPPED

    if STATUS != AVAILABLE:
        conn.send("STOP " + str(STATUS) + " The server is not available.\n")
        command = []
    else:
        conn.send("STOP " + str(STATUS) + " Stopping the server.\n")
        STATUS = STOPPED

    command = command[1:]
    return command

def shutdown(conn, command):
    global STATUS, AVAILABLE

    if STATUS != AVAILABLE:
        conn.send("SHUTDOWN " + str(STATUS) + " The server is not available.\n")
        command = []
    else:
        conn.send("SHUTDOWN " + str(STATUS) + " Shutting down the server.\n")
        disconnect(conn, command)
        sys.exit()

    return command

def status(conn, command):
    global STATUS
    conn.send("STATUS " + str(STATUS) + "\n")
    command = command[1:]
    return command

def unknown(conn, command):
    conn.send("UNKNOWN 5 Unknown command: " + command[0] + "\n")
    command = []
    return command

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

            if keyword == "CLONE":
                command = clone(conn, command)
            elif keyword == "START":
                command = start(conn, command)
            elif keyword == "MEASURE":
                command = measure(conn, command)
            elif keyword == "STOP":
                command = stop(conn, command)
            elif keyword == "STATUS":
                command = status(conn, command)
            elif keyword == "GET":
                command = get_result(conn, command)
            elif keyword == "SHUTDOWN":
                command = shutdown(conn, command)
            elif keyword == "DISCONNECT":
                command = disconnect(conn, command)
                conn, addr = sock.accept()
            else:
                command = unknown(conn, command)
