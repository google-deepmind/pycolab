# Some frequently-asked questions about pycolab

### 1. How can a game return more data beyond observation/reward/discount?

Some pycolab applications want to return more data to the caller of
`Engine.play()` than what this method returns---for example, auxiliary rewards
or statistics for monitoring. The canonical way to do this is to place the extra
data in the game's `Plot` object; the caller can then retrieve the `Plot` and
the data inside via the `Engine.the_plot` attribute.

### 2. How do I disable occlusion in the `layers` argument to `update()`?

There are several options.

Background: by default, the `layers` dict supplied to the `update()` methods of
Sprites and Drapes show where different characters appear on the game board. For
example, if you have two Drapes on the game board, A and B, and they look like
this:

```
   A: AAAAAA     B: BBB...
      AAAAAA        BBB...
      ......        BBB...
      ......        BBB...
```

and then if B comes after A in the `Engine`'s z-order, then the game board will
show B occluding A:

```
   BBBAAA
   BBBAAA
   BBB...
   BBB...
```

This means the 'A' and 'B' entries in the `layers` dict will look like this:

```
   A: ...XXX     B: XXX...
      ...XXX        XXX...
      ......        XXX...
      ......        XXX...
```

The easiest approach is to disable occlusion in layers when constructing your
pycolab `Engine`. See the `occlusion_in_layers` argument to the `Engine`
constructor and to `ascii_art.ascii_art_to_game()`.

Besides changing the behaviour of `layers` arguments to `update()` methods, this
approach also disables occlusion in the `layers` field of `Observation`
namedtuples returned by `engine.play()`. If this is unacceptable, there is an
easy second workaround. If you'd like have a look at all of A, don't look in
`layers`. Instead, look at A's curtain directly through the `things` argument to
`update`: `things['A'].curtain`. Note that this will only work for Drapes;
Sprites don't express a curtain, only a (row, column) screen position under the
`position` attribute. Hopefully this will be useful for locating an occluded
sprite.

### 3. What are the ways to get a game with top-down scrolling?

There are two "official" ways to do top-down, egocentric scrolling (where the
world appears to move around the player as they walk through it).

If you have a world with a fixed-size, finite map, the easiest way is to program
a pycolab game that renders the entire world as one giant observation, then to
"crop" out a smaller observation centered on the player from each observation
returned by `play()`. As the player moves, the cropped observation will follow
along, giving the impression of scrolling. The `cropping` module provides some
utility classes for this approach; the `better_scrolly_maze.py` and
`tennnnnnnnnnnnnnnnnnnnnnnnis.py` examples show these classes in use.

If you have a world with an "infinite-ish" map (for example, a game where the
scenery generates itself just-in-time as the player moves through it), or any
world where it would be impractical to render the entire world into one big
observation, one alternative approach has the game entities communicate with
each other about scrolling (e.g. "the game should scroll one row downward now")
and then update their own appearances to match. This approach is much more
complicated than the cropping technique, but also more flexible. The scrolling
protocol module (`protocols/scrolling.py`) provides utilities for game entities
to talk about scrolling through the Plot object; the `MazeWalker` Sprite and
`Scrolly` Drape in the `prefab_parts/` modules work with the scrolling protocol
out of the box; and the `scrolly_maze.py` example demonstrates this approach.
