# coding=utf8

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

"""Routines for pycolab game entities to discuss game board scrolling.

*Note: the scrolling mechanism that this module facilitates is only one way to
achieve scrolling behaviour in pycolab... and it happens to be one of the more
complicated ways. If you just want to scroll around a finite map, consider using
a mechanism like `ScrollingCropper` in `croppers.py`, which moves a tracking
window around the observation emitted by the game engine, and so doesn't require
game entities to think about or even know that scrolling is underway. (See
`examples/better_scrolly_maze.py` for a usage example.) You may still need the
scrolling protocol in some cases -- e.g. if you have a generated "infinite"
map -- in which case, buckle in and read on...*

Plenty of cool video games are scrolling video games (think Zelda, Defender,
Super Mario Bros.), and pycolab should be able to scroll, too. The only problem
is that with different objects putting all kinds of scenery all over the game
board, we need some way to make certain that they all move their stuff in unison
as they should. (Or not! Egocentric characters like Link and Mario move the
world around them, after all...)

In order to help everyone scroll harmoniously, the functions in this file
provide a handy way for `Sprite`s, `Drape`s, and the `Backdrop` to talk about
scrolling. Any one of these entities could scroll---your `Backdrop` could be a
scrolling window over a huge game world, or the `Backdrop` could be some neat-o
fixed starfield with a `Drape`-powered set of scrolling platforms and obstacles
to jump around; in either of these cases, `Sprite`s could be objects for the
player to collect, and would therefore have to scroll with the scenery.

## How it works:

Participation in the scrolling protocol is optional for `Sprite`s, `Drape`s, and
the `Backdrop`. Entities that do participate, however, are either egocentric
(the world scrolls around them, like Mario or Link) or not (they scroll with the
rest of the world, like Goombas and coins). While there's no need to worry much
about non-egocentric entities, any attempt to scroll the world will have to be
careful that it doesn't scroll egocentric entities into impossible places! You
can't scroll Mario into a wall, or he will be stuck there forever.

Therefore, the first step is for egocentric participants to register themselves
as egocentric via the `participate_as_egocentric` function of this module. After
this registration, the `order` (as in "command"!) function within this module
will know to check whether a particular motion is okay for all the egocentric
entities before issuing a "scrolling order" (more on this in a second).

For this reason, at each game iteration, all egocentric game entities will need
to provide a set of "legal" scrolling motions that could be undertaken *during
the next game iteration* without causing that entity to do something
impossible---like walk into a wall, or scroll partially off of the screen (if
that's something you care about). This is done via this module's `permit`
function.

By the time the next game iteration rolls around, whichever entity wants to
scroll the world can check whether a particular scrolling motion is acceptable
to all egocentric entities (via the `is_possible` function). If it is, it can
issue a "scrolling order" to all of the participating entities via the `order`
function, which simply places a note in the `Plot` object that says that a
particular scrolling motion is taking place. All of these entities should look
at the `Plot` object to see whether a scrolling order has been made, and if one
has, then they should update their `position`s or `curtain`s accordingly.
Remember, a protocol is only a way for game entities to *discuss* scrolling;
it's up to the entities themselves to actually do the scrolling if so commanded.

For convenience, any entities can see whether a scrolling order is present by
using the `get_order` function.

Important note: the scrolling protocol will only allow a single game entity to
make a scrolling order per game iteration.

## A note about update ordering:

This protocol is designed around the assumption that whichever entity issues a
scrolling order, then among all of the game entities participating in scrolling,
the "ordering entity" will have had its `update` method called by the `Engine`
first. This is because it is up to participating entities to update their
`curtain`s or `position`s to account for scrolling during the same game
iteration in which a scrolling order is made, and if an order is made _after_
another entity's `update` method has been called, then that entity will never
get the chance to do this.

For related reasons, it's anticipated that a scrolling order's "ordering entity"
will occupy a distinct and earlier update group (see discussion at the `Engine`
docstring) than the other egocentric game entities participating in scrolling.
Otherwise, it may be difficult for game entities to look at the game board
(which would probably show the last game iteration) and figure out which moves
will be legal during the next game iteration.

That said, in both of these warnings, the author may very well underestimate the
cleverness of pycolab game developers, who may discover new and ingenious ways
of using this protocol.

In case they don't, the official recommendation about update ordering is this:
whichever entity makes the orders gets updated first, non-egocentric entities
should get updated before egocentric ones do, and remaining egocentric entities
should live in a separate, later update group than the "ordering entity".

## Scrolling groups:

Most games may only have one "kind" of scrolling: the world scrolling around,
for example. The discussion so far and all of the function defaults are
engineered around this use case.

This said, all functions allow the specification of an optional string tag that
directs the function to work in the context of a "scrolling group" associated
with that tag. Each scrolling group operates exactly as described in the
preceding discussion, almost completely independently of any other scrolling
group.

There is just one exception to this independence: a pycolab game entity may
belong to at most one scrolling group. Protocol functions attempt to enforce
this restriction where possible.

## On the loose interpretation of "legal" scrolling motions:

With apologies... please consider the following circumstance. Within this
game board:

    .....
    #..#.
    ..P#.
    ..##.

`P` denotes an egocentric `Sprite` and `#` marks an obstacle within the game's
scrolling scenery. Replicating the dynamics of famous video games, we would only
like the game board to scroll if it *has* to---in this case, if the `Sprite`
would otherwise occupy the first/last row/column of the game board. So, the
board would not scroll if the `Sprite` moved upward or leftward, but would
certainly scroll if the `Sprite` moved downward (of course, in this case, an
obstacle is in the way).

What if the `Sprite` moved downward *and* leftward: "to the southwest", so to
speak?

The most minimal and natural scrolling behaviour would see the board scroll
downward only, i.e.

    #..#.
    ...#.
    .P##.
    .....

since there is room for the `Sprite` to also move leftward without impinging on
the first column of the game board. Unfortunately, the `Sprite` would never have
explicitly permitted a downward scrolling motion, since naively scrolling the
game board downward would scroll `P` into the wall that was just beneath it.

The disappointing solution to this conundrum is to permit an annoyingly subtle
flexibility in the interpretation of "legal" scrolling motions. A game entity
may issue an "illegal" scrolling order if it can be *sure* that all entities
subject to that order will remain on the game board after:

  1. first moving themselves relative to the game board to comply with the
     scrolling order, i.e. move along with the world's scenery, THEN
  2. moving relative to the game board AND the scenery to obey whatever
     action(s) are issued by the agent.

Illustrating in the example from above, when confronted with an agent action
indicating a "southwesterly" motion, the `Drape` or `Backdrop` responsible for
the background scenery would issue a strictly downward scrolling order,
understanding that `P` could be trusted to handle the scrolling and the motion
responsibly.  When it came `P`'s turn to update itself, `P` would notionally
apply the scrolling order first, yielding

    #..#.   # note that the game scenery has already scrolled
    ..P#.
    ..##.
    .....

and then, after that, it would interpret and execute the southwesterly motion,
arriving at this board state (same as what's shown above):

    #..#.
    ...#.
    .P##.
    .....

Naturally, the coordination between entities that interpret scrolling motions
loosely in this way will have to be even tighter than the basic semantics
encoded by this protocol. Notably, `prefab_parts.drapes.Scrolly` and egocentric
`prefab_parts.sprites.MazeWalker` entities do work together in this way,
provided that the very same motion action helper methods are called on these
entities at every game iteration.

## Representation within the `Plot` object:

For this section, it helps to know that the name of the default scrolling group
is `''` (the empty string).

Although you should hopefully never need to examine `Plot` object entries
relating to the scrolling protocol directly (i.e. in lieu of using this module's
functions), the following dict entries in the `Plot` object are what the
functions work with behind the scenes:

`the_plot['scrolling_everyone']`: a mapping from pycolab game entity objects
  participating in scrolling to the string identifiers of the scrolling group in
  which they participate. Since non-egocentric entities don't have to register
  with this module, the mapping may not be complete, but as soon as an entity
  calls `get_order`, it will be added.

`the_plot['scrolling_X_egocentrists']`: the set of pycolab game entity objects,
  belonging to scrolling group X, that participate in scrolling in an egocentric
  way.

`the_plot['scrolling_X_order']`: a 2-tuple containing scrolling directions to be
  obeyed by all participants in scrolling group X. These directions are the
  number of rows and the number of columns that the game window will move over
  the world, conceptually speaking, with positive row values meaning that the
  window moves downward, and positive column values meaning that the window
  moves rightward. Non-egocentric entities should therefore *subtract* these
  values from their own internal screen-relative coordinates so that they appear
  to move along with the rest of the world.

`the_plot['scrolling_X_order_frame']`: the number of the game iteration to which
  `the_plot['scrolling_X_order']` applies. If
  `the_plot.frame != the_plot['scrolling_X_order_frame']`, the order should be
  ignored.

`the_plot['scrolling_X_permitted']`: a mapping from egocentric pycolab game
  entity objects in scrolling group X to a set of scrolling order 2-tuples that
  will not result in the entity being "moved" in an impossible way.

`the_plot['scrolling_X_permitted_frame']`: a mapping from egocentric
  pycolab game entity objects in scrolling group X to the number of the game
  iteration to which the information in `the_plot['scrolling_X_permitted']`
  applies. If
  `the_plot.frame != the_plot['scrolling_X_permitted_frame'][entity]`, then
  the scrolling protocol will assume that no motion is permissible for `entity`.

## Even more nitty-gritty details:

One final caveat, since you've probably had enough reading: unless great care is
taken, it is likely to be a bad idea to issue an `order` on the very first
iteration of a game (i.e.  during the `Engine.its_showtime` call). Barring
"unusual" update orders, none of the other scrolling participants will have had
a chance to register themselves as egocentric or to say which directions will be
safe to scroll during the iteration. The `order` call is likely to succeed, but
there is a chance that one of the egocentric entities will be forced into an
illegal location before it even has a chance to live.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pycolab import things


# Some predefined scrolling motions. These motions are the number of rows and
# the number of columns that the game window will move over the world,
# conceptually speaking, with positive row values meaning that the window moves
# downward, and positive column values meaning that the window moves rightward.
# Non-egocentric entities should therefore *subtract* these values from their
# own internal screen-relative coordinates so that they appear to move along
# with the rest of the world.
NORTH = (-1, 0)
NORTHEAST = (-1, 1)
EAST = (0, 1)
SOUTHEAST = (1, 1)
SOUTH = (1, 0)
SOUTHWEST = (1, -1)
WEST = (0, -1)
NORTHWEST = (-1, -1)


class Error(RuntimeError):
  """An exception for mishandling of scrolling protocol functions.

  Clients of this protocol may also express this error when a scrolling-related
  error arises.
  """


def participate_as_egocentric(entity, the_plot, scrolling_group=''):
  """Register `entity` as egocentric with respect to the scrolling group.

  Once registered, any entity that wishes to check or issue a scrolling order
  will need to make certain that scrolling the world "around" this entity will
  not wind up making the entity execute an impossible move. (See `permit`,
  `is_possible` and `order`.)

  There is no harm in registering more than once, as long as `scrolling_group`
  remains the same.

  Args:
    entity: the pycolab game entity we wish to register as egocentric.
    the_plot: the pycolab game's `Plot` object.
    scrolling_group: a string identifier for the scrolling group with respect to
        which we are marking `entity` as egocentric.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`.
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)
  egocentrists = the_plot.setdefault(
      'scrolling_{}_egocentrists'.format(scrolling_group), set())
  egocentrists.add(entity)


def egocentric_participants(entity, the_plot, scrolling_group=''):
  """Get all entities registered egocentric with respect to `scrolling_group`.

  Args:
    entity: the pycolab game entity interested in obtaining the set of
        egocentric entities within `scrolling_group`.
    the_plot: the pycolab game's `Plot` object.
    scrolling_group: a string identifier for the scrolling group that the
        caller is querying for egocentric entities.

  Returns:
    The set of all pycolab entities registered egocentric with respect to
    `scrolling_group`.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`.
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)
  return the_plot.get(
      'scrolling_{}_egocentrists'.format(scrolling_group), set())


