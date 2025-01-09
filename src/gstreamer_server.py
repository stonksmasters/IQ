import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_gstreamer_pipeline(host="0.0.0.0", port=5000, width=640, height=480, framerate=30, bitrate=1000):
    """
    Launches a GStreamer pipeline that captures from the Pi camera (libcamerasrc),
    encodes to H.264, and sends it over UDP to `host:port`. 
    This is a minimal example, you might adapt for RTSP, etc.
    """
    Gst.init(None)  # Initialize GStreamer

    pipeline_str = (
        f"libcamerasrc ! "
        f"video/x-raw,width={width},height={height},framerate={framerate}/1 ! "
        f"videoconvert ! "
        f"x264enc tune=zerolatency speed-preset=ultrafast bitrate={bitrate} ! "
        f"h264parse ! rtph264pay config-interval=1 pt=96 ! "
        f"udpsink host={host} port={port}"
    )

    pipeline = Gst.parse_launch(pipeline_str)
    logger.info("Starting GStreamer pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    bus = pipeline.get_bus()
    loop = GLib.MainLoop()

    def on_message(bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Gstreamer ERROR: {err} {debug}")
            pipeline.set_state(Gst.State.NULL)
            loop.quit()
        elif t == Gst.MessageType.EOS:
            logger.info("End-Of-Stream reached")
            pipeline.set_state(Gst.State.NULL)
            loop.quit()

    bus.add_signal_watch()
    bus.connect("message", on_message)

    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping GStreamer pipeline.")
        pipeline.set_state(Gst.State.NULL)
