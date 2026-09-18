"""Sélection éditoriale rap français 2016–2026 ; notes et cachets fictifs de jeu.

Les groupes comptent comme une affiche. Ce catalogue rétrospectif ne représente
ni un classement officiel, ni la disponibilité réelle des artistes.
"""

# Note : rayonnement sur la période, discographie et potentiel d'ambiance en club.
RAP_SELECTION = [
    ("Jul", 99), ("Ninho", 99), ("PNL", 98), ("Booba", 98),
    ("Nekfeu", 97), ("Orelsan", 97), ("SCH", 97), ("Gims", 96),
    ("Niska", 95), ("Gazo", 95), ("Tiakola", 95), ("Werenoi", 94),
    ("SDM", 94), ("PLK", 94), ("Soprano", 93), ("Naps", 92),
    ("Djadja & Dinaz", 92), ("Vald", 92), ("Kaaris", 91), ("Zola", 91),
    ("Soolking", 91), ("Alonzo", 90), ("Lacrim", 90), ("Lomepal", 90),
    ("Josman", 90), ("Hamza", 90), ("Damso", 97), ("Leto", 89),
    ("Heuss L'Enfoiré", 88), ("Koba LaD", 88), ("Maes", 89), ("Dinos", 89),
    ("Bigflo & Oli", 89), ("Soso Maness", 87), ("S.Pri Noir", 85),
    ("Timal", 85), ("Guy2Bezbar", 86), ("La Fève", 87), ("Favé", 86),
    ("La Mano", 85), ("L2B", 85), ("Nono la grinta", 84), ("Kerchak", 84),
    ("MHD", 88), ("Gradur", 86), ("Naza", 86), ("Vegedream", 83),
    ("Franglish", 85), ("Black M", 84), ("Dadju", 88), ("Fianso", 87),
    ("Rim'K", 87), ("Rohff", 87), ("Kery James", 86), ("Youssoupha", 87),
    ("Médine", 85), ("Disiz", 87), ("Oxmo Puccino", 85), ("IAM", 87),
    ("MC Solaar", 86), ("Seth Gueko", 81), ("Sinik", 80), ("R.E.D.K.", 78),
    ("Hugo TSR", 84), ("Georgio", 83), ("Caballero & JeanJass", 82),
    ("Luidji", 88), ("Bekar", 82), ("Zamdane", 84), ("Demi Portion", 80),
    ("Swift Guad", 77), ("Davodka", 79), ("Scylla", 81), ("Freeze Corleone", 89),
    ("Alpha Wann", 88), ("Deen Burbigo", 83), ("Sneazzy", 82), ("Jazzy Bazz", 84),
    ("Edge", 77), ("Esso Luxueux", 76), ("Lesram", 82), ("Infinit'", 80),
    ("Limsa d'Aulnay", 80), ("ISHA", 82), ("Prince Waly", 81),
    ("Ichon", 80), ("Ateyaba", 82), ("Bushi", 82), ("Green Montana", 83),
    ("Jolagreen23", 80), ("So La Lune", 83), ("Khali", 81), ("Luther", 84),
    ("Yamê", 85), ("Jeune Morty", 74), ("Shay", 88), ("Chilla", 80),
    ("Lala &ce", 81), ("Le Juiice", 76), ("Theodora", 89),
]


def artist_profile(rating):
    if rating >= 95:
        tier = "Légende"
    elif rating >= 90:
        tier = "Tête d'affiche"
    elif rating >= 82:
        tier = "Confirmé"
    else:
        tier = "Scène alternative"
    return {
        "rating": rating,
        "tier": tier,
        "collection": "rap_2016_2026",
        "bonus": round(0.28 + (rating - 65) * 0.02, 2),
        "cost": 15_000 + (rating - 65) * 750,
    }


RAP_ARTISTS = {name: artist_profile(rating) for name, rating in RAP_SELECTION}
RAP_PHRASES = {}
for name, rating in RAP_SELECTION:
    low = 30 + (rating - 65) * 2
    high = low + 60
    RAP_PHRASES[name] = [
        [f"{name} entre sur scène et la foule se presse devant le club.", low, high],
        [f"Le public reprend les classiques de {name}, la piste est en feu.", low + 5, high + 5],
        [f"Le showcase de {name} se termine sous les cris de toute la salle.", low, high + 10],
    ]
