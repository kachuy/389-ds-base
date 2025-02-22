# --- BEGIN COPYRIGHT BLOCK ---
# Copyright (C) 2021 Red Hat, Inc.
# All rights reserved.
#
# License: GPL (version 3 or any later version).
# See LICENSE for details.
# --- END COPYRIGHT BLOCK ---

import logging
import ldap
import pytest
from lib389.topologies import topology_st
from lib389.plugins import RetroChangelogPlugin
from lib389._constants import *
from lib389.utils import *
from lib389.tasks import *
from lib389.cli_base import FakeArgs, connect_instance, disconnect_instance
from lib389.cli_base.dsrc import dsrc_arg_concat
from lib389.cli_conf.plugins.retrochangelog import retrochangelog_add_attr
from lib389.idm.user import UserAccount, UserAccounts
from lib389.idm.domain import Domain
from lib389._mapped_object import DSLdapObjects

pytestmark = pytest.mark.tier1

USER1_DN = 'uid=user1,ou=people,'+ DEFAULT_SUFFIX
USER2_DN = 'uid=user2,ou=people,'+ DEFAULT_SUFFIX
USER_PW = 'password'
ATTR_HOMEPHONE = 'homePhone'
ATTR_CARLICENSE = 'carLicense'

log = logging.getLogger(__name__)

#unstable or unstatus tests, skipped for now
@pytest.mark.flaky(max_runs=2, min_passes=1)
def test_retrocl_exclude_attr_add(topology_st):
    """ Test exclude attribute feature of the retrocl plugin for add operation

    :id: 3481650f-2070-45ef-9600-2500cfc51559

    :setup: Standalone instance

    :steps:
        1. Enable dynamic plugins
        2. Confige retro changelog plugin
        3. Add an entry
        4. Ensure entry attrs are in the changelog
        5. Exclude an attr
        6. Add another entry
        7. Ensure excluded attr is not in the changelog

    :expectedresults:
        1. Success
        2. Success
        3. Success
        4. Success
        5. Success
        6. Success
        7. Success
    """

    st = topology_st.standalone

    log.info('Configure retrocl plugin')
    rcl = RetroChangelogPlugin(st)
    rcl.disable()
    rcl.enable()
    rcl.replace('nsslapd-attribute', 'nsuniqueid:targetUniqueId')

    log.info('Restarting instance')
    try:
        st.restart()
    except ldap.LDAPError as e:
        ldap.error('Failed to restart instance ' + e.args[0]['desc'])
        assert False

    users = UserAccounts(st, DEFAULT_SUFFIX)

    log.info('Adding user1')
    try:
        users.create(properties={
            'sn': '1',
            'cn': 'user 1',
            'uid': 'user1',
            'uidNumber': '11',
            'gidNumber': '111',
            'givenname': 'user1',
            'homePhone': '0861234567',
            'carLicense': '131D16674',
            'mail': 'user1@whereever.com',
            'homeDirectory': '/home/user1',
            'userpassword': USER_PW})
    except ldap.ALREADY_EXISTS:
        pass
    except ldap.LDAPError as e:
        log.error("Failed to add user1: " + str(e))

    log.info('Verify homePhone and carLicense attrs are in the changelog changestring')
    try:
        retro_changelog_suffix = DSLdapObjects(st, basedn=RETROCL_SUFFIX)
        cllist = retro_changelog_suffix.filter(f'(targetDn={USER1_DN})')
    except ldap.LDAPError as e:
        log.fatal("Changelog search failed, error: " + str(e))
        assert False
    assert len(cllist) > 0
    if  cllist[0].present('changes'):
        clstr = str(cllist[0].get_attr_vals_utf8('changes'))
        assert ATTR_HOMEPHONE in clstr
        assert ATTR_CARLICENSE in clstr

    log.info('Excluding attribute ' + ATTR_HOMEPHONE)
    args = FakeArgs()
    args.connections = [st.host + ':' + str(st.port) + ':' + DN_DM + ':' + PW_DM]
    args.instance = 'standalone1'
    args.basedn = None
    args.binddn = None
    args.starttls = False
    args.pwdfile = None
    args.bindpw = None
    args.prompt = False
    args.exclude_attrs = ATTR_HOMEPHONE
    args.func = retrochangelog_add_attr
    dsrc_inst = dsrc_arg_concat(args, None)
    inst = connect_instance(dsrc_inst, False, args)
    result = args.func(inst, None, log, args)
    disconnect_instance(inst)
    assert result is None

    log.info('Restarting instance')
    try:
        st.restart()
    except ldap.LDAPError as e:
        ldap.error('Failed to restart instance ' + e.args[0]['desc'])
        assert False

    log.info('Adding user2')
    try:
        users.create(properties={
            'sn': '2',
            'cn': 'user 2',
            'uid': 'user2',
            'uidNumber': '22',
            'gidNumber': '222',
            'givenname': 'user2',
            'homePhone': '0879088363',
            'carLicense': '04WX11038',
            'mail': 'user2@whereever.com',
            'homeDirectory': '/home/user2',
            'userpassword': USER_PW})
    except ldap.ALREADY_EXISTS:
        pass
    except ldap.LDAPError as e:
        log.error("Failed to add user2: " + str(e))

    log.info('Verify homePhone attr is not in the changelog changestring')
    try:
        cllist = retro_changelog_suffix.filter(f'(targetDn={USER2_DN})')
        assert len(cllist) > 0
        if  cllist[0].present('changes'):
            clstr = str(cllist[0].get_attr_vals_utf8('changes'))
            assert ATTR_HOMEPHONE not in clstr
            assert ATTR_CARLICENSE in clstr
    except ldap.LDAPError as e:
        log.fatal("Changelog search failed, error: " + str(e))
        assert False

