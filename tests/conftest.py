# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# CDS Books is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Common pytest fixtures and plugins."""

from __future__ import absolute_import, print_function
from __future__ import absolute_import, print_function

import json
import os

import pytest
from invenio_accounts.models import User
from invenio_app.factory import create_api
from invenio_circulation.api import Loan
from invenio_circulation.pidstore.pids import CIRCULATION_LOAN_PID_TYPE
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_oauthclient.models import RemoteAccount, UserIdentity
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_search import current_search
from invenio_userprofiles.models import UserProfile

from invenio_app_ils.documents.api import DOCUMENT_PID_TYPE, Document
from invenio_app_ils.internal_locations.api import INTERNAL_LOCATION_PID_TYPE  # noqa isort:skip
from invenio_app_ils.internal_locations.api import InternalLocation  # noqa isort:skip
from invenio_app_ils.items.api import ITEM_PID_TYPE, Item
from invenio_app_ils.locations.api import LOCATION_PID_TYPE, Location
from invenio_app_ils.series.api import SERIES_PID_TYPE, Series


@pytest.fixture()
def system_user(app, db):
    """Create a regular system user."""
    user = User(**dict(id="1", email="system_user@cern.ch", active=True))
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


def load_json_from_datadir(filename):
    """Load JSON from dir."""
    _data_dir = os.path.join(os.path.dirname(__file__), "data")
    with open(os.path.join(_data_dir, filename), "r") as fp:
        return json.load(fp)


def mint_record_pid(pid_type, pid_field, record):
    """Mint the given PID for the given record."""
    PersistentIdentifier.create(
        pid_type=pid_type,
        pid_value=record[pid_field],
        object_type="rec",
        object_uuid=record.id,
        status=PIDStatus.REGISTERED,
    )
    db.session.commit()


@pytest.fixture()
def testdata(app, db, es_clear, system_user):
    """Create, index and return test data."""
    indexer = RecordIndexer()

    locations = load_json_from_datadir("locations.json")
    for location in locations:
        record = Location.create(location)
        mint_record_pid(LOCATION_PID_TYPE, "pid", record)
        record.commit()
        db.session.commit()
        indexer.index(record)

    internal_locations = load_json_from_datadir("internal_locations.json")
    for internal_location in internal_locations:
        record = InternalLocation.create(internal_location)
        mint_record_pid(
            INTERNAL_LOCATION_PID_TYPE, "pid", record
        )
        record.commit()
        db.session.commit()
        indexer.index(record)

    documents = load_json_from_datadir("documents.json")
    for doc in documents:
        record = Document.create(doc)
        mint_record_pid(DOCUMENT_PID_TYPE, "pid", record)
        record.commit()
        db.session.commit()
        indexer.index(record)

    items = load_json_from_datadir("items.json")
    for item in items:
        record = Item.create(item)
        mint_record_pid(ITEM_PID_TYPE, "pid", record)
        record.commit()
        db.session.commit()
        indexer.index(record)

    loans = load_json_from_datadir("loans.json")
    for loan in loans:
        record = Loan.create(loan)
        mint_record_pid(CIRCULATION_LOAN_PID_TYPE, "pid", record)
        record.commit()
        db.session.commit()
        indexer.index(record)

    series = load_json_from_datadir("series.json")
    for serie in series:
        record = Series.create(serie)
        mint_record_pid(SERIES_PID_TYPE, "pid", record)
        record.commit()
        db.session.commit()
        indexer.index(record)

    # flush all indices after indexing, otherwise ES won't be ready for tests
    current_search.flush_and_refresh(index='*')
    return {
        "documents": documents,
        "items": items,
        "loans": loans,
        "locations": locations,
        "series": series,
    }
