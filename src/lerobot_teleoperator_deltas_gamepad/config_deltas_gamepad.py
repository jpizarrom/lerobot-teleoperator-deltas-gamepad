from dataclasses import dataclass

from lerobot.teleoperators.config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("deltas_gamepad")
@dataclass
class DeltasGamepadConfig(TeleoperatorConfig):
    use_gripper: bool = True
