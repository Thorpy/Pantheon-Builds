===== POST 1 of 3 =====

```
PANTHEON PACT — SOLVER WEIGHTS (1/3)
Weight of 1.0 = equivalent to +1% direct damage per % of effect
Higher weight = more important to that build's optimisation goal
Conditional effects are discounted by estimated uptime fraction

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MELEE DPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  1H Speed (-1 tick)                    25   -1 tick on 1H = +25% attack rate
  Giant Slayer %/tile                    3   +5%/tile boss size, 3x3 = +15%
  Pious Fury /pray                       3   assume ~3 prayers active = +9% DPS
  Melee Max Hit %                        1   direct +1% avg damage per %
  Sara's Edge %                          1   same additive pool as Melee%
  Bandos Wrath %                         1   same additive pool as Melee%
  All Styles Dmg %                       1   applies to every combat style
  Zealous Impact %                       1   +5% 1H dmg while 2+ prayers on
  1H Mastery %                           1   flat +% for all 1H melee
  Berserker Echo %                     0.8   extra melee hit proc on berserker
  Blindbag Proc %                      0.8   extra hit with bag weapon
  Berserker % (2H only, <50 HP)        0.6   2H weapons only, 60% uptime assumed
  Reaching Echo % (2H)                 0.6   2H range echo proc, conditional
  Melee Crit %                         0.5   assume 50% crit damage bonus
  Flurry %                            0.25   next hit 1t sooner — NOT a double hit
  Sanguine Lifesteal %                 0.1   sustain, minor DPS proxy
  Min Hit (flat)                      0.05   +5 min on ~100 max ≈ +2.5% DPS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HAMMER / PRAYER DPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  1H Speed (-1 tick)                    20   -1 tick on 1H = +25% attack rate
  Prayer Regen /5t                       8   losing prayer = losing hammer DPS
  Pious Fury /pray                       3   assume ~3 prayers active = +9% DPS
  Prayer Regen /12t                      3   slower regen, still meaningful
  Hammer Prayer Bonus %                  1   orbiting hammer max hit scaling
  Spear of Light %                       1   every 5th attack, fully automatic
  Faith Surge %                          1   +25% prayer bonus = scales hammers
  1H Mastery %                           1   flat +% for all 1H melee
  Zealous Impact %                       1   +5% 1H dmg while 2+ prayers on
  Melee Max Hit %                      0.5   direct bonus to main weapon
  All Styles Dmg %                     0.5   applies to main weapon
  Prayer Drain -%                      0.4   keeps prayers on passively
  Min Hit (flat)                      0.05   minor floor raise

  Note: Devout Vessel = BONUS HP (prayer bonus × %), NOT prayer damage.
  Removed from this profile. Goes in Ironman/Sustain instead.
  Note: Hammer scaling was buffed in the latest patch. Values TBC.
```


===== POST 2 of 3 =====

```
PANTHEON PACT — SOLVER WEIGHTS (2/3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RANGED DPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  Ricochet Bounces (flat)                3   2 extra bounces = meaningful AoE
  Gale Roots %/stack                     2   5 stacks = +15% sustained on target
  Ranged Max Hit %                       1   direct +1% avg damage per %
  Heavy Loose 2H %                       1   +20% for 2H ranged, direct bonus
  Strong Pull %                          1   +20% for longbows, direct bonus
  All Styles Dmg %                       1   applies to every combat style
  Sniper %                               1   direct +7%, multiplies with Eye
  Eye Dist Dmg %/tile                  0.8   +3%/tile at range, up to +24% at 8t
  BBB Max Hit %                        0.5   18% max hit chance ≈ +9% avg DPS
  Ricochet Echo %                      0.5   echo proc + AoE value
  Ranged Crit %                        0.5   assume 50% crit damage bonus
  Charged Bolts %                      0.3   proc chain for bolt builds
  BBB Bolt Spec Dmg %                 0.15   conditional on spec firing
  BBB Bolt Proc %                     0.15   raises spec fire rate
  Headshot %                          0.12   25% for 150% after 5 hits on target
  Stock Shot %                         0.1   +50% first hit ≈ 5% over 10 hits
  Min Hit (flat)                      0.05   minor floor raise

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MAGIC DPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  Chaos Caster Echoes (flat)            30   2 free extra spells per cast
  Crackling Staff (ticks saved)          2   halves staff attack speed ≈ 2x DPS
  Magic Max Hit %                        1   direct +1% avg damage per %
  Zaros Edge Magic %                     1   same additive pool as Magic%
  Zam Edge Magic %                       1   same additive pool as Magic%
  All Styles Dmg %                       1   applies to every combat style
  Elemental Mastery %                  0.9   +25% elemental, ~90% uptime
  Blood Mastery %                      0.8   +25% blood spells, costs 15 HP/cast
  Forsaken Pact %                      0.7   +25% spells — but NO food healing
  vs Burning %                         0.6   +20% while burn active, ~60% uptime
  vs Frozen %                          0.5   needs frozen target, ~50% uptime
  Magic Crit %                         0.5   assume 50% crit damage bonus
  Volatile Cast %                     0.23   +35% but +1 tick: net only ~8% DPS
  Burn DoT Mult %                      0.2   doubles burn tick, burn ≈ 20% of DPS
  Arsonist % (post-patch)              0.2   now scales ALL max hit modifiers
  Min Hit (flat)                      0.05   minor floor raise

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BERSERKER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  Giant Slayer %/tile                    3   +5%/tile boss size, 3x3 = +15%
  Pious Fury /pray                       3   assume ~3 prayers active = +9% DPS
  Cheat Death %                          3   15% survive lethal hit (critical here)
  Berserker % (2H, <50 HP)               1   full uptime assumed — build stays low
  Melee Max Hit %                        1   direct +1% avg damage per %
  Bandos Wrath %                         1   same additive pool as Melee%
  All Styles Dmg %                       1   applies to every combat style
  Berserker Echo %                     0.8   extra melee hit proc on berserker
  Blindbag Proc %                      0.8   extra hit with bag weapon
  Reaching Echo % (2H)                 0.6   2H range echo proc, conditional
  Melee Crit %                         0.5   assume 50% crit damage bonus
  Sanguine Lifesteal %                 0.5   keep HP low for berserker activation
  Lifesteal %                          0.3   general healing at low HP
  Flurry %                            0.25   next hit 1t sooner — NOT a double hit
  Min Hit (flat)                      0.05   minor floor raise

  Note: Berserker only activates with 2H melee weapons below 50 HP.
```


