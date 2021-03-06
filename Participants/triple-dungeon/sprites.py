"""
sprites.py
A file dedicated to managing sprites and animations for characters.
"""

import arcade
import os
import re

from typing import Pattern, Iterable
from itertools import cycle


class AnimationSet(object):
    """
    A class that helps assist with grabbing new animations from a set.
    """

    def __init__(self, directory: str) -> None:
        """
        Initializes the AnimationSet class by loading files and

        :param directory: A directory containing valid animation files in the correct format.
        """

        self.directory = directory
        self.animations = os.listdir(directory)

    def getAnimations(self, pattern: Pattern) -> Iterable[arcade.Texture]:
        """
        Loads all animations from the AnimationSet's directory that match the pattern.
        The pattern must have 1 group that specifies the animation's index.

        :param pattern: A RegEx Pattern object.
        :return: A infinite iterable looping through arcade.Texture objects.
        """

        # Finds all matching files
        matches = map(lambda file: re.match(pattern, file), self.animations)
        matches = list(filter(lambda match: match is not None, matches))
        # Sort in ascending order based on the connected animation index. Zero-indexing or not does not affect order.
        matches.sort(key=lambda match: int(match.group(1)))
        # Grab the filename and load it to the file directory
        matches = list(map(lambda match: arcade.load_texture(os.path.join(self.directory, match.group(0))), matches))
        return cycle(matches)


class PlayerAnimations(AnimationSet):
    """
    A class dedicated to serving player animations.
    Player animations must be served to the class in the correct format.

    The correct format is: {action}[_{direction}]_{index}.png
    action: [idle, run, slice] - The action being taken.
    direction: [down, right, left, up] - The direction of the action, if applicable. Omit the underscore if not.
    index: [0,) - The index of the animation. Index should be enumerated in ascending order.
    """

    def __init__(self, directory: str) -> None:
        """
        Initializes the PlayerAnimations class.
        """
        super(PlayerAnimations, self).__init__(directory)

        # Grabs all animations needed. These are infinite iters, use next(iter) to grab the next animation.
        self.idles = self.getAnimations(re.compile(r'idle_(\d+).png'))
        self.down = self.getAnimations(re.compile(r'run_down_(\d+).png'))
        self.right = self.getAnimations(re.compile(r'run_right_(\d+).png'))
        self.up = self.getAnimations(re.compile(r'run_up_(\d+).png'))
        self.left = self.getAnimations(re.compile(r'run_left_(\d+).png'))
