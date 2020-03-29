Usage
=====

Prerequisites
~~~~~~~~~~~~~

Install and set up `django-channels <https://channels.readthedocs.io/en/latest/installation.html>`_ and `channel layers <https://channels.readthedocs.io/en/latest/topics/channel_layers.html>`_.  A
``CHANNEL_LAYERS`` configuration is necessary to enable the use of consumer
``channel_name`` properties, to allow storing groups of channels by name.

Managing presences
~~~~~~~~~~~~~~~~~~


In ``django-channels-presence``, two main models track the presence of channels in a room:

- ``Room``: represents a collection of channels that are in the same "room".  It has a single property, ``channel_name``, which is the "group name" for the `channel layer group <https://channels.readthedocs.io/en/latest/topics/channel_layers.html#groups>`_ to which its members are added.
- ``Presence``: represents an association of a single consumer channel name with a ``Room``, as well as the associated auth ``User`` if any.

To keep track of presence, the following steps need to be taken:

1. Add channels to a ``Room`` when users successfully join.
2. Remove channels from the ``Room`` when users leave or disconnect.
3. Periodically update the ``last_seen`` timestamp for clients' ``Presence``.
4. Prune stale ``Presence`` records that have old timestamps by running periodic tasks.
5. Listen for changes in presence to update application state or notify other users

1. Adding channels to rooms
----------------------------

Add a user to a ``Room`` using the manager ``add`` method.  For example, this
consumer adds the connecting user to a room on connection.  This will trigger the `channels_presence.signals.presence_changed <api.html#signals>`_ signal:

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.models import Room

    class MyConsumer(WebsocketConsumer):
        def connect(self):
            super().connect()
            Room.objects.add("some_room", self.channel_name, self.scope["user"])


Channel names could be added to a room at any stage -- for example, in the
``connect`` handler, the ``receive`` handler, or
wherever else makes sense.  In addition to handling ``Room`` and ``Presence``
models, ``Room.objects.add`` takes care of adding the channel name to the named
channel layer group.

2. Removing channels from rooms
-------------------------------

Remove a consumer's channel from a Room using the manager ``remove`` method.
For example, this handler for ``disconnect`` removes the user from the room on
disconnect.  This will trigger the ``presence_changed`` signal:

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.models import Room

    class MyConsumer(WebsocketConsumer):
        def disconnect(self, close_code):
            Room.objects.remove("some_room", self.channel_name)

``Room.objects.remove`` takes care of removing the specified channel name from
the channels group.

For convenience, ``channels_presence.decorators.remove_presence`` is a decorator to accomplish the same thing:

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.decorators import remove_presence

    class MyConsumer(WebsocketConsumer):
        @remove_presence
        def disconnect(self, close_code):
            pass


3. Updating the "last_seen" timestamp
-------------------------------------

In order to keep track of which sockets are actually still connected, we must
regularly update the ``last_seen`` timestamp for all present connections, and
periodically remove connections from rooms if they haven't been seen in a
while.

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.models import Presence

    class MyConsumer(WebsocketConsumer):
        def receive(self, close_code):
            Presence.objects.touch(self.channel_name)

For convenience, the ``channels_presence.decorators.touch_presence`` decorator accomplishes the same thing:

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.decorators import touch_presence    

    # handler for "websocket.receive"

    class MyConsumer(WebsocketConsumer):
        @touch_presence
        def receive(self, text_data=None, bytes_data=None):
            ...

This will update the ``last_seen`` timestamp any time any message is received
from the client.  To ensure that the timestamp remains current, clients should
send a periodic "heartbeat" message if they aren't otherwise sending data but
should be considered to still be present.

3a. Heartbeats
++++++++++++++

To allow efficient updates, if a client sends a message which is just the JSON
encoded string ``"heartbeat"``, the ``touch_presence`` decorator will stop
processing of the message after updating the timestamp.  The decorator can be
placed first in a decorator chain in order to stop processing of heartbeat
messages prior to other costly steps.

If updating ``last_seen`` on every message is too costly, an alternative to
using the ``touch_presence`` decorator is to manually call
``Presence.objects.touch`` whenever desired.  For example, this updates
``last_seen`` only when the literal message ``"heartbeat"`` is received:

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer
    from channels_presence.models import Presence

    class MyConsumer(WebsocketConsumer):
        def receive(self, text_data=None, bytes_data=None):
            ...
            if text_data == '"heartbeat"':
                Presence.objects.touch(self.channel_name)

To ensure that an active connection is not marked as stale, clients should
occasionally send ``"heartbeat"`` messages:

.. code-block:: javascript

    // client.js

    setInterval(function() {
        socket.send(JSON.stringify("heartbeat"));
    }, 30000);

The frequency should be adjusted to occur before the maximum age for
last-seen presence, set with ``settings.CHANNELS_PRESENCE_MAX_AGE`` (default 60
seconds).

4. Pruning stale connections
----------------------------

In order to remove connections whose timestamps have expired, we need to
periodically launch a cleaning task.  This can be accomplished with
``Room.objects.prune_presences()``. For convenience, this is implemented as a
celery task which can be called with celery beat:
``channels_presence.tasks.prune_presences``.  The management command
``./manage.py prune_presences`` is also available for calling from cron.

A second maintenance command, ``Room.objects.prune_rooms()``, removes any ``Room``
models that have no connections.  This is also available as the celery task
``channels_presence.tasks.prune_rooms`` and management command
``./manage.py prune_rooms``.

See the documentation for
`periodic tasks in celery <http://celery.readthedocs.io/en/latest/userguide/periodic-tasks.html>`_ details on configuring celery beat with Django.  Here is one example:

.. code-block:: python

    # settings.py

    CELERYBEAT_SCHEDULE = {
        'prune-presence': {
            'task': 'channels_presence.tasks.prune_presences',
            'schedule': timedelta(seconds=60)
        },
        'prune-rooms': {
            'task': 'channels_presence.tasks.prune_rooms',
            'schedule': timedelta(seconds=600)
        }
    }
    

5. Listening for changes in presence
------------------------------------

Use the ``channels_presence.signals.presence_changed`` signal to be notified when
a user is added or removed from a Room.  This is a useful place to define logic
to update other connected clients with the list of present users.  See the
`API reference for presence_changed <api.html#signals>`_ for an example.
