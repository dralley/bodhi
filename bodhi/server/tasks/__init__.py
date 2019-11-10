# Copyright © 2019 Red Hat, Inc. and others.
#
# This file is part of Bodhi.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""Asynchronous tasks for Bodhi."""

import logging
import sys

import celery

from bodhi.server import bugs, buildsys, initialize_db
from bodhi.server.config import config
from bodhi.server.util import pyfile_to_module


# Workaround https://github.com/celery/celery/issues/5416
if celery.version_info < (4, 3) and sys.version_info >= (3, 7):  # pragma: no cover
    from re import Pattern
    from celery.app.routes import re as routes_re
    routes_re._pattern_type = Pattern

log = logging.getLogger('bodhi')

# The Celery app object.
app = celery.Celery()
app.config_from_object(pyfile_to_module(config["celery_config"], "celeryconfig"))


def _do_init():
    config.load_config()
    initialize_db(config)
    buildsys.setup_buildsystem(config)
    bugs.set_bugtracker()


@app.task(name="compose")
def compose(api_version: int, **kwargs):
    """Trigger the compose.

    All arguments besides the ``api_version`` will be transmitted to the task handler.

    Args:
        api_version: Version of the task API. Change it if the handling of the
            arguments have changed in the task handler.
    """
    # Import here to avoid an import loop.
    # The compose task is routed independently in the configuration, therefore
    # the task will not be attempted on a host that does not have the composer
    # installed.
    from bodhi.server.tasks.composer import ComposerHandler
    log.info("Received a compose order")
    _do_init()
    composer = ComposerHandler()
    composer.run(api_version=api_version, data=kwargs)


@app.task(name="handle_update")
def handle_update(api_version: int, **kwargs):
    """Trigger the Updates handler.

    All arguments besides the ``api_version`` will be transmitted to the task handler.

    Args:
        api_version: Version of the task API. Change it if the handling of the
            arguments have changed in the task handler.
    """
    from .updates import UpdatesHandler  # Avoid an import loop
    log.info("Received an update handling order")
    _do_init()
    handler = UpdatesHandler()
    handler.run(api_version=api_version, data=kwargs)
