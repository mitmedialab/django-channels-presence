from __future__ import unicode_literals

import functools
from channels_presence.models.Presence import Presence


def touch_presence(func):
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        Presence.objects.touch(message.reply_channel.name)
        if message.content.get('text') == '"heartbeat"':
            return
        return func(message, *args, **kwargs)
    return inner

def remove_presence(func):
    @functools.wraps(func)
    def inner(message, *args, **kwargs):
        Presence.objects.leave_all(message.reply_channel.name)
        return func(message, *args, **kwargs)
    return inner

def generic_touch_presence(func):
    @functools.wraps(func)
    def inner(cls_obj, content, **kwargs):
        Presence.objects.touch(cls_obj.message.reply_channel.name)

        if content.get('text') == '"heartbeat"':
            return
        elif content['text']['type'] == 'heartbeat':
            return
        return func(cls_obj, content, **kwargs)
    return inner

def generic_remove_presence(func):
    @functools.wraps(func)
    def inner(cls_obj, content, **kwargs):
        Presence.objects.leave_all(cls_obj.message.reply_channel.name)
        return func(cls_obj, content, **kwargs)
    return inner
