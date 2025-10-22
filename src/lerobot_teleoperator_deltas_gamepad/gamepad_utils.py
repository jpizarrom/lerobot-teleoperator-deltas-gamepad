#!/usr/bin/env python

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

import logging

from lerobot.utils.utils import log_say

from lerobot.teleoperators.utils import TeleopEvents


class InputController:
    """Base class for input controllers that generate motion deltas."""

    def __init__(
        self,
        x_step_size=1.0,
        y_step_size=1.0,
        z_step_size=1.0,
        wx_step_size=1.0,
        wy_step_size=1.0,
        wz_step_size=1.0,
    ):
        """
        Initialize the controller.

        Args:
            x_step_size: Base movement step size in meters
            y_step_size: Base movement step size in meters
            z_step_size: Base movement step size in meters
        """
        self.x_step_size = x_step_size
        self.y_step_size = y_step_size
        self.z_step_size = z_step_size
        self.wx_step_size = wx_step_size
        self.wy_step_size = wy_step_size
        self.wz_step_size = wz_step_size
        self.running = True
        self.episode_end_status = None  # None, "success", or "failure"
        self.intervention_flag = False

    def start(self):
        """Start the controller and initialize resources."""
        pass

    def stop(self):
        """Stop the controller and release resources."""
        pass

    def get_deltas(self):
        """Get the current movement deltas (dx, dy, dz, wx, wy, wz) in meters."""
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    def update(self):
        """Update controller state - call this once per frame."""
        pass

    def __enter__(self):
        """Support for use in 'with' statements."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are released when exiting 'with' block."""
        self.stop()

    def get_episode_end_status(self):
        """
        Get the current episode end status.

        Returns:
            None if episode should continue, "success" or "failure" otherwise
        """
        status = self.episode_end_status
        self.episode_end_status = None  # Reset after reading
        return status

    def should_intervene(self):
        """Return True if intervention flag was set."""
        return self.intervention_flag
    
    def gripper_value(self):
        return 0.0




