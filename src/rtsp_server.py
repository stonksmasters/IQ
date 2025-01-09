import gi
print("PyGObject installed successfully!")

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib


class RTSPServer:
    def __init__(self):
        self.server = GstRtspServer.RTSPServer()

        # Factory setup
        self.factory = GstRtspServer.RTSPMediaFactory()
        self.factory.set_launch('( videotestsrc ! x264enc tune=zerolatency ! rtph264pay name=pay0 pt=96 )')
        self.factory.set_shared(True)

        # Attach factory to mount points
        self.server.get_mount_points().add_factory("/test", self.factory)

        # Optionally connect to session or client signals
        self.server.connect("client-connected", self.on_client_connected)

        # Start the server
        self.server.attach(None)
        print("RTSP server is running at rtsp://<your-ip>:8554/test")

    def on_client_connected(self, server, client):
        print("Client connected:", client)

    # To handle session signals
    def on_session_removed(self, session):
        print("Session removed:", session)


Gst.init(None)
server = RTSPServer()
loop = GLib.MainLoop()
loop.run()
