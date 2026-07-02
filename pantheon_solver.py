#!/usr/bin/env python3
"""
Pantheon Pact Tree Optimal Build Solver – Corrected v3
=======================================================
Fixes applied in this version:
  1. effectDefinitions -> effects key fix (non-stackable effects now handled correctly,
     e.g. Orbiting Hammer Max Hit now correctly caps at 150% instead of summing to 325%).
  2. Robust variant selection by slug='pantheon' instead of assuming index 0.
  3. Prerequisite override for the previously-unreachable 102/103/218/244 loop.
  4. Fixed the 279 -> 205 override, which created a NEW self-supporting 2-node loop
     with node 205 (205's real prereqs are [6, 279], so overriding 279 -> [205] let the
     two nodes "satisfy" each other without ever tracing back to a real root). 279 now
     overrides straight to the Bandos root (6), matching the pattern used for 22/23.
  5. A startup sanity check that flags if any override creates this kind of loop again.
  6. Fallback-to-greedy is now logged, so any remaining ILP/greedy mismatches are visible
     instead of silent.
  7. Removed the inaccurate "Sara and Bandos share 312 of 314 nodes" note (verified false
     against the actual data: only 15 nodes are shared between the two root's reachable sets).
"""

import json
import sys
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, value, PULP_CBC_CMD

