#!/usr/bin/env python
"""roschaos command line tool"""

from __future__ import print_function

# import errno
import os
import re
import sys
import socket

try:  # py3k
    import urllib.parse as urlparse
except ImportError:
    import urlparse


from argparse import ArgumentParser

try:
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy

import rosgraph
import rosnode
import rostopic

from rospy.core import xmlrpcapi


NAME = 'roschaos'
ID = '/roschaos'
TIMEOUT = 3.0


# def _roschaos_master_topic_scramble():
#     master = rosgraph.Master(ID)
#     master_rpc = xmlrpcapi(rosgraph.get_master_uri())
#     nodes = rosnode.get_node_names(namespace=None)
#     topic_types = rostopic._master_get_topic_types(master)
#     for node_id in nodes:
#         node_uri = rosnode.get_api_uri(master, node_id)
#         for topic_name, topic_type in topic_types:
#             pass
#             code, msg, val = master_rpc.registerPublisher(node_id, topic_name, topic_type, node_uri)
#             if code != 1:
#                 print("cannot register publication topic [%s] with master: %s" % (topic_name, msg))


def _roschaos_cmd_master(argv, parser):
    """
    Implements roschaos 'master' command.
    @param argv: command-line args
    @type  argv: [str]
    """
    subparsers = parser.add_subparsers(help='master subcommands', dest='master')
    unregister_parser = subparsers.add_parser(
        'unregister', help='Remove Registration')
    subsubparsers = unregister_parser.add_subparsers(
        help='unregister subcommands',
        dest='unregister')

    unregister_node_parser = subsubparsers.add_parser(
        'node', help='remove node registration')
    unregister_node_parser.add_argument(
        '--name',
        action='store',
        help='name expression')
    unregister_node_parser.add_argument(
        '--uri',
        action='store',
        help='uri expression')
    unregister_node_parser.add_argument(
        '--all',
        action='store_true',
        help='all nodes')

    unregister_service_parser = subsubparsers.add_parser(
        'service', help='remove service registration')
    unregister_service_parser.add_argument(
        '--name',
        action='store',
        help='name expression')

    unregister_topic_parser = subsubparsers.add_parser(
        'topic', help='remove topic registration')
    unregister_topic_parser.add_argument(
        '--name',
        action='store',
        help='name expression')
    unregister_topic_parser.add_argument(
        '--type',
        action='store',
        help='type expression')
    unregister_topic_parser.add_argument(
        '--subscribers',
        action='store_true',
        help='filter subscribers')
    unregister_topic_parser.add_argument(
        '--publishers',
        action='store_true',
        help='filter publishers')
    options, _ = parser.parse_known_args(argv)

    if options.master == 'unregister':
        if options.unregister == 'node':
            if options.all:
                _master_unregister_all_nodes()
            else:
                if not (options.name or options.uri):
                    parser.error('No action requested')
                _master_unregister_nodes(options.name, options.uri)
        elif options.unregister == 'service':
            _master_unregister_services(options.name)
        elif options.unregister == 'topic':
            if not (options.publishers or options.subscribers):
                parser.error('No --publisher or --subscriber filter provided')
            _master_unregister_topics(
                options.name,
                options.type,
                options.publishers,
                options.subscribers)


def _master_unregister_all_nodes():
    master = rosgraph.Master(ID)
    rosnode.cleanup_master_whitelist(master, [])


def _master_unregister_nodes(name_str, uri_str):
    name_pat = re.compile(name_str) if name_str else None
    uri_pat = re.compile(uri_str) if uri_str else None

    master = rosgraph.Master(ID)
    master_rpc = xmlrpcapi(rosgraph.get_master_uri())
    nodes = rosnode.get_node_names(namespace=None)
    topic_types = rostopic._master_get_topic_types(master)
    blacklisted_nodes = []
    for node_name in nodes:
        if name_pat:
            if not name_pat.match(node_name):
                continue
        node_uri = rosnode.get_api_uri(master, node_name)
        if uri_pat:
            if not uri_pat.match(node_uri):
                continue
        blacklisted_nodes.append(node_name)
    rosnode.cleanup_master_blacklist(master, blacklisted_nodes)


