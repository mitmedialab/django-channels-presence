import functools

from channels_presence.models import Presence


def touch_presence(func):
    @functools.wraps(func)
    def inner(consumer, text_data, *args, **kwargs):
        Presence.objects.touch(consumer.channel_name)
        if text_data == '"heartbeat"':
            return
        return func(consumer, text_data, *args, **kwargs)

    return inner


def remove_presence(func):
    @functools.wraps(func)
    def inner(consumer, *args, **kwargs):
        Presence.objects.leave_all(consumer.channel_name)
        return func(consumer, *args, **kwargs)

    return inner
