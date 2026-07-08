#!/usr/bin/env python3
"""
Pantheon Pact Tree Optimal Build Solver
========================================
Standalone — single file, no manual data download needed. On startup it
looks for pantheon_data.json next to this script; if missing, it curls a
fresh copy from august-rsps.com/perk-graph/data.json and saves it locally
for next time (falls back to Python's urllib if curl isn't on PATH). Pass a
file path as argv[1] to use a specific copy instead of either of those.

Validity logic is a direct port of the real client's own algorithm, extracted
from its source (f16229361d9c277e.js), not inferred from examples:
  - Undirected adjacency: a node validates via ANY node connected by a
    prerequisite edge, in either direction — not just its own listed parents.
  - A node is valid if it's a root, or its pointCost is 0, or any adjacent
    node is already valid (pure OR — no AND-logic on keystones).
  - specialRequirement has exactly two real cases: "all_links_unlocked"
    (capstones — needs its own direct prerequisites, not the full ancestor
    tree) and "exclusive_alignment" (the 6 roots — pick only one).
  - There is no god-exclusivity rule for keystone/small/medium nodes.
Verified against 4 independently-confirmed real examples (in-game click
tests and the live planner's own "unreachable" flags) before use.

Solving is parallelized across all CPU cores via multiprocessing, since the
960 (archetype, root, budget) solves are fully independent. A GPU does not
help here — CBC's branch-and-bound is inherently sequential per problem.
"""

import os
import sys
import json
import subprocess
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
BUDGETS = list(range(5, 101, 5))  # capped at 100 — confirmed real in-game point cap
TIME_LIMIT = 15  # per-solve budget; safe to raise further on a many-core machine

# ---------------------------------------------------------------------------
# Load data. Checks, in order:
#   1. An explicit file path passed as argv[1].
#   2. pantheon_data.json sitting next to this script (same folder).
#   3. If neither exists, curl it fresh from the live source and save it
#      next to this script for next time, so subsequent runs work offline.
# ---------------------------------------------------------------------------
DATA_URL = "https://august-rsps.com/perk-graph/data.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_PATH = os.path.join(SCRIPT_DIR, "pantheon_data.json")

if len(sys.argv) > 1:
    data_path = sys.argv[1]
elif os.path.exists(LOCAL_DATA_PATH):
    data_path = LOCAL_DATA_PATH
