# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2019-2020 CERN.
#
# CDS-ILS is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CDS-ILS migrator API."""

import json
import logging

import click
from elasticsearch_dsl import Q
from invenio_app_ils.proxies import current_app_ils
from invenio_db import db
from invenio_pidstore.errors import PIDDoesNotExistError

from cds_ils.literature.api import get_record_by_legacy_recid
from cds_ils.migrator.api import import_record, model_provider_by_rectype
from cds_ils.migrator.documents.api import get_document_by_barcode, \
    get_document_by_legacy_recid
from cds_ils.migrator.errors import DocumentMigrationError, ItemMigrationError
from cds_ils.migrator.internal_locations.api import \
    get_internal_location_by_legacy_recid
from cds_ils.migrator.utils import clean_item_record

migrated_logger = logging.getLogger("migrated_records")
error_logger = logging.getLogger("records_errored")


def set_internal_location_pid(record):
    """Set internal location pid for item."""
    # find internal location
    int_loc_pid_value = get_internal_location_by_legacy_recid(
        record["id_crcLIBRARY"]
    ).pid.pid_value

    record["internal_location_pid"] = int_loc_pid_value


def set_document_pid(record):
    """Set document pid for item."""
    document_cls = current_app_ils.document_record_cls

    # find document
    record["document_pid"] = None
    try:

        record["document_pid"] = get_record_by_legacy_recid(
            document_cls, record["id_bibrec"]
        ).pid.pid_value
    except DocumentMigrationError:
        error_logger.error(
            "ITEM: {0} ERROR: Document {1} not found".format(
                record["barcode"], record["id_bibrec"]
            )
        )
        record["document_pid"] = None
        # try to match by barcodes in volumes of the multiparts
    if not record["document_pid"]:
        try:
            record["document_pid"] = get_document_by_barcode(
                record["barcode"], record["id_bibrec"]
            ).pid.pid_value
        except PIDDoesNotExistError as e:
            error_logger.error(
                "ITEM: {0} ERROR: Document {1} not found".format(
                    record["barcode"], record["id_bibrec"]
                )
            )
            raise e


def import_items_from_json(dump_file, rectype="item"):
    """Load items from json file."""
    dump_file = dump_file[0]
    model, provider = model_provider_by_rectype(rectype)

    with click.progressbar(json.load(dump_file)) as bar:
        for record in bar:
            click.echo(
                'Importing item "{0}({1})"...'.format(
                    record["barcode"], rectype
                )
            )

            set_internal_location_pid(record)

            try:
                set_document_pid(record)
            except PIDDoesNotExistError:
                continue

            # clean the item JSON
            try:
                clean_item_record(record)
            except ItemMigrationError as e:
                click.secho(str(e), fg="red")
                error_logger.error(
                    "ITEM: {0} ERROR: {1}".format(record["barcode"], str(e))
                )
                continue
            try:
                # check if the item already there
                item = get_item_by_barcode(record["barcode"])
                if item:
                    click.secho(
                        "Item {0}) already exists with pid: {1}".format(
                            record["barcode"], item.pid
                        ),
                        fg="blue",
                    )
                    continue
            except ItemMigrationError:
                try:
                    import_record(
                        record, model, provider, legacy_id_key="barcode"
                    )
                    db.session.commit()
                    migrated_logger.warning(
                        "ITEM: {0} OK".format(record["barcode"])
                    )
                except Exception as e:
                    error_logger.error(
                        "ITEM: {0} ERROR: {1}".format(
                            record["barcode"], str(e)
                        )
                    )
                    db.session.rollback()


def get_item_by_barcode(barcode):
    """Retrieve item object by barcode."""
    search = current_app_ils.item_search_cls().query(
        "bool",
        filter=[
            Q("term", barcode=barcode),
        ],
    )
    result = search.execute()
    hits_total = result.hits.total.value
    if not result.hits or hits_total < 1:
        click.secho("no item found with barcode {}".format(barcode), fg="red")
        raise ItemMigrationError(
            "no item found with barcode {}".format(barcode)
        )
    elif hits_total > 1:
        raise ItemMigrationError(
            "found more than one item with barcode {}".format(barcode)
        )
    else:
        return current_app_ils.item_record_cls.get_record_by_pid(
            result.hits[0].pid
        )
