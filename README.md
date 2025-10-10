# Gamepad Teleoperation with Deltas Actions for LeRobot

The teleoperator is implemented to be used mainly with [HILSERL](https://huggingface.co/docs/lerobot/hilserl).

Actions are deltas in the robot's end-effector space (delta_x, delta_y, delta_z, delta_wx, delta_wy, delta_wz, gripper).

## Development

Install the package in editable mode:

```bash
git clone https://github.com/jpizarrom/lerobot-teleoperator-deltas-gamepad.git
cd lerobot-teleoperator-deltas-gamepad
pip install -e .
```

## Reference
This teleoperator is based on the gamepad teleoperator in [lerobot-teleoperator-gamepad](https://github.com/huggingface/lerobot/tree/main/src/lerobot/teleoperators/gamepad)