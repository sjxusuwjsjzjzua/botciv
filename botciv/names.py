"""Short pronounceable names, drawn from the world's RNG."""
ONSETS = ["k", "t", "m", "n", "s", "r", "l", "v", "d", "b", "h", "y", "z", "p", "g", "f", "th", "sh", "br", "dr"]
VOWELS = ["a", "e", "i", "o", "u", "ai", "ea", "o", "a", "i"]
CODAS = ["", "", "n", "r", "l", "s", "k", "m", "th", "sh"]


def make_name(rng, taken):
    for _ in range(200):
        n = rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(CODAS)
        if rng.random() < 0.55:
            n += rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(["", "", "n", "r", "l"])
        n = n.capitalize()
        if 3 <= len(n) <= 8 and n not in taken:
            return n
    i = len(taken)
    return f"Ash{i}"


VALUES = ["loyal to family", "loyal to friends", "proud", "generous", "thrifty", "curious",
          "fair-minded", "ambitious", "devout about promises", "suspicious of strangers",
          "welcoming to strangers", "vengeful", "forgiving", "hungry for respect",
          "fond of stories", "protective of the weak", "practical", "restless",
          "fond of solitude", "loves company", "wants to lead", "dislikes being told what to do",
          "values fairness above all", "values safety above all", "likes to bargain",
          "honest to a fault", "sly", "patient", "hot-tempered", "gentle"]
RISK = ["very cautious", "cautious", "steady", "bold", "reckless"]


def make_temperament(rng):
    vals = rng.sample(VALUES, 3)
    return f"{vals[0]}, {vals[1]}, {vals[2]}; {rng.choice(RISK)}"
