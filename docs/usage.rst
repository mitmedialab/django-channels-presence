Usage
=====

In `django-channels-presence`, two main models track the presence of channels in a room:

 - `Room`: represents a group of channels for which you want to track presence.
   It has a single property, `channel_name`, which is the name of the channels
   `Group` to which its members are added.
 - `Presence`: represents an association of a single reply channel with a `Room`.

To keep track of presence, the following 4 steps need to be taken:

 1. Add channels to rooms when users successfully join.
 2. Remove channels from rooms when users leave or disconnect.
 3. Periodically update the `last_seen` timestamp for users' Presence.
 4. Prune stale `Presence` records that have old timestamps.

1. Adding channels to rooms
----------------------------

Add a user to a `Room` using the manager `add` method.  For example, this handler
for `websocket.connect` adds the connecting user to a room.  This will trigger
the `presence_changed` signal:

::
    from channels_presence.models import Room
    from channels.auth import channel_session_user

    @channel_session_user
    def handle_ws_connect(message):
        Room.objects.add("some_room", message.reply_channel.name, message.user)

This example uses the `channel_session_user` decorator provided by Django
Channels to associate the socket with a user.  However, this is optional --
members of rooms need not be authenticated users.

Channels could be added to a room at any stage -- during handling of
`websocket.connect`, or during handling of a `websocket.receive` message, or
wherever makes sense.

2. Removing channels from rooms
-------------------------------

Remove a user from a Room using the manager `remove` method.  For example, this
handler for `websocket.disconnect` removes the user from the room on
disconnect.  This will trigger the `presence_changed` signal:

::
    from channels_presence.models import Room

    def handle_ws_disconnect(message):
        Room.objects.remove("some_room", message.reply_channel.name)

3. Updating the "last seen" timestamp
-------------------------------------

In order to keep track of which sockets are actually still connected, we must
update the `last_seen` timestamp for all present connections, and periodically
remove connections from rooms if they haven't been seen in a while.

To update timestamps for connections, use the
`channels_presence.signals.touch_presence` decorator on a method that processes
messages:

::
    from channels_presence.decorators import touch_presence    

    # handler for "websocket.receive"

    @touch_presence
    def ws_receive(message, data):
        ...

This will update the `last_seen` timestamp any time any message is received
from the client.  To ensure that the timestamp remains current, clients should
send a periodic "heartbeat" message if they aren't otherwise sending data but
should be considered to still be present.

To allow efficient updates, if a client sends a message which is just the JSON
encoded string `"heartbeat"`, the `touch_presence` decorator will stop
processing of the message after updating the timestamp.  The decorator can be
placed first in a decorator chain in order to stop processing of heartbeat
messages prior to other costly steps like loading session data or user models.

4. Pruning stale connections
----------------------------

In order to remove connections whose timestamps have expired, we need to
periodically launch a cleaning task.  This can be accomplished with
`Room.objects.prune_presences()`. For convenience, this is implemented as both
a celery task which can be called with celery beat
(`channels_presence.tasks.prune_presence`), and as a management command
(`./manage.py prune_presence`).

A second maintenance command, `Room.objects.prune_rooms()`, removes any `Room`
models that have no connections.  This is also available as the celery task
`channels_presence.tasks.prune_rooms` and management command
`./manage.py prune_rooms`.

Listening for changes in presence
---------------------------------

Use the `channels_presence.signals.presence_changed` signal to be notified when
a user is added or removed from a Room.  This is a useful place to define logic
to update other connected clients with the list of present users.  For example:

::
    # app/signals.py

    from django.dispatch import receiver

    from channels_presence.signals import presence_changed
    from channels import Group

    @receiver(presence_changed)
    def broadcast_presence(sender, room, **kwargs):
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

