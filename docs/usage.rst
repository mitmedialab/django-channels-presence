Usage
=====

In ``django-channels-presence``, two main models track the presence of channels in a room:

 - ``Room``: represents a collection of channels that are in the same "room".  It
   has a single property, ``channel_name``, which is the name of the channels
   `Group <http://channels.readthedocs.io/en/latest/getting-started.html#groups>`_ to which its members are added.
 - ``Presence``: represents an association of a single reply channel with a
   ``Room``, as well as the associated auth ``User`` if any.

To keep track of presence, the following steps need to be taken:

 1. Add channels to a ``Room`` when users successfully join.
 2. Remove channels from the ``Room`` when users leave or disconnect.
 3. Periodically update the ``last_seen`` timestamp for clients' ``Presence``.
 4. Prune stale ``Presence`` records that have old timestamps by running periodic
    tasks.
 5. Listen for changes in presence to update application state or notify other
    users

1. Adding channels to rooms
----------------------------

Add a user to a ``Room`` using the manager ``add`` method.  For example, this handler
for ``websocket.connect`` adds the connecting user to a room on connection.  This
will trigger the ``channels_presence.signals.presence_changed`` signal::

    from channels_presence.models import Room
    from channels.auth import channel_session_user

    @channel_session_user
    def handle_ws_connect(message):
        Room.objects.add("some_room", message.reply_channel.name, message.user)

This example uses the `channel_session_user <http://channels.readthedocs.io/en/latest/getting-started.html?highlight=channel_session_user#authentication>`_ decorator provided by Django
Channels to associate the socket with a user.  However, this is optional --
members of rooms need not be authenticated users.

Channels could be added to a room at any stage -- during handling of
``websocket.connect``, or during handling of a ``websocket.receive`` message, or
wherever else makes sense.  In addition to handling ``Room`` and ``Presence``
models, ``Room.objects.add`` takes care of adding the reply channel to the named
``channels.Group``.

2. Removing channels from rooms
-------------------------------

Remove a user from a Room using the manager ``remove`` method.  For example, this
handler for ``websocket.disconnect`` removes the user from the room on
disconnect.  This will trigger the ``presence_changed`` signal::

    from channels_presence.models import Room

    def handle_ws_disconnect(message):
        Room.objects.remove("some_room", message.reply_channel.name)

``Room.objects.remove`` takes care of removing the specified reply channel from
the ``channels.Group``.

3. Updating the "last_seen" timestamp
-------------------------------------

In order to keep track of which sockets are actually still connected, we must
regularly update the ``last_seen`` timestamp for all present connections, and
periodically remove connections from rooms if they haven't been seen in a
while.

To update timestamps for connections, use the
``channels_presence.decorators.touch_presence`` decorator on some method that
processes messages::

    from channels_presence.decorators import touch_presence    

    # handler for "websocket.receive"

    @touch_presence
    def ws_receive(message):
        ...

This will update the ``last_seen`` timestamp any time any message is received
from the client.  To ensure that the timestamp remains current, clients should
send a periodic "heartbeat" message if they aren't otherwise sending data but
should be considered to still be present.

To allow efficient updates, if a client sends a message which is just the JSON
encoded string ``"heartbeat"``, the ``touch_presence`` decorator will stop
processing of the message after updating the timestamp.  The decorator can be
placed first in a decorator chain in order to stop processing of heartbeat
messages prior to other costly steps like loading session data or user models.

If updating ``last_seen`` on every message is too costly, an alternative to using
the ``touch_presence`` decorator is to manually call ``Presence.objects.touch``
whenever desired.  For example, this updates ``last_seen`` only when the literal message ``"heartbeat"`` is received::

    from channels_presence.models import Presence

    def ws_receive(message):
        ...
        if message.content('text') == '"heartbeat"':
            Presence.objects.touch(message.reply_channel.name)

To ensure that an active connection is not marked as stale, clients should
occasionally send ``"heartbeat"`` messages::

    // client.js

    setInterval(function() {
        socket.send(JSON.stringify("heartbeat"));
    }, 30000);

The frequency should be adjusted to occur before the maximum age for
last-seen presence, set with ``settings.CHANNELS_PRESENCE_MAX_AGE``.

4. Pruning stale connections
----------------------------

In order to remove connections whose timestamps have expired, we need to
periodically launch a cleaning task.  This can be accomplished with
``Room.objects.prune_presences()``. For convenience, this is implemented as a
celery task which can be called with celery beat:
``channels_presence.tasks.prune_presence``.  The management command
``./manage.py prune_presence`` is also available for calling from cron.

A second maintenance command, ``Room.objects.prune_rooms()``, removes any ``Room``
models that have no connections.  This is also available as the celery task
``channels_presence.tasks.prune_rooms`` and management command
``./manage.py prune_rooms``.

See the documentation for
`periodic tasks in celery <http://celery.readthedocs.io/en/latest/userguide/periodic-tasks.html>`_ details on configuring celery beat with Django.  Here is one example::

    # settings.py

    CELERYBEAT_SCHEDULE = {
        'prune-presence': {
            'task': 'channels_presence.tasks.prune_presence',
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
to update other connected clients with the list of present users.  For example::

    # app/signals.py

    from django.dispatch import receiver

    from channels_presence.signals import presence_changed
    from channels import Group

    @receiver(presence_changed)
    def broadcast_presence(sender, room, **kwargs):
        # Broadcast the new list of present users to the room.
        Group(room.channel_name).send({
            'text': json.dumps({
                'type': 'presence',
                'payload': {
                    'channel_name': room.channel_name,
                    'members': [user.serialize() for user in room.get_users()],
                    'lurkers': room.get_anonymous_count(),
                }
            })
        })