# ---------------------------------------------------------------------------
# ARCHETYPE WEIGHT PRESETS (unchanged)
# ---------------------------------------------------------------------------
ARCHETYPE_WEIGHTS = {
    "Melee DPS": {
        'perk_graph_effect:pantheon_melee_max_hit_pct': 3.0,
        'perk_graph_effect:pantheon_crit_damage_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 1.5,
        'perk_graph_effect:pantheon_lifesteal_pct': 1.0,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 0.5,
        'perk_graph_effect:pantheon_max_hp_flat': 0.1,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 0.3,
        'perk_graph_effect:pantheon_melee_crit_chance_pct': 0.5,
        'perk_graph_effect:pantheon_defence_stat_bonus_flat': 0.3,
        'perk_graph_effect:pantheon_blindbag_proc_chance_pct': 1.0,
        'perk_graph_effect:pantheon_berserker_dmg_pct': 1.0,
        'perk_graph_effect:pantheon_giant_slayer_per_tile_pct': 1.0,
    },
    "Ranged DPS": {
        'perk_graph_effect:pantheon_ranged_max_hit_pct': 3.0,
        'perk_graph_effect:pantheon_crit_damage_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 1.5,
        'perk_graph_effect:pantheon_lifesteal_pct': 1.0,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 0.5,
        'perk_graph_effect:pantheon_max_hp_flat': 0.1,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 0.3,
        'perk_graph_effect:pantheon_ranged_crit_chance_pct': 0.5,
        'perk_graph_effect:pantheon_strongpull_longbow_damage_pct': 1.0,
        'perk_graph_effect:pantheon_heavyloose_2h_ranged_damage_pct': 1.0,
        'perk_graph_effect:pantheon_sniper_distance_damage_pct': 1.0,
        'perk_graph_effect:pantheon_eye_distance_damage_pct': 1.0,
        'perk_graph_effect:pantheon_ricochet_echo_chance_pct': 1.0,
        'perk_graph_effect:pantheon_bbb_max_hit_chance_pct': 1.0,
    },
    "Magic DPS": {
        'perk_graph_effect:pantheon_magic_max_hit_pct': 3.0,
        'perk_graph_effect:pantheon_crit_damage_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 1.5,
        'perk_graph_effect:pantheon_lifesteal_pct': 1.0,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 0.5,
        'perk_graph_effect:pantheon_max_hp_flat': 0.1,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 0.3,
        'perk_graph_effect:pantheon_magic_crit_chance_pct': 0.5,
        'perk_graph_effect:pantheon_crackling_staff_tick_reduction_flat': 2.0,
        'perk_graph_effect:pantheon_chaos_caster_echoes_per_cast_flat': 2.0,
        'perk_graph_effect:pantheon_forsaken_pact_spell_dmg_pct': 2.0,
        'perk_graph_effect:pantheon_elemental_mastery_dmg_pct': 2.0,
        'perk_graph_effect:pantheon_blood_mastery_dmg_pct': 2.0,
        'perk_graph_effect:pantheon_vs_burning_magic_max_hit_pct': 1.0,
        'perk_graph_effect:pantheon_vs_frozen_magic_max_hit_pct': 1.0,
    },
    "Hammer / Prayer": {
        'perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct': 8.0,
        'perk_graph_effect:pantheon_melee_max_hit_pct': 3.5,
        'perk_graph_effect:pantheon_prayer_bonus_flat': 3.0,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 2.0,
        'perk_graph_effect:pantheon_lifesteal_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 2.0,
        'perk_graph_effect:pantheon_prayer_drain_reduction_pct': 1.5,
        'perk_graph_effect:pantheon_crit_damage_pct': 1.5,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 1.0,
        'perk_graph_effect:pantheon_combat_prayer_regen_12tick': 0.8,
        'perk_graph_effect:pantheon_kill_prayer_restore_flat': 0.8,
        'perk_graph_effect:pantheon_melee_crit_chance_pct': 0.5,
        'perk_graph_effect:pantheon_prayer_penetration_pct': 0.5,
        'perk_graph_effect:pantheon_defence_stat_bonus_flat': 0.3,
        'perk_graph_effect:pantheon_max_hp_flat': 0.2,
    },
    "Berserker": {
        'perk_graph_effect:pantheon_melee_max_hit_pct': 3.0,
        'perk_graph_effect:pantheon_berserker_dmg_pct': 4.0,
        'perk_graph_effect:pantheon_blindbag_proc_chance_pct': 2.0,
        'perk_graph_effect:pantheon_giant_slayer_per_tile_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 2.0,
        'perk_graph_effect:pantheon_lifesteal_pct': 2.0,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 1.0,
        'perk_graph_effect:pantheon_crit_damage_pct': 1.5,
        'perk_graph_effect:pantheon_melee_crit_chance_pct': 0.5,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 0.5,
        'perk_graph_effect:pantheon_max_hp_flat': 0.3,
        'perk_graph_effect:pantheon_cheat_death_chance_pct': 3.0,
        'perk_graph_effect:pantheon_berserker_echo_chance_pct': 2.0,
        'perk_graph_effect:pantheon_flurry_chance_pct': 2.0,
        'perk_graph_effect:pantheon_prayer_penetration_pct': 0.5,
    },
    "Sustain / Tank": {
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 3.0,
        'perk_graph_effect:pantheon_defence_stat_bonus_flat': 1.5,
        'perk_graph_effect:pantheon_max_hp_flat': 1.0,
        'perk_graph_effect:pantheon_lifesteal_pct': 2.0,
        'perk_graph_effect:pantheon_reflect_damage_pct': 2.0,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 1.5,
        'perk_graph_effect:pantheon_prayer_drain_reduction_pct': 1.0,
        'perk_graph_effect:pantheon_kill_prayer_restore_flat': 0.5,
        'perk_graph_effect:pantheon_min_hit_flat': 0.5,
        'perk_graph_effect:pantheon_melee_max_hit_pct': 0.5,
        'perk_graph_effect:pantheon_balance_all_styles_damage_pct': 0.5,
    },
    "Summoner / Pet": {
        'perk_graph_effect:pantheon_pet_damage_pct': 4.0,
        'perk_graph_effect:pantheon_pet_lifesteal_pct': 2.0,
        'perk_graph_effect:pantheon_soul_tutelage_pet_damage_xp_pct': 1.0,
        'perk_graph_effect:pantheon_tithe_summon_damage_pct': 3.0,
        'perk_graph_effect:pantheon_legion_summon_damage_pct': 3.0,
        'perk_graph_effect:pantheon_conduit_per_summon_damage_pct': 3.0,
        'perk_graph_effect:pantheon_crimson_bond_summon_lifesteal_pct': 2.0,
        'perk_graph_effect:pantheon_empowered_pet_max_hit_pct': 2.0,
        'perk_graph_effect:pantheon_soul_stoking_per_summon_boss_pet_damage_pct': 2.0,
    },
    "Slayer / Hybrid": {
        'perk_graph_effect:pantheon_melee_max_hit_pct': 2.0,
        'perk_graph_effect:pantheon_ranged_max_hit_pct': 2.0,
        'perk_graph_effect:pantheon_magic_max_hit_pct': 2.0,
        'perk_graph_effect:pantheon_balance_all_styles_damage_pct': 2.0,
        'perk_graph_effect:pantheon_slayer_helm_buff_pct': 3.0,
        'perk_graph_effect:pantheon_crit_damage_pct': 2.0,
        'perk_graph_effect:pantheon_min_hit_flat': 1.5,
        'perk_graph_effect:pantheon_lifesteal_pct': 1.0,
        'perk_graph_effect:pantheon_flat_damage_reduction_pct': 1.0,
        'perk_graph_effect:pantheon_prayer_penetration_pct': 1.5,
        'perk_graph_effect:pantheon_combat_prayer_regen_5tick': 1.0,
        'perk_graph_effect:pantheon_defence_stat_bonus_flat': 0.5,
        'perk_graph_effect:pantheon_max_hp_flat': 0.3,
    },
}

