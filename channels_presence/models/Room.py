from __future__ import unicode_literals

from datetime import timedelta

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.encoding  import python_2_unicode_compatible
from django.utils.timezone import now
from channels_presence.models.Presence import Presence

from channels_presence.signals import presence_changed

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

@python_2_unicode_compatible
class Room(models.Model):
    channel_name = models.CharField(max_length=255, unique=True,
            help_text="Group channel name for this room")

    objects = RoomManager()

    def __str__(self):
        return self.channel_name

    def add_presence(self, channel_name, user=None):
        from channels import Group
        presence, created = Presence.objects.get_or_create(
            room=self,
            channel_name=channel_name,
            user=user if (user and user.is_authenticated()) else None
        )
        if created:
            Group(self.channel_name).add(channel_name)
            self.broadcast_changed(added=presence)

    def remove_presence(self, channel_name=None, presence=None):
        from channels import Group
        if presence is None:
            try:
                presence = Presence.objects.get(room=self, channel_name=channel_name)
            except Presence.DoesNotExist:
                return
        Group(self.channel_name).discard(presence.channel_name)
        presence.delete()
        self.broadcast_changed(removed=presence)

    def prune_presences(self, age_in_seconds=None):
        if age_in_seconds is None:
            age_in_seconds = getattr(settings, "CHANNELS_PRESENCE_MAX_AGE", 60)

        num_deleted, num_per_type = Presence.objects.filter(
            room=self,
            last_seen__lt=now() - timedelta(seconds=age_in_seconds)
        ).delete()
        if num_deleted > 0:
            self.broadcast_changed(bulk_change=True)

    def get_users(self):
        User = get_user_model()
        return User.objects.filter(presence__room=self).distinct()

    def get_anonymous_count(self):
        return self.presence_set.filter(user=None).count()

    def broadcast_changed(self, added=None, removed=None, bulk_change=False):
        presence_changed.send(sender=self.__class__,
            room=self,
            added=added,
            removed=removed,
            bulk_change=bulk_change)
