# Vessel slot colours sourced from https://eldenring.wiki.gg/wiki/Nightreign:Vessels
# Each entry: (vessel name, standard slots, deep of night slots).
# R/B/Y/G/W = red/blue/yellow/green/white (white accepts any colour).

NIGHTFARERS = [
    "Wylder",
    "Guardian",
    "Ironeye",
    "Duchess",
    "Raider",
    "Revenant",
    "Recluse",
    "Executor",
    "Scholar",
    "Undertaker",
]

UNIVERSAL_VESSELS = [
    ("Sacred Erdtree Grail", "YYY", "YYY"),
    ("Spirit Shelter Grail", "GGG", "GGG"),
    ("Giant's Cradle Grail", "BBB", "BBB"),
    ("Scadutree Grail", "RRR", "RRR"),
]

# Order: Urn, Goblet, Chalice, Soot-Covered Urn, Sealed Urn,
# Decrepit Goblet, Forgotten Goblet.
NIGHTFARER_VESSEL_SLOTS = {
    "Wylder": [
        "RRB/RRB",
        "YGG/YGG",
        "RYW/RBG",
        "BBY/BBY",
        "BRR/GYY",
        "BGY/BGY",
        "GYY/RGW",
    ],
    "Guardian": [
        "RYY/RYY",
        "BBG/BBG",
        "BYW/RBY",
        "RGG/RGG",
        "YYR/GGB",
        "YGG/YGG",
        "GBB/RBW",
    ],
    "Ironeye": [
        "YGG/YGG",
        "RBY/RBY",
        "RGW/RRG",
        "BYY/BYY",
        "GGY/BBR",
        "BBG/BGG",
        "YBR/YGW",
    ],
    "Duchess": [
        "RBB/RBB",
        "YYG/YYG",
        "BYW/RBY",
        "RRG/RRG",
        "BBR/GGY",
        "BGG/BGG",
        "GYY/RGW",
    ],
    "Raider": [
        "RGG/RGG",
        "RBY/RBY",
        "RRW/RYY",
        "BBG/BBG",
        "GGR/YBB",
        "YYG/YYG",
        "YBR/RGW",
    ],
    "Revenant": [
        "BBY/BBY",
        "RRG/RRG",
        "BGW/BYG",
        "RYY/RYY",
        "YBB/GGR",
        "RRY/RRY",
        "GRR/YGW",
    ],
    "Recluse": [
        "BBG/BBG",
        "RBY/RBY",
        "YGW/BGG",
        "RRY/RRY",
        "GBB/YYR",
        "YYB/YYB",
        "YBR/BGW",
    ],
    "Executor": [
        "RYY/RYY",
        "RBG/RBG",
        "BYW/YYG",
        "RRB/RRB",
        "YYR/GGB",
        "RRY/RRY",
        "GBR/YGW",
    ],
    "Scholar": [
        "RRY/RRY",
        "BGY/BGY",
        "RBW/RYY",
        "BGG/BGG",
        "YRR/GBB",
        "BBG/BBG",
        "YGB/YGW",
    ],
    "Undertaker": [
        "BGG/BGG",
        "RYY/RYY",
        "GYW/BGY",
        "RRB/RRB",
        "GGB/YRR",
        "RBB/RBB",
        "YYR/BYW",
    ],
}

VESSEL_NAME_TEMPLATES = [
    "{owner} Urn",
    "{owner} Goblet",
    "{owner} Chalice",
    "Soot-Covered {owner} Urn",
    "Sealed {owner} Urn",
    "Decrepit {owner} Goblet",
    "Forgotten {owner} Goblet",
]


def possessive(name: str) -> str:
    return f"{name}'" if name.endswith("s") else f"{name}'s"