def _master_unregister_services(name_str):
    name_pat = re.compile(name_str) if name_str else None

    master = rosgraph.Master(ID)
    _, _, services = master.getSystemState()
    for service_name, nodes in services:
        if name_pat:
            if not name_pat.match(service_name):
                continue
        for node_name in nodes:
            service_api = master.lookupService(service_name)
            master_n = rosgraph.Master(node_name)
            master_n.unregisterService(service_name, service_api)
            print("Unregistering {} {}".format(service_name, node_name))


def _master_unregister_topics(name_str, type_str, filter_publishers, filter_subscribers):
    name_pat = re.compile(name_str) if name_str else None
    type_pat = re.compile(type_str) if type_str else None

    master = rosgraph.Master(ID)
    publishers, subscribers, _ = master.getSystemState()
    topic_types = master.getTopicTypes()
    if filter_publishers:
        for topic_name, nodes in publishers:
            if name_pat:
                if not name_pat.match(topic_name):
                    continue
            if type_pat:
                if not _check_types(topic_name, topic_types, type_pat):
                    continue
            for node_name in nodes:
                node_api = master.lookupNode(node_name)
                master_n = rosgraph.Master(node_name)
                print("Unregistering publisher {} {}".format(topic_name, node_name))
                master_n.unregisterPublisher(topic_name, node_api)
    if filter_subscribers:
        for topic_name, nodes in subscribers:
            if name_pat:
                if not name_pat.match(topic_name):
                    continue
            if type_pat:
                if not _check_types(topic_name, topic_types, type_pat):
                    continue
            for node_name in nodes:
                node_api = master.lookupNode(node_name)
                master_n = rosgraph.Master(node_name)
                print("Unregistering subscriber {} {}".format(topic_name, node_name))
                master_n.unregisterSubscriber(topic_name, node_api)


def _check_types(topic_name, topic_types, type_pat):
    is_match = False
    for _topic_name, _topic_type in topic_types:
        if topic_name == _topic_name:
            is_match = is_match or bool(type_pat.match(_topic_type))
    return is_match


def _slave_backtrace_master(node_api):
    """Not all ROS client libraries implemnt getMasterUri
    e.g. rospy but not roscpp"""
    socket.setdefaulttimeout(TIMEOUT)
    node = ServerProxy(node_api)
    master_uri = rosnode._succeed(node.getMasterUri(ID))
    print('ROS_MASTER_URI=', master_uri)
    os.environ['ROS_MASTER_URI'] = master_uri


def _roschaos_cmd_slave(argv, parser):
    """
    Implements roschaos 'node' command.
    @param argv: command-line args
    @type  argv: [str]
    """

    subparsers = parser.add_subparsers(help='slave subcommands', dest='slave')
    backtrace_parser = subparsers.add_parser(
        'backtrace', help='backtrace info from slave API')
    subsubparsers = backtrace_parser.add_subparsers(
        help='backtrace subcommands',
        dest='backtrace')

    backtrace_master_parser = subsubparsers.add_parser(
        'master', help='backtrace info about master')
    backtrace_master_parser.add_argument(
        '--uri',
        help='backtrace Master URI remotly')
    options, _ = parser.parse_known_args(argv)

    if options.slave == 'backtrace':
        if options.backtrace == 'master':
            if options.uri:
                _slave_backtrace_master(options.uri)
            else:
                parser.error('No action requested')


