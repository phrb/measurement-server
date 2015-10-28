import socket, argparse, sys, threading, subprocess, imp, os, pickle

from opentuner.resultsdb.models import Result, Input, Configuration

from status_codes import *
from error_codes import *

CLONE       = "CLONE"
START       = "START"
MEASURE     = "MEASURE"
STOP        = "STOP"
LOAD        = "LOAD"
STATUS      = "STATUS"
GET         = "GET"
SHUTDOWN    = "SHUTDOWN"
UNKNOWN     = "UNKNOWN"
DISCONNECT  = "DISCONNECT"

USER_MODULE = None
INTERFACE   = None
RUN         = None
RESULT      = None

def run(desired_result, input, limit):
    global SERVER_STATUS, RESULT
    try:
        RESULT = RUN(eval("USER_MODULE.{0}()".format(INTERFACE)),
                     desired_result,
                     input,
                     limit)
    except:
        SERVER_STATUS = AVAILABLE
        raise

    SERVER_STATUS = RESULT_READY

def get_result(conn, command):
    global SERVER_STATUS, RESULT

    if SERVER_STATUS == STOPPED:
        conn.send("{0} {1} {2} The server is not available.\n".format(GET,
                                                                      UNAVAILABLE_ERROR,
                                                                      SERVER_STATUS))
        command = []
    elif SERVER_STATUS != RESULT_READY:
        conn.send("{0} {1} {2} No results available.\n".format(GET,
                                                               NO_RESULTS_ERROR,
                                                               SERVER_STATUS))
        command = command[1:]
    else:
        result        = repr(pickle.dumps(RESULT))
        conn.send("{0} {1} {2} {3}\n".format(GET,
                                             NO_ERROR,
                                             SERVER_STATUS,
                                             result))
        RESULT        = None
        command       = command[1:]
        SERVER_STATUS = AVAILABLE

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
            retcode = subprocess.call("git clone {0} {1}".format(command[1],
                                                                 command[2]),
                                                                 shell = True)

            conn.send("{0} {1} {2} {3}\n".format(CLONE,
                                                 NO_ERROR,
                                                 SERVER_STATUS,
                                                 retcode))
        except OSError as e:
            print >>sys.stderr, "Execution failed:", e
            conn.send("{0} {1} {2} Execution failed.\n".format(CLONE,
                                                               GITCLONE_ERROR,
                                                               SERVER_STATUS))

        command = command[3:]

    return command

def load_interface(conn, command):
    global USER_MODULE, RUN, INTERFACE

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
            # Loads user module as USER_MODULE, using the file path
            # received from the user.
            USER_MODULE = imp.load_source("USER_MODULE", command[1])
            INTERFACE   = command[2]
            # Stores the measurement function to be used by the server;
            # Looks for the "run" function inside the user module.
            # TODO: Treat error.
            RUN = eval("USER_MODULE.{0}.run".format(INTERFACE))
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
        # Initialization...
        SERVER_STATUS = AVAILABLE

    command = command[1:]

    return command

def measure(conn, command):
    global SERVER_STATUS

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
    elif RUN is None:
        conn.send("{0} {1} {2} No \"run\" method defined.\n".format(MEASURE,
                                                                    NO_RUN_METHOD_ERROR,
                                                                    SERVER_STATUS))
        command = []
    else:
        SERVER_STATUS = MEASURING
        conn.send("{0} {1} {2} Setting up measurement.\n".format(MEASURE,
                                                                 NO_ERROR,
                                                                 SERVER_STATUS))
        desired_result = Result(configuration = pickle.loads(eval(command[1])))
        input          = pickle.loads(eval(command[2]))
        limit          = float(command[3])
        thread = threading.Thread(target=run, args=(desired_result,
                                                    input,
                                                    limit))
        thread.daemon = True
        thread.start()
        conn.send("{0} {1} {2} Measuring.\n".format(MEASURE,
                                                    NO_ERROR,
                                                    SERVER_STATUS))
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
    global SERVER_STATUS

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
