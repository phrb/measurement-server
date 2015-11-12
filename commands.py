import socket, argparse, sys, logging
import threading, subprocess, imp
import os, pickle, random, uuid

from opentuner.resultsdb.models import Result, Input, Configuration

from status_codes import *
from error_codes import *

CLONE               = "CLONE"
START               = "START"
MEASURE             = "MEASURE"
STOP                = "STOP"
LOAD                = "LOAD"
STATUS              = "STATUS"
GET                 = "GET"
SHUTDOWN            = "SHUTDOWN"
UNKNOWN             = "UNKNOWN"
DISCONNECT          = "DISCONNECT"

user_module         = None
interface           = None
user_run            = None

queue_lock          = threading.Lock()

results             = {}
configuration_queue = {}
processing          = []

logger              = logging.getLogger("MeasurementServer")

def run():
    global results, configuration_queue, processing, logger

    while SERVER_STATUS == AVAILABLE:
        if bool(configuration_queue):
            queue_lock.acquire()

            result_id     = random.choice(configuration_queue.keys())
            configuration = configuration_queue.pop(result_id)
            processing.append(result_id)

            queue_lock.release()

            logger.debug("Desired Result Configuration: {0}".format(configuration[0].configuration.data))

            result = user_run(eval("user_module.{0}()".format(interface)),
                                   configuration[0],
                                   configuration[1],
                                   configuration[2])
            queue_lock.acquire()

            processing.pop()
            results[result_id] = result

            queue_lock.release()