def _roschaos_cmd_param(argv, parser):
    """
    Implements roschaos 'param' command.
    @param argv: command-line args
    @type  argv: [str]
    """

    subparsers = parser.add_subparsers(help='param subcommands', dest='param')
    server_parser = subparsers.add_parser(
        'server', help='server API')
    subsubparsers = server_parser.add_subparsers(
        help='server subcommands',
        dest='server')

    server_unsubscribe_parser = subsubparsers.add_parser(
        'unsubscribe', help='unsubscribe from param updates')
    server_unsubscribe_parser.add_argument(
        '--node_name',
        action='store',
        help='node name expression')
    server_unsubscribe_parser.add_argument(
        '--node_uri',
        action='store',
        help='node uri expression')
    server_unsubscribe_parser.add_argument(
        '--param_key',
        action='store',
        required=True,
        help='param key expression')
    options, _ = parser.parse_known_args(argv)

    if options.param == 'server':
        if options.server == 'unsubscribe':
            if options.node_name or options.node_uri:
                _param_server_unsubscribe(
                    options.node_name,
                    options.node_uri,
                    options.param_key)
            else:
                parser.error('Either --node_name or --node_uri is required')


def _param_server_unsubscribe(node_name_str, node_uri_str, param_key_str):
    node_name_pat = re.compile(node_name_str) if node_name_str else None
    node_uri_pat = re.compile(node_uri_str) if node_uri_str else None
    param_key_pat = re.compile(param_key_str) if param_key_str else None

    master = rosgraph.Master(ID)
    param_keys = master.getParamNames()
    param_keys.sort()
    blacklisted_param_keys = []
    for param_key in param_keys:
        if param_key_pat.match(param_key):
            blacklisted_param_keys.append(param_key)

    nodes = rosnode.get_node_names(namespace=None)
    for node_name in nodes:
        if node_name_pat:
            if not node_name_pat.match(node_name):
                continue
        node_uri = rosnode.get_api_uri(master, node_name)
        if node_uri_pat:
            if not node_uri_pat.match(node_uri):
                continue
        master_n = rosgraph.Master(node_name)
        for blacklisted_param_key in blacklisted_param_keys:
            code = master_n.unsubscribeParam(node_uri, blacklisted_param_key)
            # API docs clame: If numUnsubscribed is zero it means that
            # the caller was not subscribed to the parameter.
            # In practace: this is not true, as 1 is always retruned no mater what
            # if code != 0:
            #     print("Unsubscribed {} {}".format(blacklisted_param_key, node_name))


def roschaosmain(argv=None):
    """
    Prints roschaos main entrypoint.
    @param argv: override sys.argv
    @param argv: [str]
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = ArgumentParser(prog=NAME)
    subparsers = parser.add_subparsers(help='roschaos Subcommands', dest='roschaos')
    master_parser = subparsers.add_parser(
        'master', help='master API toolkit', add_help=False)
    slave_parser = subparsers.add_parser(
        'slave', help='slave API toolkit', add_help=False)
    param_parser = subparsers.add_parser(
        'param', help='param API toolkit', add_help=False)
    options, _ = parser.parse_known_args(argv)
    argv = argv[1:]

    try:
        if options.roschaos == 'master':
            sys.exit(_roschaos_cmd_master(argv, master_parser) or 0)
        elif options.roschaos == 'slave':
            sys.exit(_roschaos_cmd_slave(argv, slave_parser) or 0)
        elif options.roschaos == 'param':
            sys.exit(_roschaos_cmd_param(argv, param_parser) or 0)
    except socket.error:
        print("Network communication failed." +
              " Most likely failed to communicate with master.", file=sys.stderr)
        sys.exit(1)
    except rosgraph.MasterError as err:
        print("ERROR: "+str(err), file=sys.stderr)
        sys.exit(1)
    except rosnode.ROSNodeException as err:
        print("ERROR: "+str(err), file=sys.stderr)
        sys.exit(1)
    except rostopic.ROSTopicException as err:
        sys.stderr.write("ERROR: %s\n" % str(err))
        sys.exit(1)
    except KeyboardInterrupt:
        pass