def get_order(entity, the_plot, scrolling_group=''):
  """Retrieve the current scrolling order for `scrolling_group`, if one exists.

  Args:
    entity: the pycolab game entity retrieving the scrolling order.
    the_plot: the pycolab game's `Plot` object.
    scrolling_group: a string identifier for the scrolling group for which
        `entity` is requesting the current scrolling order.

  Returns:
    a scrolling order for the current game iteration, or None if there is none.
    If not None, this is a 2-tuple to be obeyed by all participants in
    `scrolling_group`. These directions are the number of rows and the number of
    columns that the game window will move over the world, conceptually
    speaking, with positive row values meaning that the window moves downward,
    and positive column values meaning that the window moves rightward.
    Non-egocentric entities should therefore *subtract* these values from their
    own internal screen-relative coordinates so that they appear to move along
    with the rest of the world.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`.
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)
  order_frame = the_plot.setdefault(
      'scrolling_{}_order_frame'.format(scrolling_group), None)
  if the_plot.frame != order_frame: return None
  return the_plot.setdefault(
      'scrolling_{}_order'.format(scrolling_group), None)


def permit(entity, the_plot, motions, scrolling_group=''):
  """Indicate next permissible motions for the egocentric entity `entity`.

  Although it's mentioned in the argument description, it's worth pointing out
  that these are motions that will be permissible for `entity` in the next
  game iteration, not in the current one.

  It is fine for the same entity to call this function more than once in the
  same game iteration, as long as `scrolling_group` is always the same.

  See the section "On the loose interpretation of 'legal' scrolling motions"
  for a disappointing but necessary complication of the semantics of this
  function.

  Args:
    entity: the egocentric pycolab game entity giving permission for
        certain scrolling motions during the next game iteration.
    the_plot: the pycolab game's `Plot` object.
    motions: an iterable of scrolling motions that will be allowable *during the
        next game iteration*. These motions are 2-tuples which can be
        interpreted as the (possibly negative) number of rows/columns that the
        game window is allowed to move downward/rightward over the game board;
        or, conveniently, this is a (sub?)set of valid (δrow, δcolumn) motions
        that `entity` will be able to make at the next iteration (the numbers
        are the same either way).
    scrolling_group: a string identifier for the scrolling group for which
        `entity` is granting scrolling permission.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`, or `entity` is not registered as egocentric within
        `scrolling_group`.
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)

  # Make certain this entity is an egocentric entity.
  egocentrists = the_plot.setdefault(
      'scrolling_{}_egocentrists'.format(scrolling_group), set())
  if entity not in egocentrists:
    raise Error(
        '{} is not registered as an egocentric entity in scrolling group '
        '{}'.format(_entity_string_for_errors(entity), repr(scrolling_group)))

  # This is the game iteration for which we are giving scrolling motion
  # permission.
  my_permit_frame = the_plot.frame + 1

  # See whether there is any old permission information around for this entity,
  # and clear it if so. While we're at it, update the frame number associated
  # with this entity's permission information.
  all_permit_frames = the_plot.setdefault(
      'scrolling_{}_permitted_frame'.format(scrolling_group), dict())
  all_permits = the_plot.setdefault(
      'scrolling_{}_permitted'.format(scrolling_group), dict())
  my_permits = all_permits.setdefault(entity, set())

  if all_permit_frames.setdefault(entity, my_permit_frame) != my_permit_frame:
    all_permit_frames[entity] = my_permit_frame
    my_permits.clear()

  # Add the argument motions to the set of permitted motions.
  my_permits.update(motions)


def is_possible(entity, the_plot, motion, scrolling_group=''):
  """Is a scrolling order legal for egocentric `scrolling_group` entities?

  See the section "On the loose interpretation of 'legal' scrolling motions"
  for a disappointing but necessary complication of the semantics of this
  function.

  Args:
    entity: the pycolab game entity interested in knowing whether `motion` is
        legal for `scrolling_group`. This entity should also be a participant
        in `scrolling_group`; external queries are not allowed.
    the_plot: the pycolab game's `Plot` object.
    motion: a 2-tuple to be obeyed by all participants in `scrolling_group`.
        These directions are the number of rows and the number of columns that
        the game window will move over the world, conceptually speaking, with
        positive row values meaning that the window moves downward, and positive
        column values meaning that the window moves rightward.
    scrolling_group: a string identifier for the scrolling group for which
        `entity` is attempting to validate a scrolling order.

  Returns:
      True iff all of the registered egocentric entities for `scrolling_group`
      have listed motion as a permissible motion for the current game iteration.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)

  egocentrists = the_plot.get(
      'scrolling_{}_egocentrists'.format(scrolling_group), set())
  for other_entity in egocentrists:
    # See if this other entity has supplied permitted moves for this frame.
    # If not, return False.
    permit_frames = the_plot.get(
        'scrolling_{}_permitted_frame'.format(scrolling_group), {})
    if permit_frames.get(other_entity) != the_plot.frame: return False

    # See if the motion we're interested in is allowed by the other entity.
    # If not, return False.
    permitted = the_plot.get(
        'scrolling_{}_permitted'.format(scrolling_group), dict()).get(
            other_entity, set())
    if motion not in permitted: return False

  # All egocentric entities are OK with the motion.
  return True


def order(entity, the_plot, motion, scrolling_group='', check_possible=True):
  """Issue a scrolling order for participants in `scrolling_group`.

  Args:
    entity: the pycolab game entity attempting to issue the scrolling order.
    the_plot: the pycolab game's `Plot` object.
    motion: a 2-tuple to be obeyed by all participants in `scrolling_group`.
        These directions are the number of rows and the number of columns that
        the game window will move over the world, conceptually speaking, with
        positive row values meaning that the window moves downward, and positive
        column values meaning that the window moves rightward.
    scrolling_group: a string identifier for the scrolling group for which
        `entity` is attempting to issue a scrolling order.
    check_possible: if True, perform a check that ensures that `motion` is
        compatible with all participants in `scrolling_group`.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`; a scrolling order has already been issued for
        `scrolling_group` at this game iteration; or `motion` is not a scrolling
        motion that is permitted by all egocentric members of `scrolling_group`.
  """
  _check_scrolling_group(entity, the_plot, scrolling_group)

  # Check that the scrolling order is permitted by all of the egocentric
  # participants in this scrolling group, and that no other scrolling order has
  # been set for this game iteration.
  order_frame = the_plot.setdefault(
      'scrolling_{}_order_frame'.format(scrolling_group), None)
  if order_frame == the_plot.frame:
    raise Error(
        '{} attempted to issue a second scrolling order for scrolling group {}.'
        ''.format(_entity_string_for_errors(entity), repr(scrolling_group)))
  if (check_possible and
      not is_possible(entity, the_plot, motion, scrolling_group)):
    raise Error(
        '{} attempted to order an impossible scrolling motion "{}" for '
        'scrolling group {}.'.format(_entity_string_for_errors(entity), motion,
                                     repr(scrolling_group)))

  # Put the scrolling order for this scrolling group in place.
  the_plot['scrolling_{}_order_frame'.format(scrolling_group)] = the_plot.frame
  the_plot['scrolling_{}_order'.format(scrolling_group)] = motion


### Private helpers ###


def _check_scrolling_group(entity, the_plot, scrolling_group):
  """Raise Error if `entity` is in a different scrolling group than the arg.

  This function also handles all aspects of managing the registry that maps
  pycolab entities to scrolling groups.

  Args:
    entity: the pycolab game entity against whose scrolling group affiliation
        we are going to compare `scrolling_group`.
    the_plot: the pycolab game's `Plot` object.
    scrolling_group: a string identifier for the scrolling group to which we are
        making certain `entity` belongs.

  Raises:
    TypeError: `entity` is not a pycolab entity.
    Error: `entity` is known to belong to a scrolling group distinct from
        `scrolling_group`.
  """
  # We could make this a decorator, but then we'd have to go to some trouble
  # to handle default arguments.

  if not isinstance(entity, (things.Backdrop, things.Drape, things.Sprite)):
    raise TypeError('an object that was not a pycolab game entity ({}) '
                    'attempted to use the scrolling protocol.'.format(entity))

  scrolling_groups = the_plot.setdefault('scrolling_everyone', {})
  last_scrolling_group = scrolling_groups.setdefault(entity, scrolling_group)
  if scrolling_group != last_scrolling_group:
    raise Error('{} has attempted to participate in the scrolling protocol as '
                'part of scrolling group {}, but is already known to belong to '
                'scrolling group {}.'.format(
                    _entity_string_for_errors(entity),
                    repr(scrolling_group), repr(last_scrolling_group)))


def _entity_string_for_errors(entity):
  """Derive a string describing `entity` for use in error messages."""
  try:
    character = entity.character
    return 'a Sprite or Drape handling character {}'.format(repr(character))
  except AttributeError:
    return 'the Backdrop'
