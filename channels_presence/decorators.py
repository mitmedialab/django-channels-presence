from __future__ import unicode_literals

import functools

from asgiref.sync import sync_to_async
from channels_presence.models import Presence

def touch_presence(func):
    @functools.wraps(func)
    async def inner(consumer, msg, *args, **kwargs):
        await sync_to_async(Presence.objects.touch)(consumer.channel_name)
        if msg.get('text') == '"heartbeat"':
            return
        return await func(consumer, msg, *args, **kwargs)
    return inner

def remove_presence(func):
    @functools.wraps(func)
    async def inner(consumer, *args, **kwargs):
        await sync_to_async(Presence.objects.leave_all)(
            consumer.channel_name)
        return await func(consumer, *args, **kwargs)
    return inner
