#!/usr/bin/env python3
"""
Pantheon Pact Tree Optimal Build Solver
========================================
Finds the highest-scoring valid build for each pact point budget across all 6 god roots.

Usage:
    python3 pantheon_solver.py [pantheon_data.json]

Requirements:
    pip install pulp

How it works:
    - Uses Integer Linear Programming (ILP) via PuLP/CBC for exact optimal solutions.
    - Prerequisites use OR semantics: to purchase a node, at least ONE of its listed
      prerequisites must already be purchased. This matches the game's visual perk grid,
      where cyclic prerequisite lists define adjacency rather than a strict dependency DAG.
    - The 6 floating no-prerequisite nodes (Blindbag, Goliath's Reach, Berserker,
      Stalwart, Pious Penetrator, Bandos's Wrath) are freely purchasable alongside
      any god root.
    - God roots are mutually exclusive (exclusive_alignment).
"""

import json
import sys
import time
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, value, PULP_CBC_CMD

# ---------------------------------------------------------------------------
# Scoring weights — edit these to match your playstyle
# ---------------------------------------------------------------------------
#
# Preset options (uncomment one block):
#
# --- MELEE DPS ---
WEIGHTS = {
    'perk_graph_effect:pantheon_melee_max_hit_pct':               3.0,
    'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   2.0,
    'perk_graph_effect:pantheon_crit_damage_pct':                 2.0,
    'perk_graph_effect:pantheon_min_hit_flat':                    1.5,
    'perk_graph_effect:pantheon_lifesteal_pct':                   0.8,
    'perk_graph_effect:pantheon_flat_damage_reduction_pct':       0.3,
    'perk_graph_effect:pantheon_max_hp_flat':                     0.1,
    'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       0.3,
    'perk_graph_effect:pantheon_ranged_max_hit_pct':              0.0,
    'perk_graph_effect:pantheon_magic_max_hit_pct':               0.0,
    'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 0.0,
    'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
}

# --- RANGED DPS ---
# WEIGHTS = {
#     'perk_graph_effect:pantheon_ranged_max_hit_pct':              3.0,
#     'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   2.0,
#     'perk_graph_effect:pantheon_crit_damage_pct':                 2.0,
#     'perk_graph_effect:pantheon_min_hit_flat':                    1.5,
#     'perk_graph_effect:pantheon_lifesteal_pct':                   0.8,
#     'perk_graph_effect:pantheon_flat_damage_reduction_pct':       0.3,
#     'perk_graph_effect:pantheon_max_hp_flat':                     0.1,
#     'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       0.3,
#     'perk_graph_effect:pantheon_melee_max_hit_pct':               0.0,
#     'perk_graph_effect:pantheon_magic_max_hit_pct':               0.0,
#     'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 0.0,
#     'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
# }

# --- MAGIC DPS ---
# WEIGHTS = {
#     'perk_graph_effect:pantheon_magic_max_hit_pct':               3.0,
#     'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   2.0,
#     'perk_graph_effect:pantheon_crit_damage_pct':                 2.0,
#     'perk_graph_effect:pantheon_min_hit_flat':                    1.5,
#     'perk_graph_effect:pantheon_lifesteal_pct':                   0.8,
#     'perk_graph_effect:pantheon_flat_damage_reduction_pct':       0.3,
#     'perk_graph_effect:pantheon_max_hp_flat':                     0.1,
#     'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       0.3,
#     'perk_graph_effect:pantheon_melee_max_hit_pct':               0.0,
#     'perk_graph_effect:pantheon_ranged_max_hit_pct':              0.0,
#     'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 0.0,
#     'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
# }

