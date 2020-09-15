# -*- coding: utf-8 -*-
#
# Copyright (C) 2019-2020 CERN.
#
# CDS-ILS is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Test LDAP functions."""

import pytest
from invenio_accounts.models import User
from invenio_oauthclient.models import RemoteAccount, UserIdentity
from invenio_userprofiles.models import UserProfile

from cds_ils.ldap.api import check_user_for_update, delete_user, \
    import_ldap_users
from cds_ils.ldap.models import Agent, LdapSynchronizationLog, TaskStatus


def test_delete_user(app_with_mail, system_user, testdata):

    with app_with_mail.extensions["mail"].record_messages() as outbox:
        assert len(outbox) == 0
        delete_user(system_user)
        assert len(outbox) == 1
        assert outbox[0].recipients == [
            app_with_mail.config["MANAGEMENT_EMAIL"]
        ]


def test_check_users_for_update(app, system_user):
    """Test check for users update in sync command."""
    with app.app_context():
        user = RemoteAccount.query.join(User).one()
        ldap_user = {
            "displayName": [b"System User"],
            "department": [b"Another department"],
            "uidNumber": [b"1"],
            "mail": [b"system.user@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"1"],
        }
        check_user_for_update(user, ldap_user)
        assert user.extra_data["department"] == "Another department"


def test_import_ldap_users(app):
    """Test that ldap user is created."""
    ldap_users = [
        {
            "displayName": [b"Ldap User"],
            "department": [b"Department"],
            "uidNumber": [b"1"],
            "mail": [b"ldap.user@cern.ch"],
            "cernAccountType": [b"Primary"],
            "employeeID": [b"1"],
        }
    ]

    import_ldap_users(ldap_users)

    user = User.query.filter(
        User.email == ldap_users[0]["mail"][0].decode("utf8")
    ).one()
    assert user

    assert UserProfile.query.filter(UserProfile.user_id == user.id).one()
    user_identity = UserIdentity.query.filter(
        UserIdentity.id == ldap_users[0]["uidNumber"][0].decode("utf8")
    ).one()
    assert user_identity
    assert user_identity.method == "cern_openid"
    assert RemoteAccount.query.filter(RemoteAccount.user_id == user.id).one()


def test_log_table(app, db):
    """Test that the log table works."""

    def find(log):
        return LdapSynchronizationLog.query.filter_by(id=log.id).one_or_none()

    # Basic insertion
    log = LdapSynchronizationLog.create_cli()
    found = find(log)
    assert found
    assert found.status == TaskStatus.RUNNING and found.agent == Agent.CLI
    found.query.delete()
    found = find(log)
    assert not found

    # Change state
    log = LdapSynchronizationLog.create_celery("1")
    found = find(log)
    assert found.status == TaskStatus.RUNNING and found.agent == Agent.CELERY
    assert found.task_id == "1"
    found.set_succeeded(5, 6, 7, 8)
    found = find(log)
    assert found.status == TaskStatus.SUCCEEDED
    assert found.ldap_fetch_count == 5
    with pytest.raises(AssertionError):
        found.set_succeeded(1, 2, 3, 4)
