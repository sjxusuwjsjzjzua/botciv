"""Default numbers for the world. Any of them can be overridden by a TOML file."""
import copy
import tomllib

DEFAULTS = {
    "world": {
        "width": 24,
        "height": 24,
        "seed": 1,
        "agents": 14,
        "max_population": 22,
        "bushes": 44,
        "herds": 3,
        "herd_size": [5, 9],
        "ticks_per_day": 12,
        "night_from": 9,            # hours 9..11 are night
        "days_per_season": 10,
        "arrival_every_days": 8,    # mean days between strangers walking in
        "arrival_below": 18,        # strangers only come while population is below this
        "fertile_share": 0.35,      # share of grass next to water that is fertile
    },
    "agent": {
        "max_health": 10,
        "max_satiety": 20,
        "start_satiety": 18,
        "hunger_every": 3,          # lose 1 satiety every N ticks (4 a day)
        "starve_every": 3,          # at 0 satiety, lose 1 health every N ticks
        "heal_every": 6,            # fed agents heal 1 health every N ticks
        "heal_every_resting": 2,
        "capacity": 20.0,
        "sight_day": 5,
        "sight_night": 2,
        "lifespan_years": [3.0, 5.5],
        "adult_ticks": 240,
        "start_age_years": [0.6, 2.2],
        "child_cost": 6,            # satiety each parent pays
        "child_min_satiety": 12,
        "child_hope_days": 10,      # an agreed child is conceived when both are fed and together, within this
        "gestation_ticks": 24,
        "memory_chars": 600,
        "belief_chars": 160,
        "self_chars": 160,       # who they have become, one sentence
        "life_chars": 120,       # each line kept for life
        "life_lines": 6,         # lines kept for life; the first ever kept is never dropped
    },
    "resources": {
        "weather": {"fibre": 0.15, "hide": 0.1, "wood": 0.07},   # share lost each day on the ground
        "bush_max": 8,
        "bush_regrow": {"spring": 7, "summer": 8, "autumn": 7, "winter": 0},  # ticks per berry, 0 = none
        "bush_die_chance": 0.01,    # each time a bush is picked bare: chance x times it has been bare this season
        "bush_spread_chance": 0.004,  # per living bush per tick in spring/summer
        "herd_move_every": 3,
        "herd_grow_every_days": 3,
        "herd_max": 12,
        "hunt_chance": [0.0, 0.04, 0.45, 0.7, 0.85],   # by hunters ready (index capped)
        "spear_bonus": 0.12,
        "hunt_meat": 8,
        "fish_chance": 0.12,
        "fish_chance_net": 0.45,
        "fish_chance_spear": 0.2,
        "seed_chance": 0.25,        # gathering fibre in summer/autumn also finds seeds
        "seed_chance_berries": 0.1, # ...and so, less often, does picking berries
        "farm_grow_ticks": 48,
        "grain_per_seed": 6,
        "farm_max_seeds": 8,        # a full farm yields 48 grain, which keeps: the road to a surplus
        "fire_ticks": 24,
        "cold_chance": 0.25,        # winter night, unsheltered: chance per tick of 1 damage
        "snare_chance": 0.06,       # per tick, a set snare catches a small animal
        "wolf_packs": 1,
        "wolf_pack_size": [2, 4],
        "wolf_hp": 5,               # per wolf
        "wolf_bite_chance": 0.3,    # per hour, at a lone person next to the pack
        "wolf_damage": 2,
    },
    "combat": {
        "base_damage": 1,
        "spear_damage": 2,
        "ally_damage": 1,
        "retaliation": 1,
        "resting_bonus": 1,
        "watched": 0.2,             # a stealthy theft's chance falls this much per person of the victim's beside the thief
    },
    "mind": {
        "kind": "gemini",           # gemini | simple | reciprocity | replay
        "quiet_ticks": 24,          # ask an idle-but-busy agent at least this often
        "speech_wake_gap": 3,       # a listener is woken by speech at most once per N ticks
        "speech_wake_gap_busy": 6,  # ... and one busy with a task at most once per N ticks
        "events_full": 12,
        "ledger_recent": 10,
        "max_failures_before_bot": 2,
    },
}


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path=None, overrides=None):
    cfg = copy.deepcopy(DEFAULTS)
    if path:
        with open(path, "rb") as f:
            cfg = deep_merge(cfg, tomllib.load(f))
    if overrides:
        cfg = deep_merge(cfg, overrides)
    return cfg
