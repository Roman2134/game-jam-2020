import enum
import math
from pathlib import Path
import time

import arcade

from triple_vision.constants import SCALING
from triple_vision.entities.entity import AnimatedEntity
from triple_vision.entities.sprites import MovingSprite
from triple_vision.entities.weapons import LaserProjectile


class Enemies(enum.Enum):
    """
    Key is base name of the image file.
    Value is default enemy health
    """
    big_demon = 1024
    imp = 512


class BaseEnemy(AnimatedEntity):
    """
    Sprite with idle and run animation.
    """
    enemy_assets_path = Path('assets/dungeon/frames')

    def __init__(self, enemy: Enemies, hp: int = 0, **kwargs) -> None:
        super().__init__(
            sprite_name=enemy.name,
            assets_path=self.enemy_assets_path,
            scale=SCALING,
            **kwargs
        )

        self.hp = enemy.value if hp < 1 else hp
        self.being_pushed = False

    def hit(
        self,
        dmg: int,
        attacker_reference: arcade.Sprite,
        throwback_force: int,
        wall_reference: arcade.SpriteList
    ) -> None:
        """
        value instead of passing it like this
        :param dmg: how much damage to hp will enemy take
        :param attacker_reference: Sprite that hit the enemy (player, projectile etc),
                                   so we know in which direction to push the enemy.
        :param throwback_force:  force (unit is pixel change) the enemy will be pushed away.
        :param wall_reference: SpriteList of things that the enemy cannot go trough. This will
                               stop the enemy from being pushed and slightly damage the enemy.
        """
        self.hp -= dmg
        if self.hp <= 0:
            self.kill()
            return

        if self.being_pushed:
            return

        # TODO DRY
        dest_x = self.center_x
        dest_y = self.center_y

        x_diff = dest_x - attacker_reference.center_x
        y_diff = dest_y - attacker_reference.center_y
        angle = math.atan2(y_diff, x_diff)

        self.change_x = math.cos(angle) * throwback_force
        self.change_y = math.sin(angle) * throwback_force

        self.color = (255, 0, 0)
        self.being_pushed = True

    def reduce_throwback(self) -> None:
        if self.being_pushed:
            if self.change_x > 0:
                self.change_x -= 1
            elif self.change_x < 0:
                self.change_x += 1

            if self.change_y > 0:
                self.change_y -= 1
            elif self.change_y < 0:
                self.change_y += 1

            if -1 <= self.change_x <= 1 and -1 <= self.change_y <= 1:
                self.being_pushed = False
                self.color = (255, 255, 255)

    def update(self, delta_time: float = 1/60) -> None:
        self.reduce_throwback()
        super().update(delta_time)


class ChasingEnemy(BaseEnemy, MovingSprite):
    """
    Simple chasing enemy that tries to catch some other sprite.
    No path-finding, just goes straight to sprite if it is in radius.
    """

    def __init__(
        self,
        ctx,
        enemy: Enemies,
        target_sprite: arcade.Sprite,
        detection_radius: int,
        **kwargs
    ) -> None:
        super().__init__(enemy, **kwargs)
        self.ctx = ctx

        self.target_sprite = target_sprite
        self.detection_radius = detection_radius

    def _detect(self) -> bool:
        return (
            abs(self.center_x - self.target_sprite.center_x) <= self.detection_radius and
            abs(self.center_y - self.target_sprite.center_y) <= self.detection_radius
        )

    def update(self, delta_time: float = 1/60):
        if not self.being_pushed:
            if self._detect():
                self.move_to(self.target_sprite.center_x,
                             self.target_sprite.center_y,
                             rotate=False)
            else:
                self.change_x = 0
                self.change_y = 0

        super().update()


class StationaryEnemy(BaseEnemy):

    def __init__(
        self,
        ctx,
        enemy: Enemies,
        target_sprite: arcade.Sprite,
        detection_radius: int,
        **kwargs
    ) -> None:
        super().__init__(enemy, **kwargs)
        self.ctx = ctx

        self.target_sprite = target_sprite
        self.detection_radius = detection_radius

        self.last_shot = time.time()

    def update(self, delta_time: float = 1/60) -> None:
        if not (
            self.center_x - self.detection_radius < self.target_sprite.center_x and
            self.target_sprite.center_x < self.center_x + self.detection_radius and
            self.center_y - self.detection_radius < self.target_sprite.center_y and
            self.target_sprite.center_y < self.center_y + self.detection_radius
        ):
            return

        if time.time() - self.last_shot < 0.75:
            return

        laser = LaserProjectile(
            center_x=self.center_x,
            center_y=self.center_y
        )
        laser.move_to(
            self.target_sprite.center_x,
            self.target_sprite.center_y,
            rotate=True,
            set_target=False
        )

        self.ctx.enemy_projectiles.append(laser)
        self.last_shot = time.time()
