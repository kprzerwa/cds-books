# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2020 CERN.
#
# invenio-app-ils is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Helpers for tests."""

import json
import os

from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus


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
