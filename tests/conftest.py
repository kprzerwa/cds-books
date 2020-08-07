# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# CDS Books is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Common pytest fixtures and plugins."""

from __future__ import absolute_import, print_function

import pytest
from invenio_accounts.models import User
from invenio_app_ils.acquisition.api import (
    ORDER_PID_TYPE,
    VENDOR_PID_TYPE,
    Order,
    Vendor,
)
from invenio_app_ils.document_requests.api import (
    DOCUMENT_REQUEST_PID_TYPE,
    DocumentRequest,
)
from invenio_app_ils.documents.api import DOCUMENT_PID_TYPE, Document
from invenio_app_ils.eitems.api import EITEM_PID_TYPE, EItem
from invenio_app_ils.ill.api import (
    BORROWING_REQUEST_PID_TYPE,
    LIBRARY_PID_TYPE,
    BorrowingRequest,
    Library,
)
from invenio_app_ils.internal_locations.api import (
    INTERNAL_LOCATION_PID_TYPE,
    InternalLocation,
)
from invenio_app_ils.items.api import ITEM_PID_TYPE, Item
from invenio_app_ils.locations.api import LOCATION_PID_TYPE, Location
from invenio_app_ils.series.api import SERIES_PID_TYPE, Series
from invenio_circulation.api import Loan
from invenio_circulation.pidstore.pids import CIRCULATION_LOAN_PID_TYPE
from invenio_indexer.api import RecordIndexer
from invenio_oauthclient.models import RemoteAccount, UserIdentity
from invenio_search import current_search
from invenio_userprofiles.models import UserProfile
from tests.helpers import load_json_from_datadir, mint_record_pid


@pytest.fixture()
def system_user(app, db):
    """Create a regular system user."""
    user = User(**dict(email="system_user@cern.ch", active=True))
    db.session.add(user)
    db.session.commit()

    user_id = user.id

    identity = UserIdentity(**dict(id="1", method="cern", id_user=user_id))
    db.session.add(identity)

    profile = UserProfile(
        **dict(
            user_id=user_id,
            _displayname="id_" + str(user_id),
            full_name="System User",
        )
    )
    db.session.add(profile)

    remote_account = RemoteAccount(
        client_id="CLIENT_ID",
        **dict(
            user_id=user_id,
            extra_data=dict(person_id="1", department="Department"),
        )
    )
    db.session.add(remote_account)
    db.session.commit()
    return user


def _create_records(db, objs, cls, pid_type):
    """Create records and index."""
    recs = []
    for obj in objs:
        record = cls.create(obj)
        mint_record_pid(pid_type, "pid", record)
        record.commit()
        recs.append(record)
    db.session.commit()
    return recs


@pytest.fixture()
def testdata(app, db, es_clear):
    """Create, index and return test data."""

    data = load_json_from_datadir("locations.json")
    locations = _create_records(db, data, Location, LOCATION_PID_TYPE)

    data = load_json_from_datadir("internal_locations.json")
    int_locs = _create_records(
        db, data, InternalLocation, INTERNAL_LOCATION_PID_TYPE
    )

    # index
    ri = RecordIndexer()
    for rec in locations + int_locs:
        ri.index(rec)

    current_search.flush_and_refresh(index="*")

    return {
        "internal_locations": int_locs,
        "locations": locations,
    }