def get_result(conn, command):
    global results

    if SERVER_STATUS == STOPPED:
        conn.send("{0} {1} {2} The server is not available.\n".format(GET,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    elif len(command) < 2:
        conn.send(("{0} {1} {2} \"GET\" takes one argument:\n\t"
                   "\"GET RESULT_ID\"\n").format(GET,
                                                 ARGUMENT_ERROR,
                                                 SERVER_STATUS))
        command = []
    elif command[1] not in results:
        if command[1] in processing:
            conn.send("{0} {1} {2} {3} Result is not ready.\n".format(GET,
                                                                      NOT_READY_ERROR,
                                                                      SERVER_STATUS,
                                                                      command[1]))
        else:
            conn.send("{0} {1} {2} {3} No such result.\n".format(GET,
                                                                 NO_SUCH_RESULT_ERROR,
                                                                 SERVER_STATUS,
                                                                 command[1]))
        command = command[2:]
    else:
        queue_lock.acquire()

        result = repr(pickle.dumps(results.pop(command[1])))

        queue_lock.release()
        conn.send("{0} {1} {2} {3} {4}\n".format(GET,
                                                 NO_ERROR,
                                                 SERVER_STATUS,
                                                 command[1],
                                                 result))
        command = command[2:]

    return command

def clone(conn, command):
    if SERVER_STATUS == STOPPED:
        conn.send("{0} {1} {2} The server is not available.\n".format(CLONE,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    elif len(command) < 3:
        conn.send(("{0} {1} {2} \"CLONE\" takes two arguments:\n\t"
                   "\"CLONE REPO DIST_DIR\"\n").format(CLONE,
                                                       ARGUMENT_ERROR,
                                                       SERVER_STATUS))
        command = []
    else:
        conn.send("{0} {1} {2} Cloning.\n".format(CLONE,
                                                  NO_ERROR,
                                                  SERVER_STATUS))

        try:
            retcode = subprocess.call("git clone --recursive {0} {1}".format(command[1],
                                                                             command[2]),
                                                                             shell = True)

            conn.send("{0} {1} {2} {3}\n".format(CLONE,
                                                 NO_ERROR,
                                                 SERVER_STATUS,
                                                 retcode))
        except OSError as e:
            conn.send("{0} {1} {2} Execution failed.\n".format(CLONE,
                                                               GITCLONE_ERROR,
                                                               SERVER_STATUS))

        command = command[3:]

    return command

def load_interface(conn, command):
    global user_module, user_run, interface, logger

    if SERVER_STATUS == STOPPED:
        conn.send("{0} {1} {2} The server is not available.\n".format(LOAD,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    elif len(command) < 3:
        conn.send(("{0} {1} {2} \"LOAD\" takes two arguments:\n\t"
                   "\"LOAD TUNER_PATH INTERFACE_NAME\"\n").format(LOAD,
                                                                 ARGUMENT_ERROR,
                                                                 SERVER_STATUS))
        command = []
    else:
        conn.send("{0} {1} {2} Loading interface.\n".format(LOAD,
                                                            NO_ERROR,
                                                            SERVER_STATUS))
        if os.path.isfile(command[1]):
            sys.path.insert(1, os.path.dirname(command[1]))
            # Loads user module as user_module, using the file path
            # received from the user.
            user_module = imp.load_source("user_module", command[1])

            logger.debug("Changing working directory to {0}".format(os.path.dirname(command[1])))
            os.chdir(os.path.dirname(command[1]))

            interface   = command[2]
            # Stores the measurement function to be used by the server;
            # Looks for the "run" function inside the user module.
            # TODO: Treat error.
            user_run = eval("user_module.{0}.run".format(interface))
            conn.send("{0} {1} {2} Done.\n".format(LOAD,
                                                   NO_ERROR,
                                                   SERVER_STATUS))
        else:
            conn.send(("{0} {1} {2} No such file."
                       " Perhaps you should clone it first.\n").format(LOAD,
                                                                       NO_FILE_ERROR,
                                                                       SERVER_STATUS))

        command = command[3:]

    return command

def start(conn, command):
    global SERVER_STATUS

    if SERVER_STATUS != STOPPED:
        conn.send("{0} {1} {2} The server was already started.\n".format(START,
                                                                         STARTED_ERROR,
                                                                         SERVER_STATUS))
    else:
        conn.send("{0} {1} {2} Starting measurement server...\n".format(START,
                                                                        NO_ERROR,
                                                                        SERVER_STATUS))
        SERVER_STATUS = AVAILABLE
        thread        = threading.Thread(target=run, args=())
        thread.daemon = True
        thread.start()

    command = command[1:]

    return command

def measure(conn, command):
    global configuration_queue
    if len(command) < 4:
        conn.send(("{0} {1} {2} \"MEASURE\" takes three arguments:\n\t"
                   "\"MEASURE PICKLED_CONFIG PICKLED_INPUT LIMIT\"\n").format(MEASURE,
                                                                              ARGUMENT_ERROR,
                                                                              SERVER_STATUS))
        command = []
    elif SERVER_STATUS != AVAILABLE:
        conn.send("{0} {1} {2} The server is not available.\n".format(MEASURE,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    elif user_run is None:
        conn.send("{0} {1} {2} No \"run\" method defined.\n".format(MEASURE,
                                                                    NO_RUN_METHOD_ERROR,
                                                                    SERVER_STATUS))
        command = []
    else:
        conn.send("{0} {1} {2} Setting up measurement.\n".format(MEASURE,
                                                                 NO_ERROR,
                                                                 SERVER_STATUS))
        desired_result                 = Result(configuration = pickle.loads(eval(command[1])))
        input                          = pickle.loads(eval(command[2]))
        limit                          = float(command[3])
        result_id                      = str(uuid.uuid4())
        queue_lock.acquire()

        configuration_queue[result_id] = (desired_result, input, limit)

        queue_lock.release()
        conn.send("{0} {1} {2} {3} Measuring.\n".format(MEASURE,
                                                        NO_ERROR,
                                                        SERVER_STATUS,
                                                        result_id))
        command = command[4:]

    return command

def disconnect(conn, command):
    conn.send("{0} {1} {2} Closing connection.\n".format(DISCONNECT,
                                                         NO_ERROR,
                                                         SERVER_STATUS))
    conn.close()
    command = []

    return command

def stop(conn, command):
    global SERVER_STATUS, results, configuration_queue, processing

    if SERVER_STATUS != AVAILABLE:
        conn.send("{0} {1} {2} The server is not available.\n".format(STOP,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    else:
        conn.send("{0} {1} {2} Stopping the server.\n".format(STOP,
                                                              NO_ERROR,
                                                              SERVER_STATUS))
        SERVER_STATUS = STOPPED
        queue_lock.acquire()

        results             = {}
        configuration_queue = {}
        processing          = []

        queue_lock.release()

    command = command[1:]
    return command

def shutdown(conn, command):
    if SERVER_STATUS != AVAILABLE:
        conn.send("{0} {1} {2} The server is not available.\n".format(SHUTDOWN,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    else:
        conn.send("{0} {1} {2} Shutting down the server.\n".format(SHUTDOWN,
                                                                   NO_ERROR,
                                                                   SERVER_STATUS))
        disconnect(conn, command)
        sys.exit()

    return command

def status(conn, command):
    conn.send("{0} {1} {2}\n".format(STATUS, NO_ERROR, SERVER_STATUS))
    command = command[1:]
    return command

def unknown(conn, command):
    conn.send("{0} {1} {2} {3} Unknown command.\n".format(UNKNOWN,
                                                          UNKNOWN_COMMAND_ERROR,
                                                          SERVER_STATUS,
                                                          command[0]))
    command = []
    return command
