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
    Add the given ``user_channel_name`` (e.g. ``consumer.channel_name``) to
    a Room with the name ``room_channel_name``.  If provided, associate the auth
    ``User`` as well.  Creates a new ``Room`` instance if it doesn't exist;
    creates any needed ``Presence`` instance, and updates the channels group
    membership.  Returns the ``room`` instance.

``Room.objects.remove(room_channel_name, user_channel_name)``
    Remove the given ``user_channel_name`` from the room with
    ``room_channel_name``. Removes relevant ``Presence`` instances, and updates
    the channels group membership.

``Room.objects.prune_presences(age_in_seconds=None)``
    Remove any ``Presence`` models whose ``last_seen`` timestamp is older than
    ``age_in_seconds`` (defaults to ``settings.CHANNELS_PRESENCE_MAX_AGE`` if
    not specified).

``Room.objects.prune_rooms()``
    Remove any rooms that have no associated ``Presence`` models.
  
**Instance properties**:

``room.channel_name``
    The channel name associated with the group for this room.

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
    The consumer channel name associated with this Presence

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
function.  Note that this decorator is syncronous, so should only be used on
syncronous handlers.

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer

    class MyConsumer(WebsocketConsumer):
        @touch_presence
        def receive(self, text_data=None, bytes_data=None):
            pass


``remove_presence``
------------------------------------------------

.. code-block:: python

    from chanels_presence.decorators import remove_presence

Decorator for use on ``websocket.disconnect`` handlers which removes any
``Presence`` instances associated with the client. Note that this decorator is
syncronous, so should only be used on syncronous handlers.

.. code-block:: python

    from channels.generic.websocket import WebsocketConsumer

    class MyConsumer(WebsocketConsumer):
        @remove_presence
        def disconnect(self, close_code):
            pass

Signals
~~~~~~~

``presence_changed``
----------------------------------------------

.. code-block:: python

    from channels_presence.signals import presence_changed

A Django signal dispatched on any addition or removal of a ``Presence`` from a
``Room``.  Use it to track when users come and go.

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

Example:

.. code-block:: python

    # app/signals.py

    import json

    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from channels_presence.signals import presence_changed
    from django.dispatch import receiver


    channel_layer = get_channel_layer()

    @receiver(presence_changed)
    def broadcast_presence(sender, room, **kwargs):
        """
        Broadcast the new list of present users to the room.
        """

        message = {
          "type": "presence",
          "payload": {
              "channel_name": room.channel_name,
              "members": [user.serialize() for user in room.get_users()],
              "lurkers": room.get_anonymous_count(),
          }
        }

        # Prepare a dict for use as a channel layer message. Here, we're using
        # the type "forward.message", which will magically dispatch to the
        # channel consumer as a call to the `forward_message` method.
        channel_layer_message = {
            "type": "forward.message",
            "message": json.dumps(message)
        }

        async_to_sync(channel_layer.group_send)(room.channel_name, channel_layer_message)

.. code-block:: python

    # app/channels.py: App consumer definition

    from channels.generic.websocket import WebsocketConsumer

    class AppConsumer(WebsocketConsumer):
        def forward_message(self, event):
            """
            Utility handler for messages to be broadcasted to groups.  Will be
            called from channel layer messages with `"type": "forward.message"`.
            """
            self.send(event["message"])