===== POST 3 of 3 =====

```
PANTHEON PACT — SOLVER WEIGHTS (3/3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IRONMAN / SUSTAIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  Demonic HP %                           5   +25% max HP, single node
  HP Regen /5t                           5   passive HP tick regen
  Cheat Death %                          4   15% survive lethal hit
  Lifesteal %                            3   primary healing source
  Prayer Regen /5t                       3   keeps sustain resources topped
  Wild Refresh (kill)                    3   +5 prayer on every kill
  Kill Heal % HP                         3   +20% HP on ranged/ballista kill
  Sanguine Lifesteal %                 2.5   melee-specific healing
  Bark DR % (active)                     2   near-immunity window when active
  DR %                                   2   passive damage reduction
  Devout Vessel (HP bonus)               2   HP = prayer bonus % — NOT damage
  Renewal Prayer Restore                 2   prayer restore when Renewal procs
  Prayer Regen /12t                    1.5   slower regen, still adds up
  Kill Pray Restore                      1   prayer on kill
  Tough Bark %                           1   reduces damage while bark active
  Reflect %                            0.5   return damage to attackers
  Prayer Drain -%                      0.5   keeps sustain running passively
  Faith Surge %                        0.5   raises prayer bonus → more HP via Vessel
  HP (flat)                            0.3   direct HP increase
  Ammo Regen %                         0.3   resource sustain
  Thornbleed %                         0.3   bleed proc on attackers
  Melee Max Hit %                      0.2   minor DPS component
  Renewal Heal /hit                   0.05   100 HP healed per hit when active
  Min Hit (flat)                      0.02   minor floor raise

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SUMMONER / PET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  Tithe Summon LS %                      2   summon lifesteal is meaningful
  Tithe Summon %                         1   +55% summon damage keystone
  Legion %                               1   +25% summon damage keystone
  Conduit %                              1   +20% per summon keystone
  Pet Max Hit %                          1   +10% pet max hit
  Pet Dmg %                              1   direct pet damage %
  Soul Stoke %                           1   boss pet dmg per active summon
  Legion Magic %/summon                0.8   +10 magic str per summon to player
  Soul Tutelage %                      0.5   pet XP gain (not raw DPS)
  Crimson Bond %                       0.5   summon lifesteal
  Conduit Pen %/summon                 0.4   +10% prayer pen per summon
  Pet Lifesteal %                      0.4   pet healing
  Lifesteal %                          0.2   general sustain
  DR %                                 0.1   minor survival

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SLAYER / HYBRID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Effect                            Weight   Reasoning
  ──────────────────────────────── ───────   ─────────────────────────────
  1H Speed (-1 tick)                    15   +25% attack rate on task with 1H
  Giant Slayer %/tile                    2   slayer bosses are usually large
  Pious Fury /pray                       2   assume ~3 prayers active on task
  Slayer Helm % (now additive)         1.5   +5% additive per node after patch
  All Styles Dmg %                     1.5   applies to all three combat styles
  Gale Roots %/stack                   1.5   5 stacks = +15% sustained on boss
  Melee Max Hit %                        1   direct damage
  Ranged Max Hit %                       1   direct damage
  Magic Max Hit %                        1   direct damage
  Sniper %                               1   direct +7%, multiplies with Eye
  Eye Dist Dmg %/tile                  0.6   +3%/tile at range, up to +24%
  Melee Crit %                         0.5   assume 50% crit damage bonus
  Ranged Crit %                        0.5   assume 50% crit damage bonus
  Magic Crit %                         0.5   assume 50% crit damage bonus
  Prayer Pen %                         0.2   ~40% of task enemies use prayer
  DR %                                 0.1   minor survival
  Lifesteal %                          0.1   minor sustain
  Min Hit (flat)                      0.05   minor floor raise
  HP (flat)                           0.02   minor survival

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  KEY CORRECTIONS vs EARLIER VERSIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Devout Vessel  — gives HP equal to prayer bonus %, NOT prayer damage
  Flurry         — makes next attack 1 tick sooner, NOT a double hit
  Crackling Staff — halves powered staff attack speed (roughly 2x DPS)
  1H Affinity    — -1 tick on 1H weapons = +25% attacks, previously missed
  Chaos Caster   — 2 free extra elemental spells per cast, no rune cost
  Berserker      — only activates with 2H melee weapons while below 50 HP
  Slayer Mantle  — now additive after patch (e.g. 15% + 5% = 20%, not 15.75%)
  Arsonist       — now scales with ALL max hit modifiers after patch
  Paladin hammers — scaling buffed in latest patch, actual new values TBC
```