# --- HYBRID ALL-STYLES DPS ---
# WEIGHTS = {
#     'perk_graph_effect:pantheon_melee_max_hit_pct':               1.5,
#     'perk_graph_effect:pantheon_ranged_max_hit_pct':              1.5,
#     'perk_graph_effect:pantheon_magic_max_hit_pct':               1.5,
#     'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   2.0,
#     'perk_graph_effect:pantheon_crit_damage_pct':                 2.0,
#     'perk_graph_effect:pantheon_min_hit_flat':                    1.0,
#     'perk_graph_effect:pantheon_lifesteal_pct':                   0.8,
#     'perk_graph_effect:pantheon_flat_damage_reduction_pct':       0.3,
#     'perk_graph_effect:pantheon_max_hp_flat':                     0.1,
#     'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       0.3,
#     'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 0.0,
#     'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
# }

# --- HAMMERDIN (prayer bonus) ---
# WEIGHTS = {
#     'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 1.5,
#     'perk_graph_effect:pantheon_melee_max_hit_pct':               1.0,
#     'perk_graph_effect:pantheon_min_hit_flat':                    0.5,
#     'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       1.2,
#     'perk_graph_effect:pantheon_lifesteal_pct':                   0.5,
#     'perk_graph_effect:pantheon_flat_damage_reduction_pct':       0.3,
#     'perk_graph_effect:pantheon_max_hp_flat':                     0.1,
#     'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   0.5,
#     'perk_graph_effect:pantheon_ranged_max_hit_pct':              0.0,
#     'perk_graph_effect:pantheon_magic_max_hit_pct':               0.0,
#     'perk_graph_effect:pantheon_crit_damage_pct':                 0.3,
#     'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
# }

# --- TANK/SURVIVABILITY ---
# WEIGHTS = {
#     'perk_graph_effect:pantheon_flat_damage_reduction_pct':       3.0,
#     'perk_graph_effect:pantheon_max_hp_flat':                     2.0,
#     'perk_graph_effect:pantheon_lifesteal_pct':                   2.0,
#     'perk_graph_effect:pantheon_combat_prayer_regen_5tick':       1.0,
#     'perk_graph_effect:pantheon_min_hit_flat':                    0.3,
#     'perk_graph_effect:pantheon_melee_max_hit_pct':               0.3,
#     'perk_graph_effect:pantheon_balance_all_styles_damage_pct':   0.5,
#     'perk_graph_effect:pantheon_ranged_max_hit_pct':              0.0,
#     'perk_graph_effect:pantheon_magic_max_hit_pct':               0.0,
#     'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 0.0,
#     'perk_graph_effect:pantheon_crit_damage_pct':                 0.0,
#     'perk_graph_effect:pantheon_pet_damage_pct':                  0.0,
# }

# ---------------------------------------------------------------------------
# Budget tiers to solve for
# ---------------------------------------------------------------------------
BUDGETS = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]

# ILP time limit per (root, budget) solve in seconds
ILP_TIME_LIMIT = 15

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
data_path = sys.argv[1] if len(sys.argv) > 1 else 'pantheon_data.json'
with open(data_path) as f:
    data = json.load(f)

node_list = data['variant']['nodes']
nodes      = {n['id']: n for n in node_list}
prereq     = {n['id']: list(n.get('prerequisites', [])) for n in node_list}
cost_map   = {n['id']: n['pointCost'] for n in node_list}

GOD_ROOTS    = {1, 2, 3, 4, 5, 6}
ALL_NODE_IDS = list(nodes.keys())

# ---------------------------------------------------------------------------
# Scoring helper
# ---------------------------------------------------------------------------
def node_score(nid: int) -> float:
    return sum(
        WEIGHTS.get(e['effectRowId'], 0) * e['value']
        for e in nodes[nid].get('effects', [])
    )

