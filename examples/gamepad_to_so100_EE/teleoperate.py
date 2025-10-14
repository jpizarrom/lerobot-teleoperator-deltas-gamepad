# !/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from dataclasses import dataclass

import numpy as np
import torch

# from lerobot.teleoperators.gamepad.teleop_gamepad import (
#     GamepadTeleop,
#     GamepadTeleopConfig,
# )
from lerobot_teleoperator_deltas_gamepad import (
    DeltasGamepad as GamepadTeleop,
    DeltasGamepadConfig as GamepadTeleopConfig,
)

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.model.kinematics import RobotKinematics
from lerobot.processor import (
    MapDeltaActionToRobotActionStep,
    RobotAction,
    RobotActionProcessorStep,
    RobotObservation,
    RobotProcessorPipeline,
    TransitionKey,
    create_transition,
)
from lerobot.processor.converters import (
    identity_transition,
    transition_to_robot_action,
)
from lerobot.robots.robot import Robot
from lerobot.robots.so100_follower.config_so100_follower import SO100FollowerConfig
from lerobot.robots.so100_follower.robot_kinematic_processor import (
    EEBoundsAndSafety,
    EEReferenceAndDelta,
    GripperVelocityToJoint,
    InverseKinematicsRLStep,
)
from lerobot.robots.so100_follower.so100_follower import SO100Follower
from lerobot.utils.robot_utils import busy_wait
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

FPS = 10

# Initialize the robot and teleoperator config
camera_config = {
    "front": OpenCVCameraConfig(index_or_path=8, width=640, height=480, fps=30, rotation=180),
    "wrist": OpenCVCameraConfig(index_or_path=2, width=640, height=480, fps=30),
}
follower_config = SO100FollowerConfig(
    port="/dev/usb_follower_arm",
    id="main_follower",
    cameras=camera_config,
    use_degrees=True,
)
gamepad_config = GamepadTeleopConfig(use_gripper=True)

# Initialize the robot and teleoperator
follower = SO100Follower(follower_config)
gamepad = GamepadTeleop(gamepad_config)

# NOTE: It is highly recommended to use the urdf in the SO-ARM100 repo: https://github.com/TheRobotStudio/SO-ARM100/blob/main/Simulation/SO101/so101_new_calib.urdf
follower_kinematics_solver = RobotKinematics(
    urdf_path="../SO-ARM100/Simulation/SO101/so101_new_calib.urdf",
    target_frame_name="gripper_frame_link",
    joint_names=list(follower.bus.motors.keys()),
)


@dataclass
class LogRobotAction(RobotActionProcessorStep):
    def action(self, action: RobotAction) -> RobotAction:
        print(f"Robot action: {action}")
        return action

    def transform_features(self, features):
        # features[PipelineFeatureType.ACTION][ACTION] = PolicyFeature(
        #     type=FeatureType.ACTION, shape=(len(self.motor_names),)
        # )
        return features


# build pipeline to convert EE action to robot joints
ee_to_follower_joints = RobotProcessorPipeline[tuple[RobotAction, RobotObservation], RobotAction](
    [
        LogRobotAction(),
        MapDeltaActionToRobotActionStep(use_rotation=True),
        LogRobotAction(),
        EEReferenceAndDelta(
            kinematics=follower_kinematics_solver,
            end_effector_step_sizes={
                "x": 0.006,
                "y": 0.01,
                "z": 0.005,
                "wx": 0.03490658503988659,
                "wy": 0.05235987755982988,
                "wz": 0.08726646259971647,
            },
            motor_names=list(follower.bus.motors.keys()),
            use_latched_reference=False,
            use_ik_solution=True,
        ),
        LogRobotAction(),
        EEBoundsAndSafety(
            end_effector_bounds={
                "min": [0.115, -0.165, -0.00175],
                "max": [0.28, 0.16, 0.06],
            },
            max_ee_step_m=0.1,
        ),
        LogRobotAction(),
        GripperVelocityToJoint(
            clip_max=30.0,
            speed_factor=0.075,
            # speed_factor=10.0,
            # discrete_gripper=True,
            scale_velocity=True,
        ),
        LogRobotAction(),
        InverseKinematicsRLStep(
            kinematics=follower_kinematics_solver,
            motor_names=list(follower.bus.motors.keys()),
            initial_guess_current_joints=False,
        ),
        LogRobotAction(),
    ],
    to_transition=identity_transition,
    to_output=transition_to_robot_action,
)


def reset_follower_position(robot_arm: Robot, target_position: np.ndarray) -> None:
    """Reset robot arm to target position using smooth trajectory."""
    current_position_dict = robot_arm.bus.sync_read("Present_Position")
    current_position = np.array(
        [current_position_dict[name] for name in current_position_dict],
        dtype=np.float32,
    )
    trajectory = torch.from_numpy(
        np.linspace(current_position, target_position, 50)
    )  # NOTE: 30 is just an arbitrary number
    for pose in trajectory:
        action_dict = dict(zip(current_position_dict, pose, strict=False))
        robot_arm.bus.sync_write("Goal_Position", action_dict)
        busy_wait(0.015)


# Connect to the robot and teleoperator
follower.connect()
# leader.connect()
gamepad.connect()

reset_pose = [0.00, 0.00, 0.00, 90.00, 90.00, 10.00]

start_time = time.perf_counter()
reset_follower_position(follower, np.array(reset_pose))
busy_wait(5.0 - (time.perf_counter() - start_time))


# Init rerun viewer
init_rerun(session_name="so100_so100_EE_teleop")

info = {}
complementary_data = {}

robot_obs = follower.get_observation()
transition = create_transition(observation=robot_obs, info=info, complementary_data=complementary_data)

print("Starting teleop loop...")
while True:
    t0 = time.perf_counter()

    # Get robot observation
    robot_obs = follower.get_observation()

    # Get teleop action
    raw_action = gamepad.get_action()

    transition[TransitionKey.OBSERVATION] = robot_obs
    transition[TransitionKey.ACTION] = raw_action

    # teleop EE -> robot joints
    follower_joints_act = ee_to_follower_joints(transition)

    # Send action to robot
    _ = follower.send_action(follower_joints_act)

    # Visualize
    log_rerun_data(observation=robot_obs, action=follower_joints_act)

    busy_wait(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
