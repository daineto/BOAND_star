# Composition theorem for the physical staircase family

This argument applies to `frozenlake_stages.grid(k, n)` for positive integer
`k` and **even `n >= 6`**. It concerns the unchanged ICAPS FrozenLake domain,
unit action costs, stationary policies and best/worst path costs. It does not
claim the same result for arbitrary connections or odd staircase sizes.

## Geometry

Before translation/padding, stage `i` starts at
`E_i=((n+10)i, ni)` and exits at `X_i=E_i+(n,n)`.
Its two ice paths share only their endpoints:

- Staircase: alternate one step up, one step right, repeated `n` times.
- Detour: left 2, up `n+2`, right `n+2`, down 2.

A connector from `X_i` to `E_(i+1)` runs right 2, down 2, right 8, up 2.
Every other tile is a wall. Only `X_(k−1)` is a goal.

Ignoring the length-two slips, the tile-neighbor graph is a chain of simple
cycles (the rooms), joined by simple paths (the connectors). The two-tile
clearance prevents other contacts. This follows directly from the coordinate
ranges: each room lies in `[x−2,x+n] × [y,y+n+2]`; a connector passes outside
both staircases, with at least one intervening wall except at its endpoints.
The same local geometry repeats for every stage. A slip follows two edges
on one straight line of this graph; it cannot cross a wall or a corner.

## Normal form of finite-worst policies

Every enabled action includes the one-tile outcome. Following only those
outcomes in a strong policy therefore gives a simple path from start to goal.
It chooses one room arm per stage and traverses the connectors forward.
Returning along a connector would revisit this path. Entering the other arm
backwards at an exit would eventually return to the entry or exit, or reverse
again within the private arm; each option creates a directed cycle.

Within a chosen arm, a reverse action includes its one- or two-tile predecessor,
whose selected forward action can reach the reversing state. That creates a
cycle. Consequently all reachable interior decisions must move forward.

There are two boundary cases because a slip can cross a junction:

1. The last connector run is collinear with the first staircase edge. When the
   entry chooses the detour, a two-tile outcome from the tile immediately below
   the entry can also reach the first staircase tile. Reversing there includes
   that same connector tile, creating a two-state cycle. This auxiliary
   staircase branch must continue forward to the exit.
2. The final staircase edge is collinear with the first connector run. A slip
   can reach the first connector tile without visiting the exit. Reversing
   there includes the staircase predecessor, also creating a two-state cycle.
   The connector must continue forward.

Those are the only slips across branch/merge vertices. Thus a strong policy is
determined, on reachable states, by its `k` entry choices. Every combination
has an acyclic forward completion. There are **`2^k` reachable strong policies**;
unreachable action assignments are not counted as different policies here.

## Exact costs, including boundary slips

A straight run of length `L` takes between `ceil(L/2)` and `L` actions.
All four detour runs are even, so its costs are `(n+4, 2n+8)`.
The isolated staircase costs `(2n, 2n)`. The connector's four even runs give
`(7,14)`.

At a staircase/connector junction, an edge of length one joins a straight run
of length two. The merged length-three run costs `(2,3)`, exactly the sum of
`(1,1)` and `(1,2)`. This holds at both ends of a connector. Therefore crossing
the labeled junction does not change either extremum relative to the sum.

The auxiliary staircase branch in case 1 above also leaves the extrema
unchanged when the entry chooses the detour. Measured from the last connector
bend two tiles below the entry:

- The detour continuation has costs `(n+5, 2n+10)`.
- Overshooting into the staircase takes two actions to its first tile, followed
  by `2n−1` staircase actions: `2n+1` in total, before the exit-side boundary
  is combined as described above.

For `n >= 6`, the auxiliary value lies between the detour's two extrema.
It cannot make the best case shorter or the worst case longer. Any exit-side
skip replaces the same length-three run, so does not invalidate this bound.
The extremal main-arm trajectories remain possible: nature may always choose
the one-tile outcomes, or the two-tile outcomes needed for each minimum.

If `j` entries choose the staircase, exact costs are therefore

```
best  = (n+11)k − 7 + (n−4)j
worst = (2n+22)k − 14 − 8j       j = 0,...,k.
```

For each additional staircase choice, best increases by `n−4 > 0` and worst
decreases by 8. These are **`k+1` distinct nondominated finite cost pairs**.
Order of choices does not affect the pair; multiplicity at point `j` is
`binomial(k,j)`.

## Why cyclic proper policies add no point

For a lower bound on any policy's best cost, allow every action and choose
its favorable outcome. Each private room arm is a path; backtracking within
it cannot shorten a route to its exit. Nor can a shortest start-to-goal route
return across a connector: the tile graph has no alternate connection around
that connector. At a junction, overshooting into the staircase is the sole
extra forward continuation, and the local calculation above makes it no
shorter than taking the detour. Overshooting and returning to that junction
cannot beat reaching it directly, which was an available outcome of the same
forward action.

The shortest possible route consequently takes the detour in every room and
has cost `(n+11)k−7`. A strong all-detour policy attains that best cost with
finite worst cost `(2n+22)k−14`. Every cyclic proper policy has best cost at
least this bound and infinite worst cost, so it is dominated by that strong
policy. The displayed finite points are the **complete** Pareto front.

## Scope of verification

The proof supplies the general claim; numerical checks are not its substitute.
Independent enumeration, original-PDDL action audits, policy replay and bounded
BOAND runs are recorded in the [scaling study](frozenlake-scaling-report.md).
The original one-to-three-stage inputs and their historical hashes remain
unchanged. Increasing `n` holds front cardinality fixed while lengthening
routes; increasing `k` increases cardinality. Neither parameter guarantees a
particular runtime or separates all sources of search difficulty.
