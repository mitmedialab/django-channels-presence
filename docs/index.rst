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

Upgrading
~~~~~~~~~

Django Channels v2 is a major backwards-incompatible change from Django
Channels v1; and hence the latest django-channels-presence is not
compatible with older versions of django-channels.

If you're using:

- django-channels v1.x: Use django-channels-presence v0.
- django-channels v2.x: Use django-channels-presence v1+.


Code that uses ``django-channels-presence`` v0 or ``django-channels`` v1 will
need to be rewritten to target channel layers, consumers, and other new
concepts from ``django-channels`` v2.

Motivation
~~~~~~~~~~

This application builds on top of
`django-channels <https://github.com/django/channels>`_. You should have a good
understanding of how it works before diving in here.  To enable groups and
messaging by channel name, ``django-channels-presence`` requires that the
optional "channel layers" feature of ``django-channels`` v2 be used.

There are 3 main tasks that need to be accomplished in order to track "presence" in rooms using ``django-channels``:

1. Observe connections, adding the channel names for each connecting socket to a group.
2. Observe disconnections, removing the channel names for each connecting socket from a group.
3. Prune channel names from groups after they go stale. We won't always get a socket disconnect event when a socket drops off; so we need to use heartbeats and a periodic pruning task to remove stale connections.

``django-channels-presence`` provides database models and helpers to handle
each of these tasks.  This implementation makes database queries on every
connection, disconnection, and message, as well as periodic queries to prune
stale connections. As a result, it will scale differently than
``django-channels`` alone.

**Contents**:

.. toctree::
   :maxdepth: 4

   usage
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