# ---------------------------------------------------------------------------
BUDGETS = list(range(5, 151, 5))
TIME_LIMIT = 60

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
data_path = sys.argv[1] if len(sys.argv) > 1 else 'pantheon_data.json'
with open(data_path) as f:
    data = json.load(f)

# FIXED: select variant by slug, not by assuming index 0 (the file also contains
# a 'clue_rewards' variant; relying on ordering is fragile).
try:
    variant = next(v for v in data['variants'] if v['slug'] == 'pantheon')
except StopIteration:
    print("Error: 'pantheon' variant not found in data.")
    sys.exit(1)

node_list = variant['nodes']
nodes      = {n['id']: n for n in node_list}
prereq     = {n['id']: list(n.get('prerequisites', [])) for n in node_list}
cost_map   = {n['id']: n['pointCost'] for n in node_list}
size_map   = {n['id']: n['size'] for n in node_list}

# FIXED: the correct top-level key is 'effects', not 'effectDefinitions'.
# Previously this always evaluated to {}, so effect_defs.get(rid, True) was always
# True and every effect (even those marked "stackable": false) was summed instead
# of capped at its max tier. This is what caused e.g. Orbiting Hammer Max Hit to
# show 325% instead of the real cap of 150%.
effect_defs = {e['rowId']: e.get('stackable', True) for e in data.get('effects', [])}

GOD_ROOTS    = {1, 2, 3, 4, 5, 6}
ALL_NODE_IDS = list(nodes.keys())

# ---------------------------------------------------------------------------
# TEMPORARY PREREQUISITE OVERRIDES FOR FLOATING / UNREACHABLE NODES
# These should be removed once the game data is fixed.
# ---------------------------------------------------------------------------
PREREQ_OVERRIDES = {
    22: [6],    # Blindbag -> Bandos root
    23: [6],    # Goliath's Reach -> Bandos root
    24: [23],   # Berserker -> Goliath's Reach
    175: [174], # Stalwart -> Stalwart 3
    239: [100], # Pious Penetrator -> Pious Penetrator 3
    279: [6],   # Bandos's Wrath -> Bandos root.
                # NOTE: this used to be [205], but node 205's real prerequisites are
                # [6, 279] -- i.e. 205 already lists 279 as one of its own OR-options.
                # Overriding 279 -> [205] created a brand-new 2-node loop (205 needs
                # "6 OR 279", 279 needs "205") that could satisfy itself without ever
                # tracing back to a real root. The ILP was exploiting this on ~95% of
                # solves, getting invalidated by is_valid_build(), and silently falling
                # back to the (weaker) greedy heuristic almost every time. Anchoring
                # 279 straight to root 6 (same pattern as 22/23) breaks the loop.
    244: [243], # Pious Penetrator 6 -> Pious Penetrator 5
                # (breaks the previously fully-isolated 102 -> 218 -> 244 -> 103 -> 102 loop)
}

# Apply overrides
for nid, new_pre in PREREQ_OVERRIDES.items():
    if nid in prereq:
        prereq[nid] = new_pre

# ---------------------------------------------------------------------------
# Sanity check: make sure no override recreates a self-supporting loop, i.e.
# an override target that itself (directly) lists the node being overridden
# as one of ITS prerequisites. This is exactly the bug that 279->[205] had.
# ---------------------------------------------------------------------------
def _check_overrides_for_new_loops():
    problems = []
    for nid, new_pre in PREREQ_OVERRIDES.items():
        for p in new_pre:
            original_pre_of_p = nodes.get(p, {}).get('prerequisites', [])
            if nid in original_pre_of_p:
                problems.append((nid, p))
    if problems:
        print("WARNING: the following overrides recreate a mutual-support loop:")
        for nid, p in problems:
            print(f"  override {nid} -> [{p}], but node {p}'s own prerequisites already include {nid}")
    return problems

_check_overrides_for_new_loops()

# ---------------------------------------------------------------------------
# Compute a tight upper bound on real prerequisite-chain depth (used as the
# "big-M" in the rank-ordering ILP constraints below). Using the true graph
# depth instead of the total node count keeps the ILP numerically tight.
# ---------------------------------------------------------------------------
def _compute_max_chain_depth():
    from collections import deque
    children = {nid: [] for nid in ALL_NODE_IDS}
    for nid in ALL_NODE_IDS:
        for p in prereq.get(nid, []):
            children.setdefault(p, []).append(nid)
    max_depth = 0
    for root in GOD_ROOTS:
        depth = {root: 0}
        q = deque([root])
        while q:
            cur = q.popleft()
            for child in children.get(cur, []):
                if child not in depth:
                    depth[child] = depth[cur] + 1
                    q.append(child)
        if depth:
            max_depth = max(max_depth, max(depth.values()))
    return max_depth

