# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2015 Red Hat, Inc.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---
#
import os
import sys
import time
import ldap
import logging
import pytest
import shutil
from lib389 import DirSrv, Entry, tools, tasks
from lib389._constants import *
from lib389.properties import *
from lib389.tasks import *
from lib389.utils import *

logging.getLogger(__name__).setLevel(logging.DEBUG)
log = logging.getLogger(__name__)

installation1_prefix = None


class TopologyStandalone(object):
    def __init__(self, standalone):
        standalone.open()
        self.standalone = standalone


@pytest.fixture(scope="module")
def topology(request):
    global installation1_prefix
    if installation1_prefix:
        args_instance[SER_DEPLOYED_DIR] = installation1_prefix

    # Creating standalone instance ...
    standalone = DirSrv(verbose=False)
    args_instance[SER_HOST] = HOST_STANDALONE
    args_instance[SER_PORT] = PORT_STANDALONE
    args_instance[SER_SERVERID_PROP] = SERVERID_STANDALONE
    args_instance[SER_CREATION_SUFFIX] = DEFAULT_SUFFIX
    args_standalone = args_instance.copy()
    standalone.allocate(args_standalone)
    instance_standalone = standalone.exists()
    if instance_standalone:
        standalone.delete()
    standalone.create()
    standalone.open()

    # Delete each instance in the end
    def fin():
        standalone.delete()
        if os.geteuid() == 0:
            os.system('setenforce 1')
    request.addfinalizer(fin)

    return TopologyStandalone(standalone)


def test_ticket47384(topology):
    '''
    Test pluginpath validation: relative and absolute paths

    With the inclusion of ticket 47601 - we do allow plugin paths
    outside the default location
    '''

    if os.geteuid() != 0:
        log.warn('This script must be run as root')
        return

    os.system('setenforce 0')

    PLUGIN_DN = 'cn=%s,cn=plugins,cn=config' % PLUGIN_WHOAMI
    tmp_dir = '/tmp'
    plugin_dir = get_plugin_dir(topology.standalone.prefix)

    # Copy the library to our tmp directory
    try:
        shutil.copy('%s/libwhoami-plugin.so' % plugin_dir, tmp_dir)
    except IOError as e:
        log.fatal('Failed to copy libwhoami-plugin.so to the tmp directory, error: '
                  + e.strerror)
        assert False
    try:
        shutil.copy('%s/libwhoami-plugin.la' % plugin_dir, tmp_dir)
    except IOError as e:
        log.warn('Failed to copy ' + plugin_dir +
                 '/libwhoami-plugin.la to the tmp directory, error: '
                  + e.strerror)

    #
    # Test adding valid plugin paths
    #
    # Try using the absolute path to the current library
    try:
        topology.standalone.modify_s(PLUGIN_DN, [(ldap.MOD_REPLACE,
                                     'nsslapd-pluginPath', '%s/libwhoami-plugin' % plugin_dir)])
    except ldap.LDAPError as e:
        log.error('Failed to set valid plugin path (%s): error (%s)' %
                  ('%s/libwhoami-plugin' % plugin_dir, e.message['desc']))
        assert False

    # Try using new remote location
    try:
        topology.standalone.modify_s(PLUGIN_DN, [(ldap.MOD_REPLACE,
                                     'nsslapd-pluginPath', '%s/libwhoami-plugin' % tmp_dir)])
    except ldap.LDAPError as e:
        log.error('Failed to set valid plugin path (%s): error (%s)' %
                  ('%s/libwhoami-plugin' % tmp_dir, e.message['desc']))
        assert False

    # Set plugin path back to the default
    try:
        topology.standalone.modify_s(PLUGIN_DN, [(ldap.MOD_REPLACE,
                                     'nsslapd-pluginPath', 'libwhoami-plugin')])
    except ldap.LDAPError as e:
        log.error('Failed to set valid relative plugin path (%s): error (%s)' %
                  ('libwhoami-plugin' % tmp_dir, e.message['desc']))
        assert False

    #
    # Test invalid path (no library present)
    #
    try:
        topology.standalone.modify_s(PLUGIN_DN, [(ldap.MOD_REPLACE,
                                     'nsslapd-pluginPath', '/bin/libwhoami-plugin')])
        # No exception?! This is an error
        log.error('Invalid plugin path was incorrectly accepted by the server!')
        assert False
    except ldap.UNWILLING_TO_PERFORM:
        # Correct, operation should be rejected
        pass
    except ldap.LDAPError as e:
        log.error('Failed to set invalid plugin path (%s): error (%s)' %
                  ('/bin/libwhoami-plugin', e.message['desc']))

    #
    # Test invalid relative path (no library present)
    #
    try:
        topology.standalone.modify_s(PLUGIN_DN, [(ldap.MOD_REPLACE,
                                     'nsslapd-pluginPath', '../libwhoami-plugin')])
        # No exception?! This is an error
        log.error('Invalid plugin path was incorrectly accepted by the server!')
        assert False
    except ldap.UNWILLING_TO_PERFORM:
        # Correct, operation should be rejected
        pass
    except ldap.LDAPError as e:
        log.error('Failed to set invalid plugin path (%s): error (%s)' %
                  ('../libwhoami-plugin', e.message['desc']))

    log.info('Test complete')


if __name__ == '__main__':
    # Run isolated
    # -s for DEBUG mode
    CURRENT_FILE = os.path.realpath(__file__)
    pytest.main("-s %s" % CURRENT_FILE)

