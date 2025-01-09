import gi
import os

print("PyGObject installed successfully!")

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib


class RTSPServer:
    def __init__(self):
        # Initialize RTSP server
        self.server = GstRtspServer.RTSPServer()
        self.factory = GstRtspServer.RTSPMediaFactory()

        # Configure the pipeline (default to test pattern; can be changed via an environment variable)
        pipeline = os.getenv(
            "RTSP_PIPELINE",
            "( videotestsrc ! videoconvert ! x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )"
        )
        self.factory.set_launch(pipeline)
        self.factory.set_shared(True)

        # Mount the media factory to /test
        mount_points = self.server.get_mount_points()
        mount_points.add_factory("/test", self.factory)

        # Attach the server to the default main context
        self.server.attach(None)

        print("RTSP server is running at rtsp://<your-ip>:8554/test")

        # Add logging for client connections and disconnections
        self.server.connect("client-connected", self.on_client_connected)
        self.server.connect("client-disconnected", self.on_client_disconnected)

    def on_client_connected(self, server, client):
        print(f"Client connected: {client}")

    def on_client_disconnected(self, server, client):
        print(f"Client disconnected: {client}")


if __name__ == "__main__":
    # Initialize GStreamer
    Gst.init(None)

    # Start the RTSP server
    server = RTSPServer()

    # Run the GLib main loop
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nRTSP server stopped.")
