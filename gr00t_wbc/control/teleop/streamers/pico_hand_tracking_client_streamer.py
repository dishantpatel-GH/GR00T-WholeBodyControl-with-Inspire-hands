"""Client streamer for receiving hand tracking data from Pico hand tracking server.

This streamer connects to a Pico hand tracking server (running on a different Pico)
and receives hand tracking data, formatting it for use in the teleop system.
"""

import pickle

import numpy as np
from scipy.spatial.transform import Rotation as R
import zmq

from gr00t_wbc.control.teleop.streamers.base_streamer import BaseStreamer, StreamerOutput

R_HEADSET_TO_WORLD = np.array(
    [
        [0, 0, -1],
        [-1, 0, 0],
        [0, 1, 0],
    ]
)


class PicoHandTrackingClientStreamer(BaseStreamer):
    """Client streamer that receives hand tracking data from Pico hand tracking server."""

    def __init__(self, server_host="localhost", server_port=5557):
        """Initialize the client streamer.
        
        Args:
            server_host: Host where the Pico hand tracking server is running (default: localhost)
            server_port: Port where the server is listening (default: 5557)
        """
        self.server_host = server_host
        self.server_port = server_port
        self.context = None
        self.socket = None

    def start_streaming(self):
        """Start the client and connect to the server."""
        if self.socket is not None:
            return

        print(f"Connecting to Pico hand tracking server at {self.server_host}:{self.server_port}...")
        
        # Setup ZMQ client
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f"tcp://{self.server_host}:{self.server_port}")
        
        # Set socket timeout to avoid blocking forever
        self.socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
        
        print(f"Connected to Pico hand tracking server")

    def _request_data(self):
        """Request hand tracking data from the server.
        
        Returns:
            dict: Hand tracking data dictionary or None if error
        """
        if self.socket is None:
            raise RuntimeError("PicoHandTrackingClientStreamer not started. Call start_streaming() first.")

        try:
            # Send request to the server
            self.socket.send(b"request_data")
            
            # Wait for the server's response
            message = self.socket.recv()
            data = pickle.loads(message)
            
            # Check for error
            if "error" in data:
                print(f"Server error: {data['error']}")
                return None
                
            return data
        except zmq.Again:
            print("Timeout waiting for server response")
            return None
        except Exception as e:
            print(f"Error requesting data from server: {e}")
            return None

    def _generate_finger_data(self, hand_joints, headset_pose, hand_side):
        """Generate finger position data from hand joints.
        
        Args:
            hand_joints: Array of hand joint data [x, y, z, qx, qy, qz, qw] for each joint
            headset_pose: Headset pose [x, y, z, qx, qy, qz, qw]
            hand_side: "left" or "right"
            
        Returns:
            numpy.ndarray: Finger position data as (25, 4, 4) transformation matrices
        """
        # Check if valid joints exist (length >= 25)
        if hand_joints is None or len(hand_joints) < 25:
            # Return zeros if no valid tracking
            return np.zeros([25, 4, 4])
        
        fingertips = np.zeros([25, 4, 4])
        
        # Process Headset Pose
        headset_pose_xyz = np.array(headset_pose[:3])
        headset_pose_quat = np.array(headset_pose[3:])
        
        # Safety check for headset quaternion
        if np.allclose(headset_pose_quat, 0):
            headset_pose_quat = np.array([0, 0, 0, 1])
        
        # Convert Headset to World frame
        h_pos = R_HEADSET_TO_WORLD @ headset_pose_xyz
        h_rot = R.from_quat(headset_pose_quat).as_matrix()
        h_rot = R_HEADSET_TO_WORLD @ h_rot @ R_HEADSET_TO_WORLD.T
        
        # Calculate Inverse Yaw
        headset_yaw = R.from_matrix(h_rot).as_euler("xyz")[2]
        inv_yaw_rot = R.from_euler("z", -headset_yaw).as_matrix()

        # Process each joint (we need 25 joints for fingers)
        num_joints = min(len(hand_joints), 25)
        for i in range(num_joints):
            # Parse joint data
            joint_data = hand_joints[i]
            j_pos_raw = np.array(joint_data[:3])
            j_quat_raw = np.array(joint_data[3:])

            # Handle Zero Norm Quaternions
            if np.allclose(j_quat_raw, 0):
                j_quat_raw = np.array([0, 0, 0, 1])  # Identity quaternion

            # Transform Raw Joint to World (Z-up)
            j_pos = R_HEADSET_TO_WORLD @ j_pos_raw
            j_rot = R.from_quat(j_quat_raw).as_matrix()
            j_rot = R_HEADSET_TO_WORLD @ j_rot @ R_HEADSET_TO_WORLD.T

            # Apply Headset Compensation
            pos_delta = j_pos - h_pos
            pos_final = inv_yaw_rot @ pos_delta
            
            rot_final = inv_yaw_rot @ j_rot

            # Store in matrix
            fingertips[i] = np.eye(4)
            fingertips[i, :3, :3] = rot_final
            fingertips[i, :3, 3] = pos_final
        
        return fingertips

    def get(self) -> StreamerOutput:
        """Get hand tracking data from the server and format as StreamerOutput.
        
        Returns:
            StreamerOutput: Structured output with hand tracking data
        """
        # Request data from server
        server_data = self._request_data()
        
        if server_data is None:
            # Return empty data if server unavailable
            return StreamerOutput(
                ik_data={
                    "left_fingers": {"position": np.zeros([25, 4, 4])},
                    "right_fingers": {"position": np.zeros([25, 4, 4])},
                },
                control_data={},
                teleop_data={},
                data_collection_data={},
                source="pico_hand_tracking",
            )
        
        # Extract data
        headset_pose = server_data.get("headset_pose")
        left_hand_joints = server_data.get("left_hand_joints")
        right_hand_joints = server_data.get("right_hand_joints")
        
        # Generate finger data
        left_fingers = self._generate_finger_data(left_hand_joints, headset_pose, "left")
        right_fingers = self._generate_finger_data(right_hand_joints, headset_pose, "right")
        
        # Return structured output with only hand tracking data
        return StreamerOutput(
            ik_data={
                "left_fingers": {"position": left_fingers},
                "right_fingers": {"position": right_fingers},
            },
            control_data={},  # No control commands from hand tracking
            teleop_data={},  # No teleop commands from hand tracking
            data_collection_data={},  # No data collection commands
            source="pico_hand_tracking",
        )

    def stop_streaming(self):
        """Stop the client and close connections."""
        if self.socket:
            self.socket.close()
            self.socket = None
        
        if self.context:
            self.context.term()
            self.context = None
        
        print("Pico hand tracking client disconnected")

    def reset_status(self):
        """Reset status (no-op for client streamer)."""
        pass
