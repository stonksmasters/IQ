import gi
print("PyGObject installed successfully!")

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

class RTSPServer:
    def __init__(self):
        self.server = GstRtspServer.RTSPServer()
        self.factory = GstRtspServer.RTSPMediaFactory()
        self.factory.set_launch('( videotestsrc ! x264enc tune=zerolatency ! rtph264pay name=pay0 pt=96 )')
        self.factory.set_shared(True)
        self.server.get_mount_points().add_factory("/test", self.factory)
        self.server.attach(None)

Gst.init(None)
server = RTSPServer()
loop = GLib.MainLoop()  # Updated to use GLib.MainLoop
loop.run()
