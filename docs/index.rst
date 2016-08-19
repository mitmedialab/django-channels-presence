.. django-channels-presence documentation master file, created by
   sphinx-quickstart on Fri Aug 12 11:38:33 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

django-channels-presence
========================

``django-channels-presence`` is a Django app which adds "rooms" and presence
notification capability to a Django application using `django-channels
<https://github.com/andrewgodwin/channels>`_.  If you're building a chat room
or other site that needs to keep track of "who is connected right now", this
might be useful to you.

Quick install
~~~~~~~~~~~~~

1. Install with pip::

    pip install django-channels-presence

2. Add ``"channels_presence"`` to ``INSTALLED_APPS``::

    # proj/settings.py

    INSTALLED_APPS = [
        ...
        "channels_presence",
        ...
    ]

Motivation
~~~~~~~~~~

This application builds on top of
`django-channels <https://github.com/andrewgodwin/channels>`_. You should have
a good understanding of how it works before diving in here -- in particular,
see django-channels'
`concepts <https://channels.readthedocs.io/en/latest/concepts.html>`_.

For efficiency and flexibility with different backends, ``django-channels`` does
not keep careful track of which sockets are currently connected, nor which of
the sockets that have been added to a
`Group <https://channels.readthedocs.io/en/latest/concepts.html#groups>`_ are
still active.  It does provide ``websocket.connect`` hook that fires when a
client first connects, and a ``websocket.disconnect`` that fires if the client
cleanly disconnects.  We can use these hooks to maintain a separate list of
which sockets (and associated users, if any) are connected to a room.  However,
there are two ways that a socket might disconnect *without* firing
``websocket.disconnect``:

 1. The client might drop out without cleanly closing its connection (for
    example, wifi signal or power drops off).
 2. The server holding the socket connections might restart, without running 
    ``websocket.disconnect`` handlers.

Because of these failure modes, we need both a way to track which clients have
been added to a room, and also a way to periodically prune any connections that
have grown stale.  ``django-channels-presence`` provides the first in the form of
database-backed ``Room`` and ``Presence`` models that can be used to track
connections in the ``websocket.connect`` and ``websocket.disconnect`` handlers, and
the second in the form of a periodic task (usable with `celerybeat
<http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html>`_ or
cron) to clean the models up.

This implementation makes database queries on every connection, disconnection,
and message, as well as periodic queries to prune stale connections. As a
result, it will scale differently than ``django-channels`` alone.

**Contents**:

.. toctree::
   :maxdepth: 4

   usage
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