# ---------------------------------------------------------------------------
# ILP solver for one (root, budget) pair
# ---------------------------------------------------------------------------
def solve_ilp(root: int, budget: int):
    """
    Returns (selected_frozenset, score) or (None, -1) on failure.

    Constraints:
      - Exactly this god root is selected; other god roots are excluded.
      - Budget: sum of point costs <= budget.
      - OR connectivity: for each node N with prerequisites,
            x[N] <= sum(x[p] for p in prereq[N])
        meaning N can only be bought if at least one neighbour is already bought.
        Nodes with no prerequisites (god roots + the 6 standalone floating nodes)
        are unconstrained and freely purchasable.
    """
    prob = LpProblem(f"r{root}_b{budget}", LpMaximize)
    x = {nid: LpVariable(f"x_{nid}", cat='Binary') for nid in ALL_NODE_IDS}

    # Objective
    prob += lpSum(node_score(nid) * x[nid] for nid in ALL_NODE_IDS)

    # God root constraints
    prob += x[root] == 1
    for r in GOD_ROOTS:
        if r != root:
            prob += x[r] == 0

    # Budget
    prob += lpSum(cost_map[nid] * x[nid] for nid in ALL_NODE_IDS) <= budget

    # OR-connectivity: x[N] <= sum of its prerequisites
    for nid in ALL_NODE_IDS:
        pre = prereq.get(nid, [])
        if not pre:
            continue          # standalone / god root — no constraint needed
        if nid in GOD_ROOTS:
            continue          # already handled above
        prob += x[nid] <= lpSum(x[p] for p in pre if p in x)

    prob.solve(PULP_CBC_CMD(msg=0, timeLimit=ILP_TIME_LIMIT))

    if prob.status != 1:
        return None, -1

    selected = frozenset(
        nid for nid in ALL_NODE_IDS
        if value(x[nid]) is not None and value(x[nid]) > 0.5
    )
    return selected, sum(node_score(nid) for nid in selected)

# ---------------------------------------------------------------------------
# Main solve loop
# ---------------------------------------------------------------------------
print("Solving optimal builds for all roots and budgets...\n")
best = {b: (-1.0, None, frozenset()) for b in BUDGETS}

for root in sorted(GOD_ROOTS):
    t0 = time.time()
    for b in BUDGETS:
        build, score = solve_ilp(root, b)
        if build is not None and score > best[b][0]:
            best[b] = (score, root, build)
    print(f"  Root {root:>2} ({nodes[root]['displayName']:<22}): {time.time() - t0:.1f}s")

# ---------------------------------------------------------------------------
# Output results
# ---------------------------------------------------------------------------
PLANNER_BASE = "https://august-rsps.com/perk-planner?v=pantheon&n="

print("\n" + "=" * 130)
print(f"{'Budget':>6} | {'Best God Root':>22} | {'Score':>7} | {'Cost':>4} | {'Nodes':>5} | Key perks (weighted effects)")
print("=" * 130)

for b in BUDGETS:
    scr, root, build = best[b]
    if not build:
        print(f"{b:>6} | No valid build found")
        continue

    total_cost = sum(cost_map[nid] for nid in build)
    ids        = sorted(build)
    url        = PLANNER_BASE + ','.join(map(str, ids))

    # Aggregate effect totals across all nodes in the build
    perk_totals: dict[str, float] = {}
    for nid in build:
        for eff in nodes[nid].get('effects', []):
            k = eff['effectRowId'].replace('perk_graph_effect:pantheon_', '')
            perk_totals[k] = perk_totals.get(k, 0) + eff['value']

    # Show up to 5 perks with non-zero weight and non-zero value, sorted by weighted contribution
    relevant = {
        k: v for k, v in perk_totals.items()
        if WEIGHTS.get(f'perk_graph_effect:pantheon_{k}', 0) > 0 and v > 0
    }
    top = sorted(
        relevant.items(),
        key=lambda kv: -WEIGHTS.get(f'perk_graph_effect:pantheon_{kv[0]}', 1) * kv[1]
    )[:5]
    perk_str = '  |  '.join(f'{k}={v:.0f}' for k, v in top)

    print(f"\n{b:>6} | {nodes[root]['displayName']:>22} | {scr:>7.1f} | {total_cost:>4} | {len(ids):>5} | {perk_str}")
    print(f"       | {url}")

print("\n" + "=" * 130)
print("\nDone.")
