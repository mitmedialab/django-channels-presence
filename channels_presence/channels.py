from __future__ import unicode_literals

from channels_presence.decorators import remove_presence

@remove_presence
def ws_disconnect(message, **kwargs):
    pass

