import arcade
import itertools
import json
import time
import os
import vlc
from . import perspective_objects


class Audio:
    BASE_DIR = os.getcwd()
    FPS = 16

    settings = None
    volume = None

    track = None
    music = None
    notes = []
    frame_count = itertools.count(1, 1)
    active = False
    vlc_instance = None
    player = None

    def __init__(self, main_):
        self.main = main_
        self.settings = self.main.settings
        self.volume = self.settings.volume * 0.1

    @classmethod
    def _setup(cls, _track: dict):
        cls.track = _track

        path = f"{cls.BASE_DIR}/main/tracks/{cls.track['path'].upper()}.{cls.track['type']}"
        cls.vlc_instance = vlc.Instance('--input-repeat=-1')
        cls.player = cls.vlc_instance.media_player_new()
        media = cls.vlc_instance.media_new(path)
        cls.player.set_media(media)

        with open(f"{cls.BASE_DIR}/main/tracks/{cls.track['path']}.json", 'r') as file:
            cls.notes = json.load(file)

    @classmethod
    def _play(cls):
        cls.player.play()
        cls.active = True
        time.sleep(0.01)

    @classmethod
    def _pause(cls):
        cls.player.pause()
        cls.active = False

    @classmethod
    def _stop(cls):
        cls.player.stop()
        cls.active = False

    @classmethod
    def get_notes(cls, frame):
        section, frame = divmod(frame, cls.FPS)
        return cls.notes[section][frame]


class PauseScreen:
    sprite_list = arcade.SpriteList()
    BASE_DIR = None
    WIDTH = None
    HEIGHT = None

    @classmethod
    def pause_setup(cls, base_dir, width, height):
        cls.BASE_DIR = base_dir
        cls.WIDTH = width
        cls.HEIGHT = height

    @classmethod
    def pause_menu(cls):
        cls.sprite_list.append(  # Game Paused text
            arcade.Sprite(filename=f"{cls.BASE_DIR}/main/Resources/game_play/Game-Paused.png",
                          center_x=cls.WIDTH / 2,
                          center_y=cls.HEIGHT / 1.25,
                          scale=1))

        cls.sprite_list.append(  # Main Menu text
            arcade.Sprite(filename=f"{cls.BASE_DIR}/main/Resources/game_play/Main-Menu.png",
                          center_x=cls.WIDTH / 2,
                          center_y=cls.HEIGHT / 1.75,
                          scale=1))

        cls.sprite_list.append(  # settings text
            arcade.Sprite(filename=f"{cls.BASE_DIR}/main/Resources/game_play/Settings.png",
                          center_x=cls.WIDTH / 2,
                          center_y=cls.HEIGHT / 2.5,
                          scale=1))

        cls.sprite_list.append(  # settings text
            arcade.Sprite(filename=f"{cls.BASE_DIR}/main/Resources/game_play/Press-SPACE-to-unpause.png",
                          center_x=cls.WIDTH / 2,
                          center_y=cls.HEIGHT / 4.75,
                          scale=0.75))

        return cls.sprite_list


class GameLogic:
    @classmethod
    def get_points(cls, note_y, key_height):
        delta = note_y - key_height
        if delta in range(-5, 5):
            return 100  # Perfect
        elif delta in range(-20, -5):
            return 50  # Good
        elif delta in range(-50, -20):
            return 20  # OK
        else:
            return -1  # Miss

    @classmethod
    def check_miss(cls, note_y, key_height):
        delta = note_y - key_height
        return delta not in range(-50, 50)

    @classmethod
    def get_data(cls,
                 keys_list: ("pressed keys", list, tuple),
                 key_data: ("Key sprites", list, tuple),
                 notes: ("note objects", list, tuple)):
        total_points, combos = 0, 0
        for loc, key in enumerate(keys_list):
            if key:
                if notes[loc] is not None:
                    points = cls.get_points(notes[loc], key_data[loc])
                    if points != -1:
                        total_points += points
                        combos += 1
                    else:
                        combos = -1
                else:
                    combos = -1
            else:
                if notes[loc] is not None:
                    if cls.check_miss(notes[loc], key_data[loc]):
                        combos = -1
        return total_points, combos


