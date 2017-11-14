# Some frequently-asked questions about pycolab

### 1. How can a game return more data beyond observation/reward/discount?

Some pycolab applications want to return more data to the caller of
`Engine.play()` than what this method returns---for example, auxiliary rewards
or statistics for monitoring. The canonical way to do this is to place the extra
data in the game's `Plot` object; the caller can then retrieve the `Plot` and
the data inside via the `Engine.the_plot` attribute.

### 2. How do I disable occlusion in the `layers` argument to `update()`?

You can't, but there's an easy workaround.

The `layers` dict supplied to the `update()` methods of Sprites and Drapes show
where different characters appear on the game board. For example, if you have
two Drapes on the game board, A and B, and they look like this:

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

If you'd like have a look at all of A, don't look in `layers`. Instead, look
at A's curtain directly through the `things` argument to `update`:
`things['A'].curtain`. Note that this will only work for Drapes; Sprites don't
express a curtain, only a (row, column) screen position under the `position`
attribute. Hopefully this will be useful for locating an occluded sprite.
