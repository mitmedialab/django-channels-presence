from django.db import models
from django.conf import settings
from django.utils.encoding  import python_2_unicode_compatible
from django.utils.timezone import now


class PresenceManager(models.Manager):
    def touch(self, channel_name):
        self.filter(channel_name=channel_name).update(last_seen=now())

    def leave_all(self, channel_name):
        for presence in self.select_related('room').filter(channel_name=channel_name):
            room = presence.room
            room.remove_presence(presence=presence)

@python_2_unicode_compatible
class Presence(models.Model):
    room = models.ForeignKey('Room', on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=255,
            help_text="Reply channel for connection that is present")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True)
    last_seen = models.DateTimeField(default=now)

    objects = PresenceManager()

    def __str__(self):
        return self.channel_name

    class Meta:
        unique_together = [('room', 'channel_name')]