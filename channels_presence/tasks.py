from celery import shared_task

from channels_presence.models import Room

@shared_task(name='channels_presence.tasks.prune_presence')
def prune_presence():
    Room.objects.prune_presences()

@shared_task(name='channels_presence.tasks.prune_rooms')
def prune_rooms():
    Room.objects.prune_rooms()
