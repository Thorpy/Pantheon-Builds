# Pantheon Pact Build Solver

A standalone Python tool that computes optimal Pantheon Pact perk trees for August RSPS, for every god, every point budget, and a handful of common playstyles — instead of eyeballing a 300+ node tree by hand.

## Why this exists

The Pantheon Pact skill tree has six gods, hundreds of interconnected perk nodes, and a hard point cap. Figuring out the *best* combination of nodes for a given budget and playstyle by hand is basically impossible — the search space is huge, some nodes are only worth taking if you've already taken others, and a handful of "obviously good" picks turn out to be traps once you actually add up the numbers. This exists to answer, definitively: *given N points and a build I care about (melee DPS, tanking, pet builds, etc.), what's the actual best set of nodes to unlock?*

## How it works

- **Data**: pulls the live perk graph straight from the game's own planner endpoint, so it's always working from the real, current node list and prerequisites — not a stale manual copy.
- **Validity**: the rules for which nodes unlock which (what counts as a valid, obtainable build) were reverse-engineered directly from the live client's own source code, not guessed from trial and error. This matters — the tree's connectivity rules are less obvious than they look at first glance.
- **Optimization**: each (god, point budget, playstyle) combination is solved as an integer linear program — think of it as the same category of math used for scheduling or logistics optimization, applied here to "which nodes give the most value without breaking the budget or picking something unreachable." A few hundred of these are solved in parallel across CPU cores, with a simpler fallback method for the rare case a solve doesn't finish in time.
- **Output**: a single self-contained HTML page with the best build for every god × budget × playstyle combination, ready to browse or share.

## Usage

```
python3 pantheon_solver.py
```

No external files needed — it fetches the current perk data itself on first run and caches it locally. Requires `pulp` (`pip install pulp`).

## Status

Playstyle weightings are a first pass and still being tuned — the underlying math and validity logic are solid, but which nodes get prioritized for a given playstyle is an ongoing calibration process, not a finished product.
