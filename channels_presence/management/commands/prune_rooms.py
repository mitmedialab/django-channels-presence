from django.core.management.base import BaseCommand
from channels_presence.models import Room

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        Room.objects.prune_rooms()
