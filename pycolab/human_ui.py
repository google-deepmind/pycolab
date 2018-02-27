# Copyright 2017 the pycolab Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Frontends for humans who want to play pycolab games."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import copy
import curses
import datetime
import textwrap

from pycolab import cropping
from pycolab.protocols import logging as plab_logging

import six


class CursesUi(object):
  """A terminal-based UI for pycolab games."""

  def __init__(self,
               keys_to_actions, delay=None,
               repainter=None, colour_fg=None, colour_bg=None,
               croppers=None):
    """Construct and configure a `CursesUi` for pycolab games.

    A `CursesUi` object can be used over and over again to play any number of
    games implemented by using pycolab---however, the configuration options used
    to build the object will probably only be suitable for some.

    `CursesUi` provides colour support, but only in terminals that support true
    colour text colour attributes, and only when there is sufficient space in
    the terminal's colourmap, as well as a sufficient number of free "colour
    pairs", to accommodate all the characters given custom colours in
    `colour_fg` and `colour_bg`. Your terminal may be compatible out of the box;
    it may be compatible but only after setting the `$TERM` environment
    variable; or it may simply not work. Some specific guidance:

        To use this:         do this:
        ------------         --------
        iTerm2               nothing (should work out of the box)
        MacOS Terminal       switch to iTerm2 (it doesn't really work)
        GNOME Terminal       set $TERM to xterm-256color
        Modern xterm         set $TERM to xterm-256color
        tmux, screen         follow guidance at [1]
        ASR-33               buy a box of crayons

    Like any self-respecting game interface, `CursesUi` features a game console,
    which can be revealed and hidden via the Page Up and Page Down keys
    respectively. Log strings accumulated in the `Plot` object via its `log`
    method are shown in the console.

    [1]: https://sanctum.geek.nz/arabesque/256-colour-terminals/

    Args:
      keys_to_actions: a dict mapping characters or key codes to whatever
          action symbols your pycolab games understand. For example, if your
          game uses the integer 5 to mean "shoot laser", you could map ' ' to 5
          so that the player can shoot the laser by tapping the space bar. "Key
          codes" are the numerical ASCII (and other) codes that the Python
          `curses` library uses to mark keypresses besides letters, numbers, and
          punctuation; codes like `curses.KEY_LEFT` may be especially useful.
          For more on these, visit the [`curses` manual](
          https://docs.python.org/2/library/curses.html#constants). Any
          character or key code received from the user but absent from this dict
          will be ignored. See also the note about `-1` in the documentation for
          the `delay` argument.
      delay: whether to timeout when retrieving a keypress from the user, and
          if so, for how long. If None, `CursesUi` will wait indefinitely for
          the user to press a key between game iterations; if positive,
          `CursesUi` will wait that many milliseconds. If the waiting operation
          times out, `CursesUi` will look up the keycode `-1` in the
          `keys_to_actions` dict and pass the corresponding action on to the
          game. So, if you use this delay option, make certain that you have an
          action mapped to the keycode `-1` in `keys_to_actions`; otherwise, the
          timeouts will be ignored, and `CursesUi` will behave as if `delay`
          were None.
      repainter: an optional `ObservationCharacterRepainter` that changes the
          characters used by the observation returned from the game engine,
          presumably to a character set that makes the observations match your
          preferred look for the game.
      colour_fg: an optional mapping from single ASCII character strings to
          3-tuples (or length 3 lists) encoding an RGB colour. These colours are
          used (in compatible terminals only) as the foreground colour when
          printing those characters. If unspecified for a particular character,
          or if None, some boring default colour is used instead. *NOTE: RGB
          component values range in `[0,999]`, not `[0,255]` as you may have
          expected.*
      colour_bg: exactly like `colour_fg`, but for charcter background colours.
          If unspecified, the same colours specified by `colour_fg` (or its
          defaults) are used instead (so characters basically become tall
          rectangular pixels).
      croppers: None, or a list of `cropping.ObservationCropper` instances
          and/or None values. If a list of `ObservationCropper`s, each cropper
          in the list will make its own crop of the observation, and the cropped
          observations will all be shown side-by-side. A None value in the list
          means observations returned by the pycolab game supplied to the `play`
          method should be shown directly instead of cropped. A single None
          value for this argument is a shorthand for `[None]`.

    Raises:
      TypeError: if any key in the `keys_to_actions` dict is neither a numerical
          keycode nor a length-1 ASCII string.
    """
    # This slot holds a reference to the game currently being played, or None
    # if no game is being played at the moment.
    self._game = None
    # What time did the game start? Or None if there is no game being played.
    self._start_time = None
    # What is our total so far? Or None if there is no game being played.
    self._total_return = None

    # For displaying messages logged by game entities in a game console.
    self._log_messages = []

    # The curses `getch` routine returns numeric keycodes, but users can specify
    # keyboard input as strings as well, so we convert strings to keycodes.
    try:
      self._keycodes_to_actions = {
          ord(key) if isinstance(key, str) else key: action
          for key, action in six.iteritems(keys_to_actions)}
    except TypeError:
      raise TypeError('keys in the keys_to_actions argument must either be '
                      'numerical keycodes or single ASCII character strings.')

    # We'd like to see whether the user is using any reserved keys here in the
    # constructor, but we have to wait until curses is actually running to do
    # that. So, the reserved key check happens in _init_curses_and_play.

    # Save colour mappings and other parameters from the user. Note injection
    # of defaults and the conversion of character keys to ASCII codepoints.
    self._delay = delay
    self._repainter = repainter
    self._colour_fg = (
        {ord(char): colour for char, colour in six.iteritems(colour_fg)}
        if colour_fg is not None else {})
    self._colour_bg = (
        {ord(char): colour for char, colour in six.iteritems(colour_bg)}
        if colour_bg is not None else self._colour_fg)

    # This slot will hold a mapping from characters to the curses colour pair
    # we'll use when we're displaying that character. None for now, since we
    # can't set it up until curses is running.
    self._colour_pair = None

    # If the user specified no croppers or any None croppers, replace them with
    # pass-through croppers that don't do any cropping.
    if croppers is None:
      self._croppers = [cropping.ObservationCropper()]
    else:
      self._croppers = croppers

    try:
      self._croppers = tuple(cropping.ObservationCropper() if c is None else c
                             for c in self._croppers)
    except TypeError:
      raise TypeError('The croppers argument to the CursesUi constructor must '
                      'be a sequence or None, not a "bare" object.')

  def play(self, game):
    """Play a pycolab game.

    Calling this method initialises curses and starts an interaction loop. The
    loop continues until the game terminates or an error occurs.

    This method will exit cleanly if an exception is raised within the game;
    that is, you shouldn't have to reset your terminal.

    Args:
      game: a pycolab game. Ths game must not have had its `its_showtime` method
          called yet.

    Raises:
      RuntimeError: if this method is called while a game is already underway.
    """
    if self._game is not None:
      raise RuntimeError('CursesUi is not at all thread safe')
    self._game = game
    self._start_time = datetime.datetime.now()
    # Inform the croppers which game we're playing.
    for cropper in self._croppers:
      cropper.set_engine(self._game)

    # After turning on curses, set it up and play the game.
    curses.wrapper(self._init_curses_and_play)

    # The game has concluded. Print the final statistics.
    duration = datetime.datetime.now() - self._start_time
    print('Game over! Final score is {}, earned over {}.'.format(
        self._total_return, _format_timedelta(duration)))

    # Clean up in preparation for the next game.
    self._game = None
    self._start_time = None
    self._total_return = None

  def _init_curses_and_play(self, screen):
    """Set up an already-running curses; do interaction loop.

    This method is intended to be passed as an argument to `curses.wrapper`,
    so its only argument is the main, full-screen curses window.

    Args:
      screen: the main, full-screen curses window.

    Raises:
      ValueError: if any key in the `keys_to_actions` dict supplied to the
          constructor has already been reserved for use by `CursesUi`.
    """
    # See whether the user is using any reserved keys. This check ought to be in
    # the constructor, but it can't run until curses is actually initialised, so
    # it's here instead.
    for key, action in six.iteritems(self._keycodes_to_actions):
      if key in (curses.KEY_PPAGE, curses.KEY_NPAGE):
        raise ValueError(
            'the keys_to_actions argument to the CursesUi constructor binds '
            'action {} to the {} key, which is reserved for CursesUi. Please '
            'choose a different key for this action.'.format(
                repr(action), repr(curses.keyname(key))))

    # If the terminal supports colour, program the colours into curses as
    # "colour pairs". Update our dict mapping characters to colour pairs.
    self._init_colour()
    curses.curs_set(0)  # We don't need to see the cursor.
    if self._delay is None:
      screen.timeout(-1)  # Blocking reads
    else:
      screen.timeout(self._delay)  # Nonblocking (if 0) or timing-out reads

    # Create the curses window for the log display
    rows, cols = screen.getmaxyx()
    console = curses.newwin(rows // 2, cols, rows - (rows // 2), 0)

    # By default, the log display window is hidden
    paint_console = False

    def crop_and_repaint(observation):
      # Helper for game display: applies all croppers to the observation, then
      # repaints the cropped subwindows. Since the same repainter is used for
      # all subwindows, and since repainters "own" what they return and are
      # allowed to overwrite it, we copy repainted observations when we have
      # multiple subwindows.
      observations = [cropper.crop(observation) for cropper in self._croppers]
      if self._repainter:
        if len(observations) == 1:
          return [self._repainter(observations[0])]
        else:
          return [copy.deepcopy(self._repainter(obs)) for obs in observations]
      else:
        return observations

    # Kick off the game---get first observation, crop and repaint as needed,
    # initialise our total return, and display the first frame.
    observation, reward, _ = self._game.its_showtime()
    observations = crop_and_repaint(observation)
    self._total_return = reward
    self._display(
        screen, observations, self._total_return, elapsed=datetime.timedelta())

    # Oh boy, play the game!
    while not self._game.game_over:
      # Wait (or not, depending) for user input, and convert it to an action.
      # Unrecognised keycodes cause the game display to repaint (updating the
      # elapsed time clock and potentially showing/hiding/updating the log
      # message display) but don't trigger a call to the game engine's play()
      # method. Note that the timeout "keycode" -1 is treated the same as any
      # other keycode here.
      keycode = screen.getch()
      if keycode == curses.KEY_PPAGE:    # Page Up? Show the game console.
        paint_console = True
      elif keycode == curses.KEY_NPAGE:  # Page Down? Hide the game console.
        paint_console = False
      elif keycode in self._keycodes_to_actions:
        # Convert the keycode to a game action and send that to the engine.
        # Receive a new observation, reward, discount; crop and repaint; update
        # total return.
        action = self._keycodes_to_actions[keycode]
        observation, reward, _ = self._game.play(action)
        observations = crop_and_repaint(observation)
        if self._total_return is None:
          self._total_return = reward
        elif reward is not None:
          self._total_return += reward

      # Update the game display, regardless of whether we've called the game's
      # play() method.
      elapsed = datetime.datetime.now() - self._start_time
      self._display(screen, observations, self._total_return, elapsed)

      # Update game console message buffer with new messages from the game.
      self._update_game_console(
          plab_logging.consume(self._game.the_plot), console, paint_console)

      # Show the screen to the user.
      curses.doupdate()

  def _display(self, screen, observations, score, elapsed):
    """Redraw the game board onto the screen, with elapsed time and score.

    Args:
      screen: the main, full-screen curses window.
      observations: a list of `rendering.Observation` objects containing
          subwindows of the current game board.
      score: the total return earned by the player, up until now.
      elapsed: a `datetime.timedelta` with the total time the player has spent
          playing this game.
    """
    screen.erase()  # Clear the screen

    # Display the game clock and the current score.
    screen.addstr(0, 2, _format_timedelta(elapsed), curses.color_pair(0))
    screen.addstr(0, 20, 'Score: {}'.format(score), curses.color_pair(0))

    # Display cropped observations side-by-side.
    leftmost_column = 0
    for observation in observations:
      # Display game board rows one-by-one.
      for row, board_line in enumerate(observation.board, start=1):
        screen.move(row, leftmost_column)  # Move to start of this board row.
        # Display game board characters one-by-one. We iterate over them as
        # integer ASCII codepoints for easiest compatibility with python2/3.
        for codepoint in six.iterbytes(board_line.tostring()):
          screen.addch(
              codepoint, curses.color_pair(self._colour_pair[codepoint]))

      # Advance the leftmost column for the next observation.
      leftmost_column += observation.board.shape[1] + 3

    # Redraw the game screen (but in the curses memory buffer only).
    screen.noutrefresh()

  def _update_game_console(self, new_log_messages, console, paint_console):
    """Update game console text buffer; draw console to the screen if enabled.

    Args:
      new_log_messages: a list of strings containing new log messages to place
          in the game console's message buffer.
      console: curses window for the game console.
      paint_console: if True, the console will be displayed at the next screen
          refresh; if not, it won't.
    """
    # First we have to format the new messages to fit within our game console.
    rows, cols = console.getmaxyx()

    # Split all log messages on newline characters.
    split_log_messages = []
    for message in new_log_messages:
      split_log_messages.extend(message.splitlines())

    # It's a little weird to wrap console log messages with a text wrapper
    # designed for English text, but that beats writing tab expansion myself.
    wrapper = textwrap.TextWrapper(
        width=cols, drop_whitespace=False, break_on_hyphens=False)
    for message in split_log_messages:
      self._log_messages.extend(wrapper.wrap(message))

    # There's only room on the screen for the last rows-1 console messages.
    del self._log_messages[:(1-rows)]

    # Draw the console if the console is visible.
    if paint_console:
      console.border(' ', ' ', curses.ACS_HLINE, ' ',
                     curses.ACS_ULCORNER, curses.ACS_URCORNER, ' ', ' ')
      console.addstr(0, 4, '{ Console }', curses.A_BOLD)
      console.addstr(1, 0, '\n'.join(self._log_messages))
      console.noutrefresh()

  def _init_colour(self):
    """Allocate curses colours and "colour pairs" for user-specified colours.

    Curses manages colour in the following way: first, entries within a
    finite palette of colours (usually 255) are assigned a particular RGB value;
    next, foreground and background pairs of these colours are defined in a
    second palette of colour pairs (also finite; perhaps around 32767 entries).
    This function takes the `colour_fg` and `colour_bg` dicts supplied to the
    constructor and attempts to allocate enough colours and colour pairs to
    handle all of the colour combinations that they specify.

    If this method determines that the terminal isn't capable of accepting a
    custom colour palette, or if there turn out not to be enough colours or
    colour pairs to accommodate the user-supplied colour dicts, this method will
    simply allow the default foreground and background colour to be used.
    """
    # The default colour for all characters without colours listed is boring
    # white on black, or "system default", or somesuch.
    self._colour_pair = collections.defaultdict(lambda: 0)
    # And if the terminal doesn't support true color, that's all you get.
    if not curses.can_change_color(): return

    # Collect all unique foreground and background colours. If this terminal
    # doesn't have enough colours for all of the colours the user has supplied,
    # plus the two default colours, plus the largest colour id (which we seem
    # not to be able to assign, at least not with xterm-256color) stick with
    # boring old white on black.
    colours = set(six.itervalues(self._colour_fg)).union(
        six.itervalues(self._colour_bg))
    if (curses.COLORS - 2) < len(colours): return

    # Get all unique characters that have a foreground and/or background colour.
    # If this terminal doesn't have enough colour pairs for all characters plus
    # the default colour pair, stick with boring old white on black.
    characters = set(self._colour_fg).union(self._colour_bg)
    if (curses.COLOR_PAIRS - 1) < len(characters): return

    # Get the identifiers for both colours in the default colour pair.
    cpair_0_fg_id, cpair_0_bg_id = curses.pair_content(0)

    # With all this, make a mapping from colours to the IDs we'll use for them.
    ids = (set(range(curses.COLORS - 1)) -  # The largest ID is not assignable?
           {cpair_0_fg_id, cpair_0_bg_id})  # We don't want to change these.
    ids = list(reversed(sorted(ids)))  # We use colour IDs from large to small.
    ids = ids[:len(colours)]  # But only those colour IDs we actually need.
    colour_ids = dict(zip(colours, ids))

    # Program these colours into curses.
    for colour, cid in six.iteritems(colour_ids):
      curses.init_color(cid, *colour)

    # Now add the default colours to the colour-to-ID map.
    cpair_0_fg = curses.color_content(cpair_0_fg_id)
    cpair_0_bg = curses.color_content(cpair_0_bg_id)
    colour_ids[cpair_0_fg] = cpair_0_fg_id
    colour_ids[cpair_0_bg] = cpair_0_bg_id

    # The color pair IDs we'll use for all characters count up from 1; note that
    # the "default" colour pair of 0 is already defined, since _colour_pair is a
    # defaultdict.
    self._colour_pair.update(
        {character: pid for pid, character in enumerate(characters, start=1)})

    # Program these color pairs into curses, and that's all there is to do.
    for character, pid in six.iteritems(self._colour_pair):
      # Get foreground and background colours for this character. Note how in
      # the absence of a specified background colour, the same colour as the
      # foreground is used.
      cpair_fg = self._colour_fg.get(character, cpair_0_fg_id)
      cpair_bg = self._colour_bg.get(character, cpair_fg)
      # Get colour IDs for those colours and initialise a colour pair.
      cpair_fg_id = colour_ids[cpair_fg]
      cpair_bg_id = colour_ids[cpair_bg]
      curses.init_pair(pid, cpair_fg_id, cpair_bg_id)


def _format_timedelta(timedelta):
  """Convert timedelta to string, lopping off microseconds."""
  # This approach probably looks awful to all you time nerds, but it will work
  # in all the locales we use in-house.
  return str(timedelta).split('.')[0]