MAX_CHAIN_DEPTH = _compute_max_chain_depth()

# ---------------------------------------------------------------------------
# Verification – no floating nodes (except roots)
# ---------------------------------------------------------------------------
def is_valid_build(selected, root):
    if root not in selected:
        return False
    for nid in selected:
        if nid == root:
            continue
        pre = prereq.get(nid, [])
        if not pre:
            return False  # non‑root floating node forbidden
        sz = size_map.get(nid, 'medium')
        if sz in ('keystone', 'capstone'):
            if not all(p in selected for p in pre):
                return False
        else:
            if not any(p in selected for p in pre):
                return False

    reachable = {root}
    changed = True
    while changed:
        changed = False
        for nid in selected:
            if nid in reachable:
                continue
            pre = prereq.get(nid, [])
            if not pre:
                continue
            sz = size_map.get(nid, 'medium')
            if sz in ('keystone', 'capstone'):
                if all(p in reachable for p in pre):
                    reachable.add(nid)
                    changed = True
            else:
                if any(p in reachable for p in pre):
                    reachable.add(nid)
                    changed = True
    return selected == reachable

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def get_all_prereqs(nid, visited=None):
    if visited is None:
        visited = set()
    if nid in visited:
        return visited
    visited.add(nid)
    for p in prereq.get(nid, []):
        get_all_prereqs(p, visited)
    return visited

def precompute_marginal_scores(weights):
    node_marginal_score = {}
    for nid in ALL_NODE_IDS:
        score = 0.0
        for eff in nodes[nid].get('effects', []):
            rid = eff['effectRowId']
            val = eff['value']
            w = weights.get(rid, 0)
            if w == 0:
                continue
            if effect_defs.get(rid, True):
                score += w * val
            else:
                all_pre = get_all_prereqs(nid) - {nid}
                best_pre_val = 0.0
                for p in all_pre:
                    for peff in nodes[p].get('effects', []):
                        if peff['effectRowId'] == rid:
                            best_pre_val = max(best_pre_val, peff['value'])
                marginal = max(0.0, val - best_pre_val)
                score += w * marginal
        node_marginal_score[nid] = score
    return node_marginal_score

def aggregate_effects(selected_ids):
    totals = {}
    for nid in selected_ids:
        for eff in nodes[nid].get('effects', []):
            rid = eff['effectRowId']
            val = eff['value']
            if effect_defs.get(rid, True):
                totals[rid] = totals.get(rid, 0) + val
            else:
                totals[rid] = max(totals.get(rid, 0), val)
    return totals

# ---------------------------------------------------------------------------
# Greedy fallback – no floating nodes (respects overrides)
# ---------------------------------------------------------------------------
def greedy_build(weights, root, budget):
    node_marginal_score = precompute_marginal_scores(weights)
    selected = {root}
    remaining = budget - cost_map[root]
    while True:
        best_node = None
        best_score = -1
        for nid in ALL_NODE_IDS:
            if nid in selected:
                continue
            if cost_map[nid] > remaining:
                continue
            pre = prereq.get(nid, [])
            if not pre:
                continue  # non‑root floating node forbidden
            sz = size_map.get(nid, 'medium')
            if sz in ('keystone', 'capstone'):
                if not all(p in selected for p in pre):
                    continue
            else:
                if not any(p in selected for p in pre):
                    continue
            score = node_marginal_score[nid]
            if score > best_score:
                best_score = score
                best_node = nid
        if best_node is None:
            break
        selected.add(best_node)
        remaining -= cost_map[best_node]
    if is_valid_build(selected, root):
        return frozenset(selected)
    else:
        return frozenset({root})