else:
    print(f"pantheon_data.json not found in {SCRIPT_DIR}, fetching from {DATA_URL} ...")
    try:
        subprocess.run(
            ["curl", "-fsSL", DATA_URL, "-o", LOCAL_DATA_PATH],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # curl missing or failed (e.g. Windows without curl on PATH pre-2018) —
        # fall back to Python's own HTTP client so this still works everywhere.
        try:
            import urllib.request
            urllib.request.urlretrieve(DATA_URL, LOCAL_DATA_PATH)
        except Exception as e:
            if os.path.exists(LOCAL_DATA_PATH):
                os.remove(LOCAL_DATA_PATH)  # don't leave a partial/corrupt file behind
            print(f"Couldn't fetch {DATA_URL}: {e}")
            print("Check your internet connection, or manually download the file to:")
            print(f"  {LOCAL_DATA_PATH}")
            sys.exit(1)
    print(f"Saved to {LOCAL_DATA_PATH} — future runs will use this local copy.")
    data_path = LOCAL_DATA_PATH

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
is_root_map = {n['id']: bool(n.get('isRoot')) for n in node_list}
special_map = {n['id']: n.get('specialRequirement') for n in node_list}

effect_defs = {e['rowId']: e.get('stackable', True) for e in data.get('effects', [])}

GOD_ROOTS    = {1, 2, 3, 4, 5, 6}
ALL_NODE_IDS = list(nodes.keys())

# 2026-07-07: REBUILT FROM THE REAL CLIENT SOURCE (f16229361d9c277e.js), extracted
# live via console. Every previous version of this validity logic — the AND-logic-
# on-keystones model, the "empty prereq = forbidden" model, the "empty prereq =
# free" model, and the god-exclusivity model — was an inference from examples and
# is now known to be wrong in some respect. This is not an inference; it is a
# direct transcription of the client's own functions tY/tV/tK.
#
# Key facts this reveals that no prior version had right:
#  - Adjacency is UNDIRECTED. A node's "prerequisites" list creates a two-way edge:
#    it can be validated via that listed parent, OR via any other node that lists
#    IT as a prerequisite. Direction of the listed prerequisite does not gate
#    which side must come "first".
#  - A node is valid if it isRoot, OR its pointCost is 0, OR ANY undirected
#    neighbor is already valid (pure OR across all neighbors — no AND logic on
#    keystones at all).
#  - specialRequirement has exactly two real cases:
#      "perkgraph:all_links_unlocked" (capstones): all of the node's own DIRECT
#        prerequisites must be valid (not the full ancestor tree).
#      "pantheon:exclusive_alignment" (the 6 roots only): at most one node
#        carrying this flag may be valid at once — i.e. exactly the single-root
#        rule, with no other meaning.
#  - There is NO god-exclusivity mechanic anywhere for keystone/capstone/small/
#    medium nodes. A node with an empty prerequisite list and pointCost > 0 (e.g.
#    22, 23, 24, 175, 239, 279) is only reachable via nodes that list IT as their
#    OWN prerequisite (reverse edges) — it is not "free", and it is not
#    "forbidden" either; it's exactly as reachable as any other node under the
#    undirected-OR rule above.
UNDIRECTED_ADJ = {nid: set() for nid in nodes}
for _n in node_list:
    for _p in _n['prerequisites']:
        UNDIRECTED_ADJ[_n['id']].add(_p)
        UNDIRECTED_ADJ.setdefault(_p, set()).add(_n['id'])

def _special_ok(nid, valid_set):
    sr = special_map.get(nid)
    if not sr:
        return True
    if sr == 'perkgraph:all_links_unlocked':
        pre = prereq.get(nid, [])
        return len(pre) == 0 or all(p in valid_set for p in pre)
    if sr == 'pantheon:exclusive_alignment':
        return not any(
            other != nid and special_map.get(other) == sr and other in valid_set
            for other in GOD_ROOTS
        )
    return True

def _reachable_set(selected):
    """Exact port of the client's fixed-point closure (the 'cascade' reconciliation
    function). Returns the subset of `selected` that is actually valid/obtainable."""
    valid = set()
    changed = True
    while changed:
        changed = False
        for a in selected:
            if a in valid:
                continue
            if a not in nodes:
                continue
            if is_root_map.get(a) or cost_map.get(a) == 0:
                conn_ok = True
            else:
                conn_ok = any(nb in valid for nb in UNDIRECTED_ADJ.get(a, ()))
            if conn_ok and _special_ok(a, valid):
                valid.add(a)
                changed = True
    return valid

# ---------------------------------------------------------------------------
# NOTE: every previous version of this file had a block here for hardcoded
# prerequisite overrides, OR_LOGIC_NODES exceptions, and AND-vs-OR-by-size
# logic. All of that is now known to be unnecessary: the real client uses
# plain undirected-OR reachability (see UNDIRECTED_ADJ / _reachable_set
# above) for every node regardless of size, with no AND-logic anywhere
# except the two explicit specialRequirement cases already handled in
# _special_ok(). Nodes with empty prerequisite lists (22, 23, 24, 175, 239,
# 279, etc.) are neither "free" nor "forbidden" — they're ordinary nodes
# whose only edges come from OTHER nodes listing them as a prerequisite
# (reverse edges), which UNDIRECTED_ADJ already captures correctly. No
# guessed overrides, size-based AND/OR split, or god-exclusivity rule is
# needed or correct. This whole block is intentionally empty now.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Compute a tight upper bound on real prerequisite-chain depth (used as the
# "big-M" in the rank-ordering ILP constraints below). Using the true graph
# depth instead of the total node count keeps the ILP numerically tight.
# NOTE: this now walks UNDIRECTED_ADJ (BFS distance from each root) rather
# than the old directed parent->child tree, since reachability itself is
# undirected. It's still just a bound for the ILP's big-M, not a validity
# rule, so a slightly loose bound here is fine.
# ---------------------------------------------------------------------------
def _compute_max_chain_depth():
    from collections import deque
    max_depth = 0
    for root in GOD_ROOTS:
        depth = {root: 0}
        q = deque([root])
        while q:
            cur = q.popleft()
            for nb in UNDIRECTED_ADJ.get(cur, ()):
                if nb not in depth:
                    depth[nb] = depth[cur] + 1
                    q.append(nb)
        if depth:
            max_depth = max(max_depth, max(depth.values()))
    return max_depth

MAX_CHAIN_DEPTH = _compute_max_chain_depth()

# ---------------------------------------------------------------------------
# Verification — exact port of the real client's validity check.
# ---------------------------------------------------------------------------
def is_valid_build(selected, root):
    selected = set(selected)
    if root not in selected:
        return False
    return _reachable_set(selected) == selected


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
_all_prereqs_cache = {}
def get_all_prereqs(nid, _visiting=None):
    """Full ancestor closure of nid, memoized. Retains cycle protection (in
    case the source data ever has one) while still being O(1) amortized
    across repeated calls, unlike the original which re-walked the whole
    chain from scratch every time — including once per non-stackable effect
    per node per full node scan, which used to happen 180x per archetype."""
    if nid in _all_prereqs_cache:
        return _all_prereqs_cache[nid]
    if _visiting is None:
        _visiting = set()
    if nid in _visiting:
        return {nid}  # cycle guard
    _visiting.add(nid)
    visited = {nid}
    for p in prereq.get(nid, []):
        visited |= get_all_prereqs(p, _visiting)
    _all_prereqs_cache[nid] = visited
    return visited

# ---------------------------------------------------------------------------
# MANUAL ABILITY SCORES — for nodes with NO numeric `effects`
# ---------------------------------------------------------------------------
# 54 nodes in this tree (every capstone, plus several keystones) grant real,
# often build-defining mechanics that are only described in text, not encoded
# as a numeric effect. The scoring model below can only ever value what's in
# an `effects` array, so without this these nodes silently score 0 forever,
# no matter how strong they are, and the solver will never recommend them.
#
# These numbers are Claude's own judgment calls from reading each node's
# description, loosely calibrated against comparable weighted stats
# elsewhere in this file (e.g. a 25%-damage stat with weight 4.0 scores 100).
# THEY ARE NOT MEASURED DATA. Treat them as a reasonable starting point and
# adjust freely — there is no way to derive these mechanically from the JSON.
# ---------------------------------------------------------------------------
MANUAL_ABILITY_SCORES = {
    8:   {'Hammer / Prayer': 20, 'Melee DPS': 10},   # Smite: +0.35%/pt equipped prayer bonus dmg
    9:   {'Sustain / Tank': 15},                      # Devotion: def/dmg scaling with prayer pts
    13:  {'Summoner / Pet': 35},                      # Legion: free duplicate thrall summon
    14:  {'Summoner / Pet': 22},                      # Soul Conduit: +15% dmg per active summon to boss pet
    15:  {'Summoner / Pet': 12},                      # Blood Tithe: +15% pet/summon dmg, -30 HP cost
    16:  {'Ranged DPS': 28},                          # Eye of Armadyl: halved mitigation + up to +16% dmg
    20:  {'Sustain / Tank': 22},                      # Bark Skin: 35% less dmg (1/3 delayed as bleed)
    303: {'Magic DPS': 22},                           # Heretic Mastery: spellbook + Heretic's Meteor combo
    304: {'Summoner / Pet': 28},                      # Necromancer Mastery: infinite range/LOS + new summon
    305: {'Ranged DPS': 22},                          # Skyborn Mastery: +10 tile base range + chaining echo
    321: {'Hammer / Prayer': 28},                     # Aegis of Light: Omni prayer + explicit +15% hammer dmg
    339: {'Berserker': 22, 'Melee DPS': 12},          # Avatar of Bandos: timed combat-mode burst window
    356: {'Sustain / Tank': 28},                      # World Guardian: +50% reflect + anti-one-shot cap
}

_marginal_score_cache = {}
def precompute_marginal_scores(weights, archetype_name=None):
    # Cache key: archetype_name alone is sufficient since each archetype has
    # exactly one fixed weights dict in ARCHETYPE_WEIGHTS — this function's
    # result never varies across root/budget, only across archetype. Without
    # this, the full node scan (including the get_all_prereqs walk for every
    # non-stackable effect) ran 180 times per archetype instead of once —
    # 1440 redundant full recomputations across the whole run. Note this
    # cache is per-process under multiprocessing (each worker has its own
    # copy), so it helps most when a worker handles several tasks from the
    # same archetype in a row — which the task ordering already does, since
    # tasks are generated grouped by archetype.
    if archetype_name is not None and archetype_name in _marginal_score_cache:
        return _marginal_score_cache[archetype_name]
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
        if archetype_name is not None:
            score += MANUAL_ABILITY_SCORES.get(nid, {}).get(archetype_name, 0)
        node_marginal_score[nid] = score
    if archetype_name is not None:
        _marginal_score_cache[archetype_name] = node_marginal_score
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

def get_ability_nodes(selected_ids):
    """Which manually-scored ability nodes (if any) are present in a build."""
    return [nid for nid in selected_ids if nid in MANUAL_ABILITY_SCORES]

# ---------------------------------------------------------------------------
# Greedy fallback – no floating nodes (respects overrides)
# ---------------------------------------------------------------------------
def greedy_build(weights, root, budget, archetype_name=None):
    node_marginal_score = precompute_marginal_scores(weights, archetype_name)
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
            # Real client rule: valid if root/free-cost, or ANY undirected
            # neighbor is already selected (selected is always fully valid
            # here, so this is the same test the live client's incremental
            # click-handler uses), AND the specialRequirement (if any) passes.
            if not (is_root_map.get(nid) or cost_map.get(nid) == 0):
                if not any(nb in selected for nb in UNDIRECTED_ADJ.get(nid, ())):
                    continue
            if not _special_ok(nid, selected):
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
def solve_archetype(weights, root, budget, prev_solution=None, fallback_log=None, archetype_name=None):
    candidate_nodes = [nid for nid in ALL_NODE_IDS if cost_map[nid] <= budget]
    node_marginal_score = precompute_marginal_scores(weights, archetype_name)
    N = MAX_CHAIN_DEPTH + 2

    prob = LpProblem(f"r{root}_b{budget}", LpMaximize)
    x = {nid: LpVariable(f"x_{nid}", cat='Binary') for nid in candidate_nodes}
    rank = {nid: LpVariable(f"rank_{nid}", lowBound=0, upBound=N, cat='Integer') for nid in candidate_nodes}

    if prev_solution:
        for nid in candidate_nodes:
            x[nid].setInitialValue(1 if prev_solution.get(nid, 0) == 1 else 0)

    prob += lpSum(node_marginal_score[nid] * x[nid] for nid in candidate_nodes)

    if root not in x:
        return None, -1, False
    prob += x[root] == 1
    prob += rank[root] == 0

    for r in GOD_ROOTS:
        if r != root and r in x:
            prob += x[r] == 0

    prob += lpSum(cost_map[nid] * x[nid] for nid in candidate_nodes) <= budget

    for nid in candidate_nodes:
        if nid == root:
            continue
        if is_root_map.get(nid):
            continue  # other roots already forced to x==0 above
        if cost_map.get(nid) == 0:
            # Real client rule: pointCost==0 nodes are always valid regardless
            # of connectivity. No gating constraint at all — only the shared
            # budget constraint above applies.
            continue

        sr = special_map.get(nid)
        if sr == 'perkgraph:all_links_unlocked':
            # Real rule for capstones: ALL of the node's own DIRECT
            # prerequisites must be selected (not the full ancestor tree,
            # and not "any neighbor" — this is the one real AND case).
            pre = prereq.get(nid, [])
            if not pre:
                continue  # trivially satisfied per the real client logic
            pre_candidates = [p for p in pre if p in candidate_nodes]
            if len(pre_candidates) < len(pre):
                prob += x[nid] == 0
                continue
            for p in pre_candidates:
                prob += x[nid] <= x[p]
                prob += rank[nid] >= rank[p] + 1 - N * (1 - x[nid])
        else:
            # Ordinary node: real rule is undirected-OR reachability — valid
            # if ANY undirected neighbor (parent OR child of the original
            # directed prerequisite edge) is selected. MTZ rank-ordering on
            # whichever neighbor edge is used still prevents cycles from
            # bootstrapping a selection with no real path to the root.
            neighbors = [nb for nb in UNDIRECTED_ADJ.get(nid, ()) if nb in candidate_nodes]
            if not neighbors:
                prob += x[nid] == 0
                continue
            z = {nb: LpVariable(f"z_{nid}_{nb}", cat='Binary') for nb in neighbors}
            prob += lpSum(z[nb] for nb in neighbors) >= x[nid]
            for nb in neighbors:
                prob += z[nb] <= x[nb]
                prob += z[nb] <= x[nid]
                prob += rank[nid] >= rank[nb] + 1 - N * (1 - z[nb])

    prob.solve(PULP_CBC_CMD(msg=0, timeLimit=TIME_LIMIT, warmStart=bool(prev_solution), gapRel=0.01))

    fell_back = False
    try:
        selected = frozenset(
            nid for nid in candidate_nodes
            if value(x[nid]) is not None and value(x[nid]) > 0.5
        )
        if selected and is_valid_build(selected, root):
            score = sum(node_marginal_score[nid] for nid in selected)
            return selected, score, False
        else:
            fell_back = True
            greedy = greedy_build(weights, root, budget, archetype_name)
            score = sum(node_marginal_score[nid] for nid in greedy)
            return greedy, score, True
    except Exception:
        greedy = greedy_build(weights, root, budget, archetype_name)
        score = sum(node_marginal_score[nid] for nid in greedy)
        return greedy, score, True

# ---------------------------------------------------------------------------
# Parallel solving — every (archetype, root, budget) combo is fully
# independent, so this is embarrassingly parallel across CPU cores. A GPU
# does NOT help here: CBC's branch-and-bound is inherently sequential per
# problem (no mature GPU MIP solver is in general use), so the real lever
# for speed on better hardware is core count, not GPU compute. Bumped the
# optimality gap back down to 0.01 (from the emergency 0.05 used only to
# survive tight interactive tool-call time limits) since with real
# parallelism there's no need to trade quality for speed anymore.
# ---------------------------------------------------------------------------
def _solve_task(task):
    archetype_name, root, budget = task
    weights = ARCHETYPE_WEIGHTS[archetype_name]
    build, score, fell_back = solve_archetype(weights, root, budget, None, None, archetype_name)
    return (archetype_name, root, budget, build, score, fell_back)




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
.pa{background:#241a04;color:#e8b040;border:1px solid #4a3208;font-weight:700}
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
<p class="sub">8 archetypes &middot; 5&ndash;100pt &middot; ILP exact solver &middot; Core effect filtering &middot; Free-standing nodes confirmed via live testing (no guessed overrides)</p>
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

            # Ability-only nodes (no numeric effect, manually scored) get their own
            # distinct pill so it's clear WHY the build reaches for them.
            ability_ids = get_ability_nodes(build)
            for aid in ability_ids:
                aname = nodes[aid]['displayName']
                pill_html += f'<span class="pill pa" title="Ability (no numeric stat) — manually scored, see notes">{aname} ⚡</span> '

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
        <li><strong>Free-standing nodes</strong> (empty prerequisite list, e.g. Blindbag, Goliath's Reach, Pierce Faith chains) are directly selectable with no unlock chain required — confirmed via live in-game testing, not a guess.</li>
        <li><strong>Node 244</strong> now uses its real live prerequisite (103) as of 2026-07-06 — previously a guess, now confirmed data.</li>
        <li><strong>Devout Vessel</strong> = HP bonus from prayer bonus %, not damage.</li>
        <li><strong>Flurry</strong> = next attack fires 1 tick sooner.</li>
        <li><strong>Crackling Staff</strong> halves powered‑staff attack speed.</li>
        <li>Use the <strong>Planner</strong> link to see the exact node selection and total cost.</li>
        <li><strong>Gold ⚡ pills</strong> mark ability nodes (capstones and a few keystones) that have no numeric stat in the game data — only descriptive text (e.g. Smite, Necromancer Mastery, Aegis of Light). Their scores are Claude's own judgment call from reading each description, not measured data, so treat their presence/absence as a rough guide rather than a precise ranking.</li>
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
    import pickle, os, time
    import multiprocessing as mp

    CHECKPOINT_FILE = "checkpoint.pkl"
    # raw[(archetype, root, budget)] = (build, score, fell_back)
    raw = {}

    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "rb") as f:
            raw = pickle.load(f)
        print(f"Resumed from checkpoint: {len(raw)} tasks already done")

    all_tasks = [
        (archetype_name, root, budget)
        for archetype_name in ARCHETYPE_WEIGHTS
        for root in sorted(GOD_ROOTS)
        for budget in BUDGETS
    ]
    remaining = [t for t in all_tasks if t not in raw]
    total = len(all_tasks)
    print(f"{len(raw)}/{total} tasks already done, {len(remaining)} remaining")

    if remaining:
        n_workers = os.cpu_count() or 4
        # Chunk size = one full budget sweep for a given (archetype, root).
        # Tasks are generated grouped by archetype, so this keeps each chunk
        # within a single archetype in the common case — letting the
        # precompute_marginal_scores cache actually pay off within a worker
        # (it's keyed by archetype, so a worker that gets a mixed-archetype
        # chunk would just recompute more than once, still fine) — while
        # cutting inter-process overhead by ~20x versus sending one task at
        # a time.
        chunksize = max(1, len(BUDGETS))
        print(f"Solving {len(remaining)} tasks across {n_workers} processes "
              f"(TIME_LIMIT={TIME_LIMIT}s/solve, chunksize={chunksize})...")
        t0 = time.time()
        done_count = 0
        SAVE_EVERY = max(1, len(remaining) // 40)  # ~40 checkpoint saves over the run
        with mp.Pool(processes=n_workers) as pool:
            for archetype_name, root, budget, build, score, fell_back in pool.imap_unordered(
                _solve_task, remaining, chunksize=chunksize
            ):
                raw[(archetype_name, root, budget)] = (build, score, fell_back)
                done_count += 1
                if done_count % SAVE_EVERY == 0 or done_count == len(remaining):
                    with open(CHECKPOINT_FILE, "wb") as f:
                        pickle.dump(raw, f)
                    elapsed = time.time() - t0
                    rate = done_count / elapsed if elapsed > 0 else 0
                    eta = (len(remaining) - done_count) / rate if rate > 0 else float('inf')
                    print(f"  {len(raw)}/{total} done "
                          f"({rate:.1f} tasks/s, ETA {eta/60:.1f} min)", flush=True)

    # Reassemble the per-archetype, per-budget "best across roots" structure
    # that generate_html() expects.
    all_results = {}
    fallback_log = []
    for archetype_name, weights in ARCHETYPE_WEIGHTS.items():
        best = {b: (-1.0, None, frozenset()) for b in BUDGETS}
        for root in sorted(GOD_ROOTS):
            for b in BUDGETS:
                build, score, fell_back = raw[(archetype_name, root, b)]
                if fell_back:
                    fallback_log.append((archetype_name, root, b))
                if build is not None and score > best[b][0]:
                    best[b] = (score, root, build)
        all_results[archetype_name] = (best, weights)

    total_solves = len(all_tasks)
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
