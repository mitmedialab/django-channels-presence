API Reference
=============

Settings
~~~~~~~~

``CHANNELS_PRESENCE_MAX_AGE``
    Default ``60``. Maximum age in seconds before a presence is considered
    expired.

Models
~~~~~~

``Room``
---------------------------------

::

    from channels_presence.models import Room

**Manager**:

``Room.objects.add(room_chanel_name, user_channel_name, user=None)``
    Add the given ``user_channel_name`` (e.g. ``message.reply_channel.name``) to
    a Room with the name ``room_channel_name``.  If provided, associate the auth
    ``User`` as well.  Creates a new ``Room`` instance if it doesn't exist;
    creates any needed ``Presence`` instance, and updates the channels
    ``Group``.  Returns the ``room`` instance.

``Room.objects.remove(room_channel_name, user_channel_name)``
    Remove the given ``user_channel_name`` from the room with
    ``room_channel_name``. Removes relevant ``Presence`` instances, and updates
    the channels ``Group``.

``Room.objects.prune_presences(age_in_seconds=None)``
    Remove any ``Presence`` models whose ``last_seen`` timestamp is older than
    ``age_in_seconds`` (defaults to ``settings.CHANNELS_PRESENCE_MAX_AGE`` if
    not specified).

``Room.objects.prune_rooms()``
    Remove any rooms that have no associated ``Presence`` models.
  
**Instance properties**:

``room.channel_name``
    The channels Group name associated with this room.

**Instance methods**:

``room.get_users()``
    Return a queryset with all of the unique authenticated users who are
    present in this room.

``room.get_anonymous_count()``
    Return the number of non-authenticated sockets which are present in this
    room.

``Presence``
-------------------------------------

::

    from channels_presence.models import Presence

**Manager**:

``Presence.objects.touch(channel_name)``
    Updates the ``last_seen`` timestamp to now for all instances with the given
    channel name.

``Presence.objects.leave_all(channel_name)``
    Removes all ``Presence`` instances with the given channel name.  Triggers
    ``channels_presence.signals.presence_changed`` for any changed rooms.

**Instance properties**:

``presence.room``
    The room to which this Presence belongs

``presence.channel_name``
    The reply channel associated with this Presence

``presence.user``
    A ``settings.AUTH_USER_MODEL`` associated with this Presence, or None

``presence.last_seen``
    Timestamp for the last time socket traffic was seen for this presence.

Decorators
~~~~~~~~~~

``touch_presence``
-----------------------------------------------

::

    from chanels_presence.decorators import touch_presence

Decorator for use on ``websocket.receive`` handlers which updates the
``last_seen`` timestamp on any ``Presence`` instances associated with the
client.  If the message being sent is the literal JSON-encoded ``"heartbeat"``,
message processing stops and the decorator does not call the decorated
function.

Example::

    @touch_presence
    def ws_receive(message, *args, **kwargs):
        # ... process any received message except "heartbeat" ...
        pass

``remove_presence``
------------------------------------------------

::

    from chanels_presence.decorators import remove_presence

Decorator for use on ``websocket.disconnect`` handlers which removes any
``Presence`` instances associated with the client.

Example::

    @remove_presence
    def ws_disconnect(message):
        pass

Signals
~~~~~~~

``presence_changed``
----------------------------------------------

::

    from channels_presence.signals import presence_changed

This is sent on any addition or removal of a ``Presence`` from a ``Room``.  Use it
to track when users come and go.

Arguments sent with this signal:

``room``
    The ``Room`` instance from which a ``Presence`` was added or removed.

``added``
    The ``Presence`` instance which was added, or ``None``.

``removed``
    The ``Presence`` instance which was removed, or ``None``.

``bulk_change``
    If ``True``, indicates that this was a bulk change in presence.  More than
    one presence may have been added or removed, and particular instances will
    not be provided in ``added`` or ``removed`` arguments.

Example::

    import json
    from django.dispatch import receiver

    from channels import Group
    from channels_presence.signals import presence_changed

    def broadcast_to_room(room, message):
        Group(room.channel_name).send({
            'text': json.dumps(message)
        })

    @receiver(presence_changed)
    def handle_presence_changed(sender, room, added, removed, bulk_change):
        if added:
            broadcast_to_room({'added': added.channel_name})
        if removed:
            broadcast_to_room({'removed': removed.channel_name})
        if bulk_change:
            broadcast_to_room({'presence': [p.channel_name for p in room.presence_set.all()]})

Convenience
~~~~~~~~~~~

``ws_disconnect``
--------------------------------------------

::

    from channels_presence.channels import ws_disconnect

This is a convenience handler which can be installed to always clean up
presence on disconnect.  Use it if you don't have any other particular logic
that needs to happen on disconnect.

Example in channels routing::

    from channels.routing import route

    channel_routing = [
        route("websocket.disconnect", "channels_presence.channels.ws_disconnect"),
    ]

The implementation is simply::

    # channels_presence/channels.py

    from channels_presence.decorators import remove_presence

    @remove_presence
    def ws_disconnect(message, **kwargs):
        pass
    
