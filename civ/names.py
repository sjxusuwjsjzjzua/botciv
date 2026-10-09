"""Names, temperaments and wants, drawn from the world's random stream."""
ONSETS = ["k", "t", "m", "n", "s", "r", "l", "v", "d", "b", "h", "y", "z", "p", "g", "f", "th", "sh", "br", "dr",
          "kh", "tr", "gl", "st", "w", "j"]
VOWELS = ["a", "e", "i", "o", "u", "ai", "ea", "o", "a", "i", "ae", "ou"]
CODAS = ["", "", "n", "r", "l", "s", "k", "m", "th", "sh", "nd", "rn"]


# sounds a name must never hold (words in the tongues the people's own words are read in)
UNFIT = ("shit", "fuck", "cunt", "piss", "cock", "dick", "slut", "whor", "rape", "nazi", "fag", "nig", "tit", "anus",
         "porn", "sex", "kill", "dead", "poo", "fart", "bum", "turd", "crap", "damn", "hell", "satan")


def make_name(rng, taken, tongue=None):
    """A name not yet taken, in the sounds of a tongue (a people's: civ/content/peoples.py) or the old common ones."""
    on, vo, co = (tongue["onsets"], tongue["vowels"], tongue["codas"]) if tongue else (ONSETS, VOWELS, CODAS)
    for _ in range(400):
        n = rng.choice(on) + rng.choice(vo) + rng.choice(co)
        if rng.random() < 0.55:
            n += rng.choice(on) + rng.choice(vo) + rng.choice(["", "", "n", "r", "l", "s"] if not tongue else co)
        n = n.capitalize()
        if 3 <= len(n) <= 9 and n not in taken and not any(u in n.lower() for u in UNFIT):
            taken.add(n)
            return n
    n = f"Ash{len(taken)}"
    taken.add(n)
    return n


VALUES = ["loyal to family", "loyal to friends", "proud", "generous", "thrifty", "curious",
          "fair-minded", "ambitious", "devout about promises", "suspicious of strangers",
          "welcoming to strangers", "vengeful", "forgiving", "hungry for respect",
          "fond of stories", "protective of the weak", "practical", "restless",
          "fond of solitude", "loves company", "wants to lead", "dislikes being told what to do",
          "values fairness above all", "values safety above all", "likes to bargain",
          "honest to a fault", "sly", "patient", "hot-tempered", "gentle", "devout", "inventive",
          "proud of their craft", "fond of beautiful things"]
RISK = ["very cautious", "cautious", "steady", "bold", "reckless"]

WANTS = ["a family of your own", "to be looked up to by others", "never to go hungry again",
         "to master a craft no one else has", "to be left alone", "to lead others",
         "to have more than anyone else", "close friends you can trust", "to know every corner of the land",
         "to keep your kin safe", "to be remembered after you are gone", "peace between everyone",
         "to get even with anyone who wrongs you", "comfort and ease", "to be free of anyone's rule",
         "to build something that lasts", "to see your people grow great", "to learn everything that can be learned"]


def temperament(rng):
    vals = rng.sample(VALUES, 3)
    return f"{vals[0]}, {vals[1]}, {vals[2]}; {rng.choice(RISK)}"


def want(rng):
    return rng.choice(WANTS)


# A household's rules, in the words of its founder's nature (bot founders; the people word their own). Every
# bot household once had the same sentence: 66 of world2's 67 groups, and 97 cairns carried it.
RULE_LINES = {
    "generosity": ["No one of us goes hungry while another has food.", "What one gathers, all may eat.",
                   "The old and the young eat first.", "We give to those who ask in need."],
    "industry": ["Every store is full before winter.", "Each hand works from dawn; the idle eat last.",
                 "We mend what we use and waste nothing.", "A field left bare is a shame on us all."],
    "ambition": ["{leader} leads, and we follow.", "Each year our fields reach further.",
                 "Our name will be known across the land.", "We bow to no other household."],
    "sociability": ["Strangers who come in peace may eat at our fire.", "Quarrels are settled by talk, not blows.",
                    "We meet at the fire each evening.", "A guest is never turned away at night."],
    "curiosity": ["Whoever learns a craft teaches it to the rest.", "We try what others have not.",
                  "Every child learns two crafts.", "What is learnt is never kept secret among us."],
    "boldness": ["A blow against one of us is a blow against all.", "We do not run from wolves or men.",
                 "We hunt together and share the kill.", "Who wrongs us answers for it."],
    "caution": ["Our stores stay closed to strangers.", "No one walks alone after dark.",
                "We keep a fire burning through the night.", "We lend nothing we cannot spare."],
}


def group_rules(rng, traits, leader):
    """Two lines from the founder's strongest leanings (cautious if not bold)."""
    t = dict(traits or {})
    t["caution"] = 1 - t.get("boldness", 0.5)
    keys = sorted((k for k in RULE_LINES if k in t), key=lambda k: -(t[k] + 0.3 * rng.random()))[:2] or ["generosity"]
    return " ".join(rng.choice(RULE_LINES[k]).format(leader=leader) for k in keys)
