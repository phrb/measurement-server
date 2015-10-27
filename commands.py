import socket, argparse, opentuner, sys, threading, subprocess, imp, os

from status_codes import *
from time import sleep

CLONE      = "CLONE"
START      = "START"
MEASURE    = "MEASURE"
STOP       = "STOP"
LOAD       = "LOAD"
STATUS     = "STATUS"
GET        = "GET"
SHUTDOWN   = "SHUTDOWN"
UNKNOWN    = "UNKNOWN"
DISCONNECT = "DISCONNECT"

INTERFACE  = None

def run(time):
    global SERVER_STATUS, RESULT_READY
    sleep(time)
    SERVER_STATUS = RESULT_READY

def get_result(conn, command):
    global SERVER_STATUS, AVAILABLE, RESULT_READY

    if SERVER_STATUS == STOPPED:
        conn.send(GET + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    elif SERVER_STATUS != RESULT_READY:
        conn.send(GET + " "  + str(SERVER_STATUS) + " No results available.\n")
        command = command[1:]
    else:
        conn.send(GET + " " + str(SERVER_STATUS) + " PICKLED_RESULT\n")
        command = command[1:]
        SERVER_STATUS = AVAILABLE

    return command

def clone(conn, command):
    global SERVER_STATUS, AVAILABLE

    if SERVER_STATUS == STOPPED:
        conn.send(CLONE + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    elif len(command) < 3:
        conn.send(CLONE + "  4 \"CLONE\" takes two arguments:\n\t\"CLONE REPO DIST_DIR\"\n")
        command = []
    else:
        conn.send(CLONE + " " + str(SERVER_STATUS) + " Cloning repository \"" +
                  command[1] + "\" to: \"" + command[2] + "\"\n")

        try:
            retcode = subprocess.call("git clone " + command[1] + " " +
                                      command[2], shell = True)

            conn.send(CLONE + " " + str(SERVER_STATUS) + " " + str(retcode) + "\n")
        except OSError as e:
            print >>sys.stderr, "Execution failed:", e
            conn.send(CLONE + " 6 Execution failed.")

        command = command[3:]

    return command

def load_interface(conn, command):
    global SERVER_STATUS, AVAILABLE, INTERFACE

    if SERVER_STATUS == STOPPED:
        conn.send(LOAD + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    elif len(command) < 3:
        conn.send(LOAD + "  4 \"LOAD\" takes two arguments:\n\t\"LOAD TUNER_PATH INTERFACE_NAME\"\n")
        command = []
    else:
        conn.send(LOAD + " " + str(SERVER_STATUS) + " Loading interface \"" +
                  command[2] + "\" from: \"" + command[1] + "\"\n")

        if os.path.isfile(command[1]):
            INTERFACE = imp.load_source("USER_MODULE", command[1])
            conn.send(LOAD + " " + str(SERVER_STATUS) + " Done.\n")
            eval("INTERFACE." + command[2] + ".run")
        else:
            conn.send(LOAD + " 7 No such file. Perhaps you should clone it first.\n")

        command = command[3:]

    return command

def start(conn, command):
    global SERVER_STATUS, STOPPED, AVAILABLE

    if SERVER_STATUS != STOPPED:
        conn.send(START + " " + str(SERVER_STATUS) + " The server was already started.\n")
    else:
        conn.send(START + " " + str(SERVER_STATUS) + " Starting measurement server...\n")
        # Initialization...
        SERVER_STATUS = AVAILABLE

    command = command[1:]

    return command

def measure(conn, command):
    global SERVER_STATUS, AVAILABLE, MEASURING

    if len(command) < 4:
        conn.send(MEASURE + " 4 \"MEASURE\" takes three arguments:\n\t\"")
        conn.send(MEASURE + " PICKLED_CONFIG PICKLED_INPUT LIMIT\"\n")
        command = []
    elif SERVER_STATUS != AVAILABLE:
        conn.send(MEASURE + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    else:
        SERVER_STATUS = MEASURING
        conn.send(MEASURE + " " + str(SERVER_STATUS) + " Measuring...\n")
        thread = threading.Thread(target=run, args=(16, ))
        thread.daemon = True
        thread.start()
        command = command[4:]

    return command

def disconnect(conn, command):
    conn.send(DISCONNECT + " " + str(SERVER_STATUS) + " Closing Connection.\n")
    conn.close()
    command = []

    return command

def stop(conn, command):
    global SERVER_STATUS, AVAILABLE, STOPPED

    if SERVER_STATUS != AVAILABLE:
        conn.send(STOP + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    else:
        conn.send(STOP + " " + str(SERVER_STATUS) + " Stopping the server.\n")
        SERVER_STATUS = STOPPED

    command = command[1:]
    return command

def shutdown(conn, command):
    global SERVER_STATUS, AVAILABLE

    if SERVER_STATUS != AVAILABLE:
        conn.send(SHUTDOWN + " " + str(SERVER_STATUS) + " The server is not available.\n")
        command = []
    else:
        conn.send(SHUTDOWN + " " + str(SERVER_STATUS) + " Shutting down the server.\n")
        disconnect(conn, command)
        sys.exit()

    return command

def status(conn, command):
    global SERVER_STATUS
    conn.send(STATUS + " " + str(SERVER_STATUS) + "\n")
    command = command[1:]
    return command

def unknown(conn, command):
    conn.send(UNKNOWN + " 5 Unknown command: " + command[0] + "\n")
    command = []
    return command
