import json
from datetime import timedelta

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels_presence.signals import presence_changed

channel_layer = get_channel_layer()


class PresenceManager(models.Manager):
    def touch(self, channel_name):
        self.filter(channel_name=channel_name).update(last_seen=now())

    def leave_all(self, channel_name):
        for presence in self.select_related("room").filter(channel_name=channel_name):
            room = presence.room
            room.remove_presence(presence=presence)


class Presence(models.Model):
    room = models.ForeignKey("Room", on_delete=models.CASCADE)
    channel_name = models.CharField(
        max_length=255, help_text="Reply channel for connection that is present"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    last_seen = models.DateTimeField(default=now)

    objects = PresenceManager()

    def __str__(self):
        return self.channel_name

    class Meta:
        unique_together = [("room", "channel_name")]


class RoomManager(models.Manager):
    def add(self, room_channel_name, user_channel_name, user=None):
        room, created = Room.objects.get_or_create(channel_name=room_channel_name)
        room.add_presence(user_channel_name, user)
        return room

    def remove(self, room_channel_name, user_channel_name):
        try:
            room = Room.objects.get(channel_name=room_channel_name)
        except Room.DoesNotExist:
            return
        room.remove_presence(user_channel_name)

    def prune_presences(self, channel_layer=None, age=None):
        for room in Room.objects.all():
            room.prune_presences(age)

    def prune_rooms(self):
        Room.objects.filter(presence__isnull=True).delete()


class Room(models.Model):
    channel_name = models.CharField(
        max_length=255, unique=True, help_text="Group channel name for this room"
    )

    objects = RoomManager()

    def __str__(self):
        return self.channel_name

    def add_presence(self, channel_name, user=None):
        if user and user.is_authenticated:
            authed_user = user
        else:
            authed_user = None
        presence, created = Presence.objects.get_or_create(
            room=self, channel_name=channel_name, user=authed_user
        )
        if created:
            async_to_sync(channel_layer.group_add)(self.channel_name, channel_name)
            self.broadcast_changed(added=presence)

    def remove_presence(self, channel_name=None, presence=None):
        if presence is None:
            try:
                presence = Presence.objects.get(room=self, channel_name=channel_name)
            except Presence.DoesNotExist:
                return

        async_to_sync(channel_layer.group_discard)(
            self.channel_name, presence.channel_name
        )
        presence.delete()
        self.broadcast_changed(removed=presence)

    def prune_presences(self, age_in_seconds=None):
        if age_in_seconds is None:
            age_in_seconds = getattr(settings, "CHANNELS_PRESENCE_MAX_AGE", 60)

        num_deleted, num_per_type = Presence.objects.filter(
            room=self, last_seen__lt=now() - timedelta(seconds=age_in_seconds)
        ).delete()
        if num_deleted > 0:
            self.broadcast_changed(bulk_change=True)

    def get_users(self):
        User = get_user_model()
        return User.objects.filter(presence__room=self).distinct()

    def get_anonymous_count(self):
        return self.presence_set.filter(user=None).count()

    def broadcast_changed(self, added=None, removed=None, bulk_change=False):
        presence_changed.send(
            sender=self.__class__,
            room=self,
            added=added,
            removed=removed,
            bulk_change=bulk_change,
        )