class GameScreen(arcade.View, PauseScreen):
    """ Main audio playing screen. """

    # settings
    no_fail = True  # no matter how many times u miss you're not gonna loose
    BASE_DIR = os.getcwd()

    # setup
    key_binds = None
    left_button_active = False
    middle_button_active = False
    right_button_active = False

    paused = started = False
    left = center = right = False   # notes

    background = None
    key_1, key_2, key_3 = None, None, None
    count_down = []
    to_be_rendered = None

    # Game Data
    score = 0
    combo = 0
    notes_hit = 0
    notes_missed = 0
    notes_total = 0

    def __init__(self, main_):
        super().__init__()
        self.audio = Audio(main_=main_)
        self.main = main_
        self.settings = main_.settings
        self.WIDTH, self.HEIGHT = self.main.window.width, self.main.window.height
        self.background_sprite = arcade.Sprite(
            filename=f"{self.BASE_DIR}/main/Resources/game_play/Notes-Background.png",
            scale=1,
            image_height=self.HEIGHT,
            image_width=self.WIDTH)

    def setup(self, _track):
        """
        This Adds the background image, Keys 1 -> 3 sprites, and countdown sprites,
        this also setups the audio system and gets that ready as well as the pause-
        page and loads key binds.

        :param _track:
        :return:
        """

        arcade.schedule(self.on_note_change, 1 / 16)
        self.audio._setup(_track)
        self.pause_setup(base_dir=self.BASE_DIR, width=self.WIDTH, height=self.HEIGHT)
        self.key_binds = self.settings.key_binds
        self.background = arcade.Sprite(
            filename=f"{self.BASE_DIR}/main/Resources/background.png",
            scale=0.4,
            image_height=self.HEIGHT * 14/5,
            image_width=self.WIDTH)

        self.key_1 = arcade.Sprite(
            filename=f"{self.BASE_DIR}/main/Resources/game_play/note_key.png",
            scale=(self.WIDTH / self.HEIGHT) / (20/3))
        self.key_2 = arcade.Sprite(
            filename=f"{self.BASE_DIR}/main/Resources/game_play/note_key.png",
            scale=(self.WIDTH / self.HEIGHT) / (20/3))
        self.key_3 = arcade.Sprite(
            filename=f"{self.BASE_DIR}/main/Resources/game_play/note_key.png",
            scale=(self.WIDTH / self.HEIGHT) / (20/3))

        self.count_down.append(
            arcade.Sprite(filename=f"{self.BASE_DIR}/main/Resources/game_play/1.png", scale=1))
        self.count_down.append(
            arcade.Sprite(filename=f"{self.BASE_DIR}/main/Resources/game_play/2.png", scale=1))
        self.count_down.append(
            arcade.Sprite(filename=f"{self.BASE_DIR}/main/Resources/game_play/3.png", scale=1))

    def on_note_change(self, td):
        """ This is the function that cycles through each note array, this is a 3 dimension list,
            Normally this should render at 16 fps to update (on a 4/4 song) This can be 64 fps if
            vlc is being weird?
        """

        self.active = self.audio.player.is_playing()
        if self.active:
            self.left, self.center, self.right = self.audio.get_notes(next(self.audio.frame_count))

        elif not self.paused and not self.active and self.started:
            pass
            # with open(f"{self.BASE_DIR}/tracks/{self.track['path']}_new.json", 'w+') as file:
            #   json.dump(self.notes_, file)

    def on_start(self):
        self.started = True
        self.audio._play()

    def on_pause(self):
        self.paused = not self.paused
        self.audio._pause()

    def on_update(self, delta_time: float):
        """ In charge of registering if a user had hit or missed a note. """
        points_to_add, combos = GameLogic.get_data(
            (self.left_button_active, self.middle_button_active, self.right_button_active),
            (self.key_1, self.key_2, self.key_3),
            ()  # todo get jamie to help with note handling
        )
        self.score += points_to_add
        self.combo = (self.combo + combos) if combos != -1 else 0

        if not self.audio.player.is_playing() and self.started and not self.paused:
            pass  # todo make a end screen

    def on_draw(self, time_delta=None, count_down=None):
        """ In charge of rendering the notes at current time. """
        arcade.start_render()

        # Background rendering
        self.background.center_x = self.WIDTH / 2
        self.background.center_y = self.HEIGHT / 2
        self.background.scale = 0.4
        self.background.width = self.WIDTH
        self.background.alpha = 200
        self.background.draw()

        # White mask note box
        arcade.draw_rectangle_filled(
            self.WIDTH / 2,
            self.HEIGHT / 2,
            width=self.WIDTH / 2,
            height=self.HEIGHT,
            color=arcade.color.WHITE)

        # Note background sprite render
        self.background_sprite.center_x = self.WIDTH / 2
        self.background_sprite.center_y = self.HEIGHT / 2
        self.background_sprite.scale = 1
        self.background_sprite.width = self.WIDTH / 2
        self.background_sprite.alpha = 160
        self.background_sprite.draw()

        # If un pausing render  todo finish
        if count_down is not None:
            count_down.draw()

        # White box behind the keys
        arcade.draw_rectangle_filled(
            self.WIDTH / 2,
            self.HEIGHT / 10,
            width=self.WIDTH / 2,
            height=self.key_1.height,
            color=arcade.color.WHITE)

        # Renders pressed keys if NOT paused
        if not self.paused and self.started:
            if self.left_button_active:
                self.key_1.center_x = self.WIDTH / 2 - (self.WIDTH / (200 / 21))
                self.key_1.center_y = self.HEIGHT / 10
                self.key_1.scale = ((self.WIDTH / self.HEIGHT) / (20 / 3)) * (self.HEIGHT / 600)
                self.key_1.draw()

            if self.middle_button_active:
                self.key_2.center_x = self.WIDTH / 2
                self.key_2.center_y = self.HEIGHT / 10
                self.key_2.scale = ((self.WIDTH / self.HEIGHT) / (20 / 3)) * (self.HEIGHT / 600)
                self.key_2.draw()

            if self.right_button_active:
                self.key_3.center_x = self.WIDTH / 2 + (self.WIDTH / (200 / 21))
                self.key_3.center_y = self.HEIGHT / 10
                self.key_3.scale = ((self.WIDTH / self.HEIGHT) / (20 / 3)) * (self.HEIGHT / 600)
                self.key_3.draw()

        # Audio progress bar
        pos = self.audio.player.get_position()
        lower_x, lower_y = self.WIDTH / 1.1 + self.WIDTH / 150, self.HEIGHT / 20
        height, width = self.HEIGHT - self.HEIGHT / 7, self.WIDTH / 18

        # Black outline
        arcade.draw_line(start_x=lower_x,
                         start_y=lower_y,
                         end_x=lower_x + 300,
                         end_y=height,
                         line_width=width,
                         color=arcade.color.CRIMSON)
        # Filled
        arcade.draw_line(start_x=lower_x + 5,
                         start_y=lower_y,
                         end_x=lower_x + 300 - 5,
                         end_y=height * pos,
                         line_width=width,
                         color=arcade.color.CRIMSON)

        # Shows Pause menu because i suck?
        if self.paused:
            self.background.alpha = 255
            self.background.draw()
            self.pause_menu().draw()

    def on_key_press(self, symbol: int, modifiers: int):
        """ This is only for registering if keys are pressed and to change the relevant buttons """

        # Actual game keys
        if symbol == self.key_binds['left']:
            self.left_button_active = True

        elif symbol == self.key_binds['center']:
            self.middle_button_active = True

        elif symbol == self.key_binds['right']:
            self.right_button_active = True

        elif symbol == arcade.key.SPACE:
            if not self.started:
                self.on_start()
            else:
                self.on_pause()

    def on_key_release(self, symbol: int, modifiers: int):
        """ This is only for registering if keys are released and to change the relevant buttons """

        # Actual game keys
        if symbol == self.key_binds['left']:
            self.left_button_active = False

        elif symbol == self.key_binds['center']:
            self.middle_button_active = False

        elif symbol == self.key_binds['right']:
            self.right_button_active = False