class GamepadController(InputController):
    """Generate motion deltas from gamepad input."""

    def __init__(
        self,
        x_step_size=1.0,
        y_step_size=1.0,
        z_step_size=1.0,
        wx_step_size=1.0,
        wy_step_size=1.0,
        wz_step_size=1.0,
        deadzone=0.1,
    ):
        super().__init__(
            x_step_size,
            y_step_size,
            z_step_size,
            wx_step_size,
            wy_step_size,
            wz_step_size,
        )
        self.deadzone = deadzone
        self.joystick = None

        self.current_hat = None
        self.intervention_flag = False
        self.current_values = {}

    def start(self):
        """Initialize pygame and the gamepad."""
        import pygame

        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            logging.error(
                "No gamepad detected. Please connect a gamepad and try again."
            )
            self.running = False
            return

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        self.current_hat = (0, 0)
        logging.info(f"Initialized gamepad: {self.joystick.get_name()}")

        print("Gamepad controls:")
        print("  RB (right bumper): Toggle intervention mode")
        print("  Left analog stick (Up/Down): Move Gripper in X plane")
        print("  Left analog stick (Left/Right): Move Gripper in Y plane")
        print("  Right analog stick (Vertical): Move Gripper in Z axis")
        print("  Hold LB + Left analog stick (Up/Down): Rotate Gripper around X axes")
        print(
            "  Hold LB + Left analog stick (Left/Right): Rotate Gripper around Y axes"
        )
        print(
            "  Hold LB + Right analog stick (Left/Right): Rotate Gripper around Z axis"
        )
        print("  Hold RT (right trigger) to open gripper")
        print("  Hold LT (left trigger) to close gripper")
        print("  A/Green button: End episode with SUCCESS")
        print("  B/Red button: End episode with FAILURE")
        print("  X/Blue button: Rerecord episode")
        print(
            "  D-Pad: Additional discrete movement commands (WASD keys) for LeKiwi Base"
        )

    def stop(self):
        """Clean up pygame resources."""
        import pygame

        if pygame.joystick.get_init():
            if self.joystick:
                self.joystick.quit()
            pygame.joystick.quit()
        pygame.quit()

    def update(self):
        """Process pygame events to get fresh gamepad readings."""
        import pygame

        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                # A button (0) for success
                if event.button == 0:
                    self.episode_end_status = TeleopEvents.SUCCESS
                # B button (1) for failure
                elif event.button == 1:
                    self.episode_end_status = TeleopEvents.FAILURE
                # X button (2) for rerecord
                elif event.button == 2:
                    self.episode_end_status = TeleopEvents.RERECORD_EPISODE

                elif event.button == 4:
                    self.current_values["button_4"] = 1

                elif event.button == 5:  # RB button for intervention flag
                    if not self.intervention_flag:
                        log_say("Human intervention step.", play_sounds=True)
                    else:
                        log_say("Ending human intervention step.", play_sounds=True)
                    self.intervention_flag = not self.intervention_flag

            # Reset episode status on button release
            elif event.type == pygame.JOYBUTTONUP:
                if event.button in [0, 1, 2]:
                    self.episode_end_status = None

                elif event.button == 4:
                    self.current_values["button_4"] = 0

            elif event.type == pygame.JOYAXISMOTION:
                if event.axis == 5:  # RT open gripper
                    self.current_values["joy_5"] = event.value
                elif event.axis == 2:  # LT close gripper
                    self.current_values["joy_2"] = event.value
                elif event.axis == 0:
                    self.current_values["joy_0"] = event.value
                elif event.axis == 1:
                    self.current_values["joy_1"] = event.value
                elif event.axis == 3:
                    self.current_values["joy_3"] = event.value
                elif event.axis == 4:
                    self.current_values["joy_4"] = event.value

            elif event.type == pygame.JOYHATMOTION:
                self.current_hat = event.value

    def get_deltas(self):
        """Get the current movement deltas from gamepad state."""
        import pygame

        try:
            rot_mode = self.current_values.get("button_4", 0)  # left (LB)
            x_input = y_input = z_input = 0
            wx_input = wy_input = wz_input = 0

            if not rot_mode:
                # Read joystick axes
                # Left stick X and Y (typically axes 0 and 1)
                y_input = self.current_values.get("joy_0", 0)  # Left/Right
                x_input = self.current_values.get("joy_1", 0)  # Up/Down

                # Right stick Y (typically axis 3 or 4)
                z_input = self.current_values.get("joy_4", 0)  # Up/Down for Z
            else:
                wx_input = self.current_values.get("joy_1", 0)  # Up/Down
                wy_input = self.current_values.get("joy_0", 0)  # Left/Right

                wz_input = self.current_values.get("joy_3", 0)  # Left/Right for Z

            # Apply deadzone to avoid drift
            x_input = 0 if abs(x_input) < self.deadzone else x_input
            y_input = 0 if abs(y_input) < self.deadzone else y_input
            z_input = 0 if abs(z_input) < self.deadzone else z_input
            wx_input = 0 if abs(wx_input) < self.deadzone else wx_input
            wy_input = 0 if abs(wy_input) < self.deadzone else wy_input
            wz_input = 0 if abs(wz_input) < self.deadzone else wz_input

            # Calculate deltas (note: may need to invert axes depending on controller)
            delta_x = -x_input * self.x_step_size  # Forward/backward
            delta_y = -y_input * self.y_step_size  # Left/right
            delta_z = -z_input * self.z_step_size  # Up/down
            delta_wx = wx_input * self.wx_step_size  # Rotation around X
            delta_wy = -wy_input * self.wy_step_size  # Rotation around Y
            delta_wz = wz_input * self.wz_step_size  # Rotation around Z

            return delta_x, delta_y, delta_z, delta_wx, delta_wy, delta_wz

        except pygame.error:
            logging.error("Error reading gamepad. Is it still connected?")
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    def gripper_value(self):
        """Get the current gripper value from triggers."""
        # Typically, RT is axis 5 and LT is axis 2
        rt_value = self.current_values.get("joy_5", 0)  # Open gripper
        lt_value = self.current_values.get("joy_2", 0)  # Close gripper

        # Normalize trigger values from [-1, 1] to [0, 1]
        rt_normalized = (rt_value + 1) / 2.0
        lt_normalized = (lt_value + 1) / 2.0

        # Gripper value: positive to open, negative to close
        gripper_value = rt_normalized - lt_normalized

        gripper_value = max(-1.0, min(1.0, gripper_value))

        return gripper_value

    def get_buttons(self):
        """Get the current button states from gamepad."""

        button_states = {}

        if self.current_hat != (0, 0):
            map_hat_to_key = {
                (0, 1): "w",  # "up"
                (0, -1): "s",  # "down"
                (1, 0): "d",  # "right"
                (-1, 0): "a",  # "left"
                # (1, 1): "up-right"
                # (-1, 1): "up-left"
                # (1, -1): "down-right"
                # (-1, -1): "down-left"
                # (0, 0): "center"
            }
            key = map_hat_to_key.get(self.current_hat, None)
            if key:
                button_states[key] = None

        return button_states

    def reset(self) -> None:
        """Reset the gamepad state."""
        self.intervention_flag = False
        self.episode_end_status = None
        self.current_values = {}

        self.current_hat = None