# ---------------------------------------------------------------------------
# ILP solver – no floating nodes (respects overrides)
#
# STRUCTURAL FIX: the old formulation only required "at least one of my
# prerequisites is also selected" (or "all", for keystones). That's too weak:
# a closed loop of nodes can satisfy each other's requirement without ever
# tracing back to the actual root (e.g. A needs B, B needs C, C needs A).
# We saw this happen for real, repeatedly, on the live data (102/103/218/244,
# 205/279, 178/230/179/247, ...) — patching each one by hand as it's found
# doesn't scale.
#
# The fix is a rank/ordering constraint, the same trick used to eliminate
# subtours in TSP formulations (MTZ constraints): every candidate node gets
# an integer rank r[nid]. The root is rank 0. Whenever a node is selected via
# a specific justifying prerequisite edge, its rank must be strictly greater
# than that prerequisite's rank. A cycle would require strictly increasing
# ranks all the way around back to the start, which is impossible — so the
# ILP can no longer "bootstrap" a selection purely from a loop.
# ---------------------------------------------------------------------------
def solve_archetype(weights, root, budget, prev_solution=None, fallback_log=None):
    candidate_nodes = [nid for nid in ALL_NODE_IDS if cost_map[nid] <= budget]
    node_marginal_score = precompute_marginal_scores(weights)
    # Tight bound on chain depth (measured via BFS: deepest real prereq chain in the
    # whole tree is 16 hops). Using this instead of len(candidate_nodes) keeps the
    # big-M constraints numerically tight, which is the difference between ~0.5s and
    # 60s per solve for the larger budgets.
    N = MAX_CHAIN_DEPTH + 2

    prob = LpProblem(f"r{root}_b{budget}", LpMaximize)
    x = {nid: LpVariable(f"x_{nid}", cat='Binary') for nid in candidate_nodes}
    rank = {nid: LpVariable(f"rank_{nid}", lowBound=0, upBound=N, cat='Integer') for nid in candidate_nodes}

    if prev_solution:
        for nid in candidate_nodes:
            x[nid].setInitialValue(1 if prev_solution.get(nid, 0) == 1 else 0)

    prob += lpSum(node_marginal_score[nid] * x[nid] for nid in candidate_nodes)

    if root not in x:
        return None, -1
    prob += x[root] == 1
    prob += rank[root] == 0

    for r in GOD_ROOTS:
        if r != root and r in x:
            prob += x[r] == 0

    prob += lpSum(cost_map[nid] * x[nid] for nid in candidate_nodes) <= budget

    for nid in candidate_nodes:
        if nid == root:
            continue
        pre = prereq.get(nid, [])
        if not pre:
            prob += x[nid] == 0  # non-root floating node forbidden
            continue
        pre_candidates = [p for p in pre if p in candidate_nodes]
        if not pre_candidates:
            prob += x[nid] == 0
            continue
        sz = size_map.get(nid, 'medium')
        if sz in ('keystone', 'capstone'):
            # AND: every listed prerequisite must be selected AND have a
            # strictly smaller rank whenever nid itself is selected.
            if len(pre_candidates) < len(pre):
                # a required prerequisite isn't even affordable at this budget
                prob += x[nid] == 0
                continue
            for p in pre_candidates:
                prob += x[nid] <= x[p]
                prob += rank[nid] >= rank[p] + 1 - N * (1 - x[nid])
        else:
            # OR: at least one prerequisite must be selected, and we track
            # which one specifically "justifies" nid via an edge-selector z,
            # enforcing the rank order only along that chosen edge.
            z = {p: LpVariable(f"z_{nid}_{p}", cat='Binary') for p in pre_candidates}
            prob += lpSum(z[p] for p in pre_candidates) >= x[nid]
            for p in pre_candidates:
                prob += z[p] <= x[p]
                prob += z[p] <= x[nid]
                prob += rank[nid] >= rank[p] + 1 - N * (1 - z[p])

    prob.solve(PULP_CBC_CMD(msg=0, timeLimit=TIME_LIMIT, warmStart=bool(prev_solution)))

    try:
        selected = frozenset(
            nid for nid in candidate_nodes
            if value(x[nid]) is not None and value(x[nid]) > 0.5
        )
        if selected and is_valid_build(selected, root):
            score = sum(node_marginal_score[nid] for nid in selected)
            return selected, score
        else:
            if fallback_log is not None:
                fallback_log.append((root, budget))
            greedy = greedy_build(weights, root, budget)
            score = sum(node_marginal_score[nid] for nid in greedy)
            return greedy, score
    except Exception:
        if fallback_log is not None:
            fallback_log.append((root, budget))
        greedy = greedy_build(weights, root, budget)
        score = sum(node_marginal_score[nid] for nid in greedy)
        return greedy, score

# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------
def generate_builds_for_archetype(archetype_name, weights, fallback_log):
    best = {b: (-1.0, None, frozenset()) for b in BUDGETS}
    for root in sorted(GOD_ROOTS):
        prev_solution = None
        for b in BUDGETS:
            build, score = solve_archetype(weights, root, b, prev_solution, fallback_log)
            if build is not None and score > best[b][0]:
                best[b] = (score, root, build)
            if build:
                prev_solution = {nid: 1 if nid in build else 0 for nid in ALL_NODE_IDS}
            else:
                prev_solution = None
    return best

