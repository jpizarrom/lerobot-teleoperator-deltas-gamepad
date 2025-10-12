# Gamepad Teleoperation with Deltas Actions for LeRobot

The teleoperator is implemented to be used mainly with [HILSERL](https://huggingface.co/docs/lerobot/hilserl).

Actions are deltas in the robot's end-effector space (delta_x, delta_y, delta_z, delta_wx, delta_wy, delta_wz, gripper).

Gamepad controls:
- RB: Toggle intervention mode
- Left analog stick (Up/Down): Move Gripper in X plane
- Left analog stick (Left/Right): Move Gripper in Y plane
- Right analog stick (Vertical): Move Gripper in Z axis
- Hold LB + Left analog stick (Up/Down): Rotate Gripper around X axes
- Hold LB + Left analog stick (Left/Right): Rotate Gripper around Y axes
- Hold LB + Right analog stick (Left/Right): Rotate Gripper around Z axis
- Hold RT to open gripper
- Hold LT to close gripper
- A/Green button: End episode with SUCCESS
- B/Red button: End episode with FAILURE
- X/Blue button: Rerecord episode
- D-Pad: Additional discrete movement commands (WASD keys) for LeKiwi Base

## Development

Install the package in editable mode:

```bash
git clone https://github.com/jpizarrom/lerobot-teleoperator-deltas-gamepad.git
cd lerobot-teleoperator-deltas-gamepad
pip install -e .
```

## Reference
This teleoperator is based on the gamepad teleoperator in [lerobot-teleoperator-gamepad](https://github.com/huggingface/lerobot/tree/main/src/lerobot/teleoperators/gamepad)