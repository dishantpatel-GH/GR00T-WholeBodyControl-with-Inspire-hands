"""Server for streaming hand tracking data from a separate Pico device.

This server connects to a different Pico controller and streams only hand tracking data
(left/right hand joints) via ZMQ. This allows simultaneous control of arms/lower body
with one Pico and hands with another Pico.
"""

import pickle
import time
from contextlib import contextmanager

import click
import numpy as np
from scipy.spatial.transform import Rotation as R
import zmq

from gr00t_wbc.control.teleop.device.pico.xr_client import XrClient

R_HEADSET_TO_WORLD = np.array(
    [
        [0, 0, -1],
        [-1, 0, 0],
        [0, 1, 0],
    ]
)


class PicoHandTrackingServer:
    """Server that streams hand tracking data from a Pico device via ZMQ."""

    def __init__(self, port=5557):
        """Initialize the server.
        
        Args:
            port: ZMQ port to bind to (default: 5557, different from manus port 5556)
        """
        self.port = port
        self.xr_client = None
        self.context = None
        self.socket = None
        self.pico_service_pid = None

    def _run_pico_service(self):
        """Run the Pico service in a subprocess."""
        import subprocess
        self.pico_service_pid = subprocess.Popen(
            ["bash", "/opt/apps/roboticsservice/runService.sh"]
        )
        print(f"Pico service running with pid {self.pico_service_pid.pid}")

    def _stop_pico_service(self):
        """Stop the Pico service."""
        if self.pico_service_pid:
            import subprocess
            subprocess.Popen(["kill", "-9", str(self.pico_service_pid.pid)])
            print(f"Pico service killed with pid {self.pico_service_pid.pid}")

    def _get_hand_tracking_data(self):
        """Get hand tracking data from the Pico device.
        
        Returns:
            dict: Dictionary containing left/right hand joints and headset pose
        """
        # Get headset pose (needed for coordinate transformation)
        headset_pose = self.xr_client.get_pose_by_name("headset")
        
        # Get hand tracking states
        left_hand_tracking_state = self.xr_client.get_hand_tracking_state("left")
        right_hand_tracking_state = self.xr_client.get_hand_tracking_state("right")
        
        # Get hand joint locations
        left_hand_joints = None
        right_hand_joints = None
        
        try:
            left_hand_joints = self.xr_client.get_hand_joint_locations("left")
            right_hand_joints = self.xr_client.get_hand_joint_locations("right")
        except Exception as e:
            print(f"Error getting hand joints: {e}")
        
        return {
            "headset_pose": headset_pose,
            "left_hand_tracking_state": left_hand_tracking_state,
            "right_hand_tracking_state": right_hand_tracking_state,
            "left_hand_joints": left_hand_joints,
            "right_hand_joints": right_hand_joints,
            "timestamp": time.time(),
        }

    @contextmanager
    def activate(self):
        """Context manager for server activation."""
        try:
            # Initialize XR client
            self.xr_client = XrClient()
            print("Pico XR client initialized for hand tracking server")
            
            # Run Pico service
            self._run_pico_service()
            time.sleep(2)  # Give service time to start
            
            # Setup ZMQ server
            self.context = zmq.Context()
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            print(f"Pico hand tracking server bound to port {self.port}")
            
            yield self
        finally:
            # Cleanup
            if self.socket:
                self.socket.close()
            if self.context:
                self.context.term()
            if self.xr_client:
                self.xr_client.close()
            self._stop_pico_service()
            print("Pico hand tracking server stopped")

    def run(self):
        """Run the server loop."""
        print("Pico hand tracking server running. Waiting for requests...")
        while True:
            try:
                # Wait for a request from the client
                _ = self.socket.recv()
                
                # Get hand tracking data
                data = self._get_hand_tracking_data()
                
                # Serialize and send the data
                serialized_data = pickle.dumps(data)
                self.socket.send(serialized_data)
                
            except KeyboardInterrupt:
                print("\nShutting down server...")
                break
            except Exception as e:
                print(f"Error in server loop: {e}")
                # Send error response
                error_data = {"error": str(e), "timestamp": time.time()}
                self.socket.send(pickle.dumps(error_data))


@click.command()
@click.option("--port", type=int, default=5557, help="ZMQ port to bind to (default: 5557)")
@click.option("--host", type=str, default="*", help="Host to bind to (default: * for all interfaces)")
def main(port, host):
    """Run the Pico hand tracking server.
    
    The server binds to all interfaces (*) by default, allowing remote connections.
    To find your IP address for clients to connect:
        Linux/Mac: hostname -I or ifconfig
        Windows: ipconfig
    """
    print(f"Starting Pico hand tracking server on {host}:{port}...")
    server = PicoHandTrackingServer(port=port)
    print("Activating server...")
    with server.activate():
        # Get local IP for display
        import socket
        try:
            # Connect to a dummy address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"==> Pico hand tracking server is running")
            print(f"==> Listening on all interfaces (0.0.0.0:{port})")
            print(f"==> Clients can connect to: {local_ip}:{port}")
        except Exception:
            print(f"==> Pico hand tracking server is running at port {port}")
        server.run()


if __name__ == "__main__":
    main()