# ---------------------------------------------------------------------------
# HTML generation (v5 style)
# ---------------------------------------------------------------------------
def generate_html(all_results):
    html_parts = []
    html_parts.append("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pantheon Pact Builds – Optimal Guides</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#08070f;color:#c4bca8;font-family:"Segoe UI",system-ui,sans-serif;padding:24px 14px}
h1{text-align:center;font-size:1.4rem;letter-spacing:.1em;text-transform:uppercase;color:#e8d89a;margin-bottom:3px}
.sub{text-align:center;font-size:.7rem;color:#3a3448;margin-bottom:18px;letter-spacing:.05em}
.tabs{display:flex;flex-wrap:wrap;gap:3px;margin-bottom:16px;justify-content:center}
.tab{padding:6px 11px;border-radius:4px;border:1px solid #1e1c30;font-size:.7rem;font-weight:600;cursor:pointer;text-transform:uppercase;background:#0c0b18;color:#5a5478;transition:all .12s}
.tab:hover{background:#14122a;color:#9088b8}
.tab.active{color:#e8d89a;border-color:#423a60;background:#18152c}
.arch-section{display:none}
.arch-section.active{display:block}
.arch-desc{background:#0d0b1a;border:1px solid #1c1a32;border-radius:5px;padding:9px 13px;margin-bottom:12px;font-size:.73rem;color:#726888;line-height:1.6}
.arch-desc strong{color:#a090c0;font-size:.8rem}
.arch-desc .note{color:#c89040;font-size:.7rem;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:.78rem}
thead th{background:#0e0c1c;color:#5a5490;text-transform:uppercase;letter-spacing:.07em;font-size:.62rem;padding:8px 10px;border-bottom:2px solid #1e1c38;white-space:nowrap}
tbody tr{border-bottom:1px solid #141220}
tbody tr:nth-child(odd){background:#0b0a16}
tbody tr:nth-child(even){background:#090816}
tbody tr:hover{background:#161428!important}
tbody tr.duplicate{background:#181420!important;border-left:3px solid #3a2a40}
tbody tr.duplicate:hover{background:#1e1830!important}
td{padding:7px 10px;vertical-align:middle}
.col-pts{font-size:.93rem;font-weight:700;color:#e8d89a;text-align:center;white-space:nowrap}
.col-pts.hi{color:#6ecf80}
.col-pts.dup{color:#5a4a60}
.col-root{font-weight:600;white-space:nowrap;font-size:.75rem}
.r1{color:#7ec8e3}
.r2{color:#c96060}
.r3{color:#b07fd6}
.r4{color:#78c47c}
.r5{color:#5fc0a8}
.r6{color:#c8a050}
.col-meta{color:#3a3458;font-size:.7rem;text-align:center;white-space:nowrap}
.stats{display:flex;flex-wrap:wrap;gap:3px}
.pill{display:inline-block;border-radius:3px;padding:2px 5px;font-size:.67rem;font-weight:600;white-space:nowrap}
.pd{background:#1c0e0e;color:#e06868;border:1px solid #3e1414}
.pu{background:#0e1c0e;color:#58b858;border:1px solid #163c16}
.ps{background:#0e1218;color:#5078c0;border:1px solid #162240}
.pp{background:#1c1608;color:#c89040;border:1px solid #402c08}
.pc{background:#160c1e;color:#b058c8;border:1px solid #36105a}
.px{background:#121220;color:#8090b0;border:1px solid #202248}
.dup-label{color:#5a4a60;font-size:.6rem;font-style:italic;margin-left:6px}
a.btn{color:#5868a8;text-decoration:none;font-size:.67rem;border:1px solid #1e1e3c;padding:3px 7px;border-radius:3px;white-space:nowrap;transition:all .12s}
a.btn:hover{background:#161c36;color:#8898e8;border-color:#343860}
.note-box{margin:20px auto 0;max-width:960px;background:#0d0b1a;border:1px solid #1a1830;border-radius:6px;padding:14px 18px;font-size:.72rem;color:#5a5470;line-height:1.65}
.note-box h3{color:#7868a8;margin-bottom:7px;font-size:.74rem;text-transform:uppercase;letter-spacing:.06em}
.note-box li{margin-left:16px;margin-bottom:4px}
.note-box strong{color:#9880c0}
</style>
</head>
<body>
<h1>Pantheon Pact Tree &mdash; Build Guide</h1>
<p class="sub">8 archetypes &middot; 5&ndash;150pt &middot; ILP exact solver &middot; Core effect filtering &middot; Temporary prerequisite patches applied</p>
<div class="tabs">
""")

    for i, (name, _) in enumerate(all_results.items()):
        active = 'active' if i == 0 else ''
        html_parts.append(f'<button class="tab {active}" onclick="show(\'{name.replace(" ", "_")}\',this)">{name}</button>')

    html_parts.append('</div>')

    # Core effect requirements
    core_requirements = {
        "Melee DPS": ['perk_graph_effect:pantheon_melee_max_hit_pct'],
        "Ranged DPS": ['perk_graph_effect:pantheon_ranged_max_hit_pct'],
        "Magic DPS": ['perk_graph_effect:pantheon_magic_max_hit_pct'],
        "Hammer / Prayer": ['perk_graph_effect:pantheon_hammer_max_hit_prayer_bonus_pct'],
        "Berserker": ['perk_graph_effect:pantheon_berserker_dmg_pct'],
        "Sustain / Tank": ['perk_graph_effect:pantheon_flat_damage_reduction_pct', 'perk_graph_effect:pantheon_reflect_damage_pct'],
        "Summoner / Pet": ['perk_graph_effect:pantheon_pet_damage_pct', 'perk_graph_effect:pantheon_tithe_summon_damage_pct'],
        "Slayer / Hybrid": ['perk_graph_effect:pantheon_slayer_helm_buff_pct', 'perk_graph_effect:pantheon_balance_all_styles_damage_pct'],
    }

    core_effect_display = {
        "Melee DPS": "melee damage",
        "Ranged DPS": "ranged damage",
        "Magic DPS": "magic damage",
        "Hammer / Prayer": "orbiting hammers",
        "Berserker": "berserker damage bonus",
        "Sustain / Tank": "damage reduction or reflect",
        "Summoner / Pet": "pet/summon damage",
        "Slayer / Hybrid": "slayer helm or all‑style damage",
    }

    for name, (results, weights) in all_results.items():
        section_id = name.replace(" ", "_")
        desc = {
            "Melee DPS": "Focuses on melee max hit, melee crit, and lifesteal.",
            "Ranged DPS": "Maximises ranged max hit, distance bonuses, and bolt effects.",
            "Magic DPS": "Prioritises magic max hit, staff speed, and chaos echoes.",
            "Hammer / Prayer": "Orbiting hammers scale with prayer bonus. Only builds with hammers are shown.",
            "Berserker": "Low‑HP, high‑risk melee with berserker and blindbag.",
            "Sustain / Tank": "Stacks damage reduction, HP, lifesteal, and reflect.",
            "Summoner / Pet": "Boosts pet and summon damage.",
            "Slayer / Hybrid": "Balanced all‑styles with slayer helm and prayer penetration."
        }.get(name, "")
        req_effects = core_requirements.get(name, [])
        desc_note = f"Only rows that include <strong>{core_effect_display.get(name, 'the core effect')}</strong> are shown. If a budget is missing, the core effect wasn't affordable yet."
        html_parts.append(f'<div id="{section_id}" class="arch-section">')
        html_parts.append(f'<div class="arch-desc"><strong>{name}</strong> &mdash; {desc}<br><span class="note">{desc_note}</span></div>')
        html_parts.append('<table><thead><tr><th>Points</th><th>God Root</th><th>Cost/N</th><th style="min-width:460px">Key stats (final in‑game values)</th><th>Planner</th></tr></thead><tbody>')

        PLANNER_BASE = "https://august-rsps.com/perk-planner?v=pantheon&n="
        prev_build = None
        prev_root = None
        for b in BUDGETS:
            scr, root, build = results[b]
            if not build:
                continue
            final_effects = aggregate_effects(build)
            # Core effect check
            has_core = False
            for req in req_effects:
                if final_effects.get(req, 0) > 0:
                    has_core = True
                    break
            if not has_core:
                continue

            total_cost = sum(cost_map[nid] for nid in build)
            ids = sorted(build)
            url = PLANNER_BASE + ','.join(map(str, ids))

            is_dup = (prev_build is not None and build == prev_build and root == prev_root)
            dup_label = '<span class="dup-label">(same as previous)</span>' if is_dup else ''

            # Build pill stats
            relevant = {}
            for k, v in final_effects.items():
                short = k.replace('perk_graph_effect:pantheon_', '')
                if weights.get(k, 0) > 0 and v > 0:
                    relevant[short] = v
            top = sorted(relevant.items(), key=lambda kv: -weights.get(f'perk_graph_effect:pantheon_{kv[0]}', 1) * kv[1])[:5]
            pill_html = ''.join(f'<span class="pill {get_pill_class(k)}">{k}={v:.0f}</span> ' for k, v in top)
            if not pill_html:
                pill_html = '<span style="color:#3a3458;font-size:.7rem">(no weighted stats)</span>'

            root_name = nodes[root]['displayName']
            root_class = f"r{root}" if root in [1,2,3,4,5,6] else ""
            pts_class = "col-pts hi" if b in [5,10] else "col-pts"
            if is_dup:
                pts_class += " dup"
            html_parts.append(f"""
            <tr class="{'duplicate' if is_dup else ''}">
                <td class="{pts_class}">{b} {dup_label}</td>
                <td class="col-root {root_class}">{root_name}</td>
                <td class="col-meta">{total_cost}/{len(ids)}</td>
                <td><div class="stats">{pill_html}</div></td>
                <td><a class="btn" href="{url}" target="_blank">Open &#8599;</a></td>
            </tr>
            """)
            prev_build = build
            prev_root = root

        html_parts.append('</tbody></table></div>')

    html_parts.append("""
    <div class="note-box"><h3>How builds work</h3>
    <ul>
        <li><strong>Keystones require ALL listed prerequisites</strong>, small/medium nodes need only one.</li>
        <li><strong>Root switches</strong> are marked by a new row with a different god.</li>
        <li><strong>Duplicate rows</strong> labelled <span style="color:#5a4a60;">(same as previous)</span> mean the optimal build hasn’t changed.</li>
        <li><strong>Temporary prerequisite patches</strong> have been applied for nodes that were previously floating or in unreachable loops. These will be removed once the game data is fixed.</li>
        <li><strong>Devout Vessel</strong> = HP bonus from prayer bonus %, not damage.</li>
        <li><strong>Flurry</strong> = next attack fires 1 tick sooner.</li>
        <li><strong>Crackling Staff</strong> halves powered‑staff attack speed.</li>
        <li>Use the <strong>Planner</strong> link to see the exact node selection and total cost.</li>
    </ul></div>
    <script>
    function show(id,btn){
        document.querySelectorAll(".arch-section").forEach(s=>s.classList.remove("active"));
        document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
        document.getElementById(id).classList.add("active");
        btn.classList.add("active");
    }
    </script>
    </body></html>
    """)

    return ''.join(html_parts)

# Helper function to pick pill colour based on stat name
def get_pill_class(short_name):
    short = short_name.lower()
    if 'damage' in short or 'max_hit' in short:
        return 'pd'
    elif 'min_hit' in short:
        return 'pu'
    elif 'lifesteal' in short or 'heal' in short:
        return 'ps'
    elif 'prayer' in short or 'faith' in short or 'devout' in short:
        return 'pp'
    elif 'crit' in short:
        return 'pc'
    else:
        return 'px'

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    import pickle, os
    CHECKPOINT_FILE = "checkpoint.pkl"
    all_results = {}
    fallback_log = []

    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "rb") as f:
            all_results, fallback_log = pickle.load(f)
        print(f"Resumed from checkpoint: {list(all_results.keys())}")

    for archetype_name, weights in ARCHETYPE_WEIGHTS.items():
        if archetype_name in all_results:
            print(f"Skipping {archetype_name} (already in checkpoint)")
            continue
        print(f"Solving for {archetype_name}...")
        results = generate_builds_for_archetype(archetype_name, weights, fallback_log)
        all_results[archetype_name] = (results, weights)
        print(f"Finished {archetype_name}\n")
        with open(CHECKPOINT_FILE, "wb") as f:
            pickle.dump((all_results, fallback_log), f)

    if len(all_results) < len(ARCHETYPE_WEIGHTS):
        print(f"Progress saved: {len(all_results)}/{len(ARCHETYPE_WEIGHTS)} archetypes done. Re-run to continue.")
        return

    total_solves = len(ARCHETYPE_WEIGHTS) * len(GOD_ROOTS) * len(BUDGETS)
    print(f"ILP fallback-to-greedy count: {len(fallback_log)} / {total_solves} solves "
          f"({100 * len(fallback_log) / total_solves:.1f}%)")
    if fallback_log:
        print("Fell back on:", fallback_log[:20], "..." if len(fallback_log) > 20 else "")

    html = generate_html(all_results)
    with open("pantheon_builds.html", "w") as f:
        f.write(html)
    print("Done! Open pantheon_builds.html in your browser.")
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

if __name__ == "__main__":
    main()
