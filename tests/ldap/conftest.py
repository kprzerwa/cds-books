# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 CERN.
#
# CDS Books is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Pytest fixtures and plugins for the API application."""

from __future__ import absolute_import, print_function

import os

import jinja2
import pytest
from flask import Blueprint
from invenio_app.factory import create_app as _create_app


@pytest.fixture(scope="module")
def create_app():
    """Create test app."""
    return _create_app


@pytest.fixture(scope="module")
def app_with_mail(app):
    """App with email test templates."""
    # app.register_blueprint(
    #     Blueprint(
    #         "invenio_app_ils_tests",
    #         __name__,
    #         template_folder="../cds_books/circulation/templates",
    #     )
    # )
    # add extra test templates to the search app blueprint, to fake the
    # existence of `invenio-theme` base templates.
    test_templates_path = os.path.join(os.path.dirname(__file__), "templates")
    print("PATH:", test_templates_path)
    test_templates_path = "/home/konstantina/Documents/Work/cds-books/cds_books/circulation/templates"
    enhanced_jinja_loader = jinja2.ChoiceLoader(
        [app.jinja_loader, jinja2.FileSystemLoader(test_templates_path),]
    )
    # override default app jinja_loader to add the new path
    app.jinja_loader = enhanced_jinja_loader
    yield app