#unstable or unstatus tests, skipped for now
@pytest.mark.flaky(max_runs=2, min_passes=1)
def test_retrocl_exclude_attr_mod(topology_st):
    """ Test exclude attribute feature of the retrocl plugin for mod operation

    :id: f6bef689-685b-4f86-a98d-f7e6b1fcada3

    :setup: Standalone instance

    :steps:
        1. Enable dynamic plugins
        2. Confige retro changelog plugin
        3. Add user1 entry
        4. Ensure entry attrs are in the changelog
        5. Exclude an attr
        6. Modify user1 entry
        7. Ensure excluded attr is not in the changelog

    :expectedresults:
        1. Success
        2. Success
        3. Success
        4. Success
        5. Success
        6. Success
        7. Success
    """

    st = topology_st.standalone

    log.info('Configure retrocl plugin')
    rcl = RetroChangelogPlugin(st)
    rcl.disable()
    rcl.enable()
    rcl.replace('nsslapd-attribute', 'nsuniqueid:targetUniqueId')

    log.info('Restarting instance')
    try:
        st.restart()
    except ldap.LDAPError as e:
        ldap.error('Failed to restart instance ' + e.args[0]['desc'])
        assert False

    users = UserAccounts(st, DEFAULT_SUFFIX)

    log.info('Adding user1')
    try:
        user1 = users.create(properties={
            'sn': '1',
            'cn': 'user 1',
            'uid': 'user1',
            'uidNumber': '11',
            'gidNumber': '111',
            'givenname': 'user1',
            'homePhone': '0861234567',
            'carLicense': '131D16674',
            'mail': 'user1@whereever.com',
            'homeDirectory': '/home/user1',
            'userpassword': USER_PW})
    except ldap.ALREADY_EXISTS:
        user1 = UserAccount(st, dn=USER1_DN)
    except ldap.LDAPError as e:
        log.error("Failed to add user1: " + str(e))

    log.info('Verify homePhone and carLicense attrs are in the changelog changestring')
    try:
        retro_changelog_suffix = DSLdapObjects(st, basedn=RETROCL_SUFFIX)
        cllist = retro_changelog_suffix.filter(f'(targetDn={USER1_DN})')
    except ldap.LDAPError as e:
        log.fatal("Changelog search failed, error: " + str(e))
        assert False
    assert len(cllist) > 0
    if  cllist[0].present('changes'):
        clstr = str(cllist[0].get_attr_vals_utf8('changes'))
        assert ATTR_HOMEPHONE in clstr
        assert ATTR_CARLICENSE in clstr

    log.info('Excluding attribute ' + ATTR_CARLICENSE)
    args = FakeArgs()
    args.connections = [st.host + ':' + str(st.port) + ':' + DN_DM + ':' + PW_DM]
    args.instance = 'standalone1'
    args.basedn = None
    args.binddn = None
    args.starttls = False
    args.pwdfile = None
    args.bindpw = None
    args.prompt = False
    args.exclude_attrs = ATTR_CARLICENSE
    args.func = retrochangelog_add_attr
    dsrc_inst = dsrc_arg_concat(args, None)
    inst = connect_instance(dsrc_inst, False, args)
    result = args.func(inst, None, log, args)
    disconnect_instance(inst)
    assert result is None

    log.info('Restarting instance')
    try:
        st.restart()
    except ldap.LDAPError as e:
        ldap.error('Failed to restart instance ' + e.args[0]['desc'])
        assert False

    log.info('Modify user1 carLicense attribute')
    try:
        user1.replace(ATTR_CARLICENSE, "123WX321")
    except ldap.LDAPError as e:
        log.fatal('test_retrocl_exclude_attr_mod: Failed to update user1 attribute: error ' + e.message['desc'])
        assert False

    log.info('Verify carLicense attr is not in the changelog changestring')
    try:
        cllist = retro_changelog_suffix.filter(f'(targetDn={USER1_DN})')
        assert len(cllist) > 0
        # There will be 2 entries in the changelog for this user, we are only
        #interested in the second one, the modify operation.
        if  cllist[1].present('changes'):
            clstr = str(cllist[1].get_attr_vals_utf8('changes'))
            assert ATTR_CARLICENSE not in clstr
    except ldap.LDAPError as e:
        log.fatal("Changelog search failed, error: " + str(e))
        assert False


def test_retrocl_trimming(topology_st):
    """Test retrocl trimming works

    :id: 54c6747f-6772-43b7-8b03-09e13fa0c205
    :setup: Standalone Instance
    :steps:
        1. Enable Retro changelog
        2. Add a bunch of entries
        3. Configure trimming
        4. Verify trimming occurred
    :expectedresults:
        1. Success
        2. Success
        3. Success
        4. Success
    """

    inst = topology_st.standalone
    # Configure plugin
    log.info('Configure retrocl plugin')
    rcl = RetroChangelogPlugin(inst)
    rcl.enable()
    inst.restart()

    # Do some updates
    suffix = Domain(inst, DEFAULT_SUFFIX)
    for idx in range(0, 10):
        suffix.replace('description', str(idx))

    # Setup trimming
    rcl.replace('nsslapd-changelog-trim-interval', '2')
    rcl.replace('nsslapd-changelogmaxage', '5s')
    inst.config.set('nsslapd-errorlog-level', '65536') # plugin logging
    inst.restart()

    # Verify trimming occurs
    time.sleep(5)
    assert inst.searchErrorsLog("trim_changelog: removed ")

    # Clean up
    inst.config.set('nsslapd-errorlog-level', '0')


if __name__ == '__main__':
    # Run isolated
    # -s for DEBUG mode
    CURRENT_FILE = os.path.realpath(__file__)
    pytest.main("-s %s" % CURRENT_FILE)
