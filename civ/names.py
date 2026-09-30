"""Names, temperaments and wants, drawn from the world's random stream."""
ONSETS = ["k", "t", "m", "n", "s", "r", "l", "v", "d", "b", "h", "y", "z", "p", "g", "f", "th", "sh", "br", "dr",
          "kh", "tr", "gl", "st", "w", "j"]
VOWELS = ["a", "e", "i", "o", "u", "ai", "ea", "o", "a", "i", "ae", "ou"]
CODAS = ["", "", "n", "r", "l", "s", "k", "m", "th", "sh", "nd", "rn"]


def make_name(rng, taken):
    for _ in range(400):
        n = rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(CODAS)
        if rng.random() < 0.55:
            n += rng.choice(ONSETS) + rng.choice(VOWELS) + rng.choice(["", "", "n", "r", "l", "s"])
        n = n.capitalize()
        if 3 <= len(n) <= 9 and n not in taken:
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
