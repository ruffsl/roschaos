#!/usr/bin/env python
"""roschaos command line tool"""

from __future__ import print_function

import os
import errno
import sys
import socket
import time
try:
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy

try: #py3k
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from argparse import ArgumentParser

import rospy
import rosgraph
import rostopic
import rosnode

from rospy.core import xmlrpcapi


NAME = 'roschaos'
ID = '/roschaos'
TIMEOUT = 3.0


def _roschaos_master_topic_unlist():
    master = rosgraph.Master(ID)
    rosnode.cleanup_master_whitelist(master, [])


def _roschaos_master_topic_scramble():
    master = rosgraph.Master(ID)
    master_rpc = xmlrpcapi(rosgraph.get_master_uri())
    nodes = rosnode.get_node_names(namespace=None)
    topic_types = rostopic._master_get_topic_types(master)
    for node_id in nodes:
        node_uri = rosnode.get_api_uri(master, node_id)
        for topic_name, topic_type in topic_types:
            pass
            code, msg, val = master_rpc.registerPublisher(node_id, topic_name, topic_type, node_uri)
            if code != 1:
                print("cannot register publication topic [%s] with master: %s" % (topic_name, msg))


def _roschaos_cmd_master(argv):
    """
    Implements roschaos 'master' command.
    @param argv: command-line args
    @type  argv: [str]
    """
    args = argv[2:]
    parser = ArgumentParser(prog=NAME)
    subparsers = parser.add_subparsers(help='Master Subcommands')
    topic_parser = subparsers.add_parser(
        'topic', help='Modify Topic Registration')
    topic_parser.add_argument(
        '--scramble',
        action='store_true',
        help='Scramble all topic registration')
    topic_parser.add_argument(
        '--unlist',
        action='store_true',
        help='Unlist all topic registration')

    if options.scramble:
        _roschaos_master_topic_scramble()
    if options.unlist:
        _roschaos_master_topic_unlist()


def _roschaos_node_master_backtrace(node_api):
    """Not all ROS client libraries implemnt getMasterUri
    e.g. rospy but not roscpp"""
    socket.setdefaulttimeout(TIMEOUT)
    node = ServerProxy(node_api)
    master_uri = rosnode._succeed(node.getMasterUri(ID))
    print('ROS_MASTER_URI=', master_uri)
    os.environ['ROS_MASTER_URI'] = master_uri


def _roschaos_cmd_node(argv):
    """
    Implements roschaos 'node' command.
    @param argv: command-line args
    @type  argv: [str]
    """
    args = argv[2:]
    parser = ArgumentParser(prog=NAME)
    subparsers = parser.add_subparsers(help='Node Subcommands')
    server_parser = subparsers.add_parser(
        'master', help='Interact with Node Slave API')
    server_parser.add_argument(
        '--backtrace',
        help='Backtrace Master URI remotly')
    options, args = parser.parse_known_args(args)

    if options.backtrace:
        _roschaos_node_master_backtrace(options.backtrace)


def _roschaos_master_param_scramble():
    # TODO
    pass


def _roschaos_master_param_unlist():
    # TODO
    pass


def _roschaos_cmd_param(argv):
    """
    Implements roschaos 'param' command.
    @param argv: command-line args
    @type  argv: [str]
    """
    args = argv[2:]
    parser = ArgumentParser(prog=NAME)
    subparsers = parser.add_subparsers(help='Param Subcommands')
    server_parser = subparsers.add_parser(
        'server', help='Modify Server Registration')
    server_parser.add_argument(
        '--scramble',
        action='store_true',
        help='Scramble all param registration')
    server_parser.add_argument(
        '--unlist',
        action='store_true',
        help='Unlist all param registration')
    options, args = parser.parse_known_args(args)

    if options.scramble:
        _roschaos_master_param_scramble()
    if options.unlist:
        _roschaos_master_param_unlist()

def _fullusage():
    print("""roschaos is a command-line tool for pentesting ROS APIs.
Commands:
\troschaos master topic --scramble\tscramble all topic registration
\troschaos master topic --unlist\t\tunlist all topic registration
\troschaos param server --scramble\tscramble all param registration
\troschaos param server --unlist\t\tunlist all param registration
\troschaos node master --backtrace\tbacktrace Master URI remotly from node
Type roschaos <command> -h for more detailed usage, e.g. 'roschaos master topic -h'
""")
    sys.exit(getattr(os, 'EX_USAGE', 1))

def roschaosmain(argv=None):
    """
    Prints roschaos main entrypoint.
    @param argv: override sys.argv
    @param argv: [str]
    """
    if argv == None:
        argv = sys.argv
    if len(argv) == 1:
        _fullusage()
    try:
        command = argv[1]
        if command == 'master':
            sys.exit(_roschaos_cmd_master(argv) or 0)
        elif command == 'node':
            sys.exit(_roschaos_cmd_node(argv) or 0)
        elif command == 'param':
            sys.exit(_roschaos_cmd_param(argv) or 0)
        elif command == '--help':
            _fullusage(False)
        else:
            _fullusage()
    except socket.error:
        print("Network communication failed. Most likely failed to communicate with master.", file=sys.stderr)
        sys.exit(1)
    except rosgraph.MasterError as e:
        print("ERROR: "+str(e), file=sys.stderr)
        sys.exit(1)
    except rosnode.ROSNodeException as e:
        print("ERROR: "+str(e), file=sys.stderr)
        sys.exit(1)
    except rostopic.ROSTopicException as e:
        sys.stderr.write("ERROR: %s\n"%str(e))
        sys.exit(1)
    except KeyboardInterrupt: pass
