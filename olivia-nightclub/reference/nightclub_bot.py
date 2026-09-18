import os
import re
import json
import time
import random
import asyncio
import unicodedata
import discord
from flex import CARS, WATCHES, BITCOIN_PRICE, RESALE_RATE, flex_embed

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_FILE = os.path.join(
    BASE_DIR,
    "nightclub_data.json"
)

TICK_SECONDS = 180

DARK = 0x101014
DARK_2 = 0x18181F
GOLD = 0x8B7A55

ARTIST_SHOWCASE_BONUS = {
    "Boro 700": 0.66,
    "Gims": 0.55,
    "PLK": 0.50,
    "Leto": 0.47,
    "L2B": 0.44,
    "La Mano": 0.42,
    "Nono la grinta": 0.40,
    "Timal": 0.38,
    "TK": 0.36,
    "Niaks": 0.34,
    "Le Crime": 0.32,
    "3robi": 0.30,
    "Mensa": 0.28,
    "RnBoi": 0.26,
    "Timar": 0.24,
    "La Rvfleuse": 0.22,
    "Lagui": 1.00,
    "Bello&Dallas": 0.18,
}

ARTISTS = [
    "Lagui",
    "Boro 700"
] + [
    artist
    for artist in ARTIST_SHOWCASE_BONUS.keys()
    if artist not in ("Lagui", "Boro 700")
]


# Phrases aléatoires affichées quand un showcase vient d'avoir lieu.
# Chaque phrase donne aussi un petit bonus de clientèle.
SHOWCASE_PHRASES = {
    "Boro 700": [
        ("Boro 700 est arrivé comme un patron, le carré s'est rempli en quelques minutes.", 65, 135),
        ("Boro 700 a retourné la scène et ramené une grosse vague de clients.", 70, 140),
        ("Le passage de Boro 700 a mis toute la boîte en tension.", 60, 130),
        ("Boro 700 a fait lever toute la salle, personne ne voulait partir.", 65, 135),
        ("Boro 700 a transformé la soirée en vraie nuit de patron.", 75, 145),
    ],
    "Lagui": [
        ("Lagui a retourné la boîte, la foule connaissait chaque parole.", 90, 180),
        ("Lagui a fait trembler les murs, personne ne voulait quitter la piste.", 100, 200),
        ("Lagui est monté sur scène et la soirée est partie en folie.", 80, 170),
        ("Lagui a terminé son showcase sous les cris de toute la salle.", 95, 190),
        ("Le showcase de Lagui a fait parler toute la ville cette nuit.", 110, 210),
    ],
    "Gims": [
        ("Gims a lancé ses classiques, toute la salle a chanté avec lui.", 70, 140),
        ("Gims a rempli la piste dès son arrivée sur scène.", 65, 135),
        ("Le passage de Gims a attiré une grosse foule devant la boîte.", 75, 150),
        ("Gims a mis une ambiance énorme jusqu'à la fin du showcase.", 70, 145),
    ],
    "PLK": [
        ("PLK a mis le feu au carré, les clients se sont rapprochés de la scène.", 65, 135),
        ("PLK a enchaîné les morceaux et la boîte s'est remplie.", 60, 130),
        ("Le showcase de PLK a ramené du monde jusqu'à l'entrée.", 70, 140),
        ("PLK a retourné le public avec une fin de showcase explosive.", 65, 145),
    ],
    "Leto": [
        ("Leto a fait monter la pression dès son premier morceau.", 55, 125),
        ("Leto a retourné le carré VIP, la salle était bouillante.", 60, 130),
        ("Le public a suivi Leto du début à la fin du showcase.", 50, 120),
        ("Leto a ramené une vraie ambiance de nuit dans toute la boîte.", 60, 135),
    ],
    "L2B": [
        ("L2B a débarqué à plusieurs et la salle s'est immédiatement réveillée.", 55, 125),
        ("L2B a enchaîné les sons, la piste ne s'est pas vidée.", 50, 120),
        ("Le showcase de L2B a attiré une grosse bande de clients.", 60, 130),
        ("L2B a mis une ambiance collective énorme dans la boîte.", 55, 125),
    ],
    "La Mano": [
        ("La Mano a mis tout le monde debout dès son entrée.", 50, 115),
        ("La Mano a chauffé la salle et les clients ont afflué.", 55, 120),
        ("Le showcase de La Mano a fait monter l'ambiance d'un cran.", 45, 110),
        ("La Mano a terminé son passage sous une salle en folie.", 50, 120),
    ],
    "Nono la grinta": [
        ("Nono la grinta a ramené une énergie folle sur scène.", 45, 110),
        ("Nono la grinta a fait sauter toute la première rangée.", 50, 115),
        ("Le showcase de Nono la grinta a attiré du monde au dernier moment.", 40, 105),
        ("Nono la grinta a laissé la salle en ébullition.", 45, 110),
    ],
    "Timal": [
        ("Timal a retourné la piste avec un showcase très chaud.", 45, 105),
        ("Timal a fait chanter la salle jusqu'à la dernière minute.", 40, 100),
        ("Le passage de Timal a ramené plusieurs groupes de clients.", 45, 110),
        ("Timal a mis une grosse ambiance devant la scène.", 40, 105),
    ],
    "TK": [
        ("TK a chauffé la salle et les téléphones se sont levés partout.", 40, 100),
        ("TK a fait bouger toute la piste pendant son showcase.", 35, 95),
        ("Le showcase de TK a ramené de nouveaux clients dans la nuit.", 40, 100),
        ("TK a terminé son passage avec toute la salle debout.", 35, 95),
    ],
    "Niaks": [
        ("Niaks a mis la pression sur scène, le public a suivi.", 35, 95),
        ("Niaks a retourné le premier rang pendant son showcase.", 35, 90),
        ("Le passage de Niaks a ramené une nouvelle vague de clients.", 40, 100),
        ("Niaks a gardé la piste pleine jusqu'à la fin.", 35, 95),
    ],
    "Le Crime": [
        ("Le Crime a mis une ambiance sombre et lourde dans toute la boîte.", 35, 90),
        ("Le Crime a captivé la salle pendant tout son showcase.", 30, 85),
        ("Le showcase de Le Crime a ramené des curieux jusque devant l'entrée.", 35, 95),
        ("Le Crime a terminé son passage sous les cris du public.", 30, 90),
    ],
    "3robi": [
        ("3robi a ramené une grosse énergie et le public a suivi.", 30, 85),
        ("3robi a fait bouger la salle dès les premières secondes.", 35, 90),
        ("Le showcase de 3robi a ramené du monde sur la piste.", 30, 85),
        ("3robi a transformé la fin de soirée en vrai concert.", 35, 95),
    ],
    "Mensa": [
        ("Mensa a surpris la salle avec un showcase très propre.", 30, 80),
        ("Mensa a ramené une nouvelle ambiance dans la boîte.", 25, 75),
        ("Le public s'est rapproché de la scène pendant le passage de Mensa.", 30, 85),
        ("Mensa a fini son showcase avec une salle bien remplie.", 25, 80),
    ],
    "RnBoi": [
        ("RnBoi a posé une ambiance mélodique, les clients sont restés sur la piste.", 25, 75),
        ("RnBoi a attiré du monde autour de la scène.", 30, 80),
        ("Le showcase de RnBoi a donné une autre vibe à toute la boîte.", 25, 75),
        ("RnBoi a terminé son passage avec un public conquis.", 30, 85),
    ],
    "Timar": [
        ("Timar a mis une bonne pression sur scène et la salle a répondu.", 25, 70),
        ("Timar a ramené plusieurs nouveaux groupes dans la boîte.", 25, 75),
        ("Le showcase de Timar a gardé les clients jusqu'à tard.", 20, 70),
        ("Timar a fini son passage devant une piste bien remplie.", 25, 75),
    ],
    "La Rvfleuse": [
        ("La Rvfleuse a réveillé la salle avec un passage énergique.", 20, 65),
        ("La Rvfleuse a attiré plusieurs curieux devant la scène.", 20, 70),
        ("Le showcase de La Rvfleuse a donné un coup de boost à la soirée.", 25, 70),
        ("La Rvfleuse a gardé la piste animée jusqu'à la fin.", 20, 65),
    ],
    "Bello&Dallas": [
        ("Bello & Dallas ont retourné la boîte, le public a suivi jusqu'au dernier son.", 25, 80),
        ("Bello & Dallas ont mis une ambiance chaotique mais la salle a adoré.", 30, 85),
        ("Le duo Bello & Dallas a fait rester les clients bien après le showcase.", 25, 75),
        ("Bello & Dallas ont chauffé le carré et ramené du monde devant la scène.", 30, 80),
    ],
}


def generate_showcase_event(artist):
    """
    Produit une phrase et un bonus/malus clients pour le showcase.
    Certains artistes ont des événements spéciaux.
    """

    # Boro 700 : 60 % de chance de déclencher le pacte avec Saisai.
    if artist == "Boro 700" and random.random() < 0.60:
        gained = random.randint(
            80,
            160
        )

        return {
            "artist": artist,
            "text": (
                "Boro 700 a pacté avec la boîte : Saisai débarque par surprise "
                "et transforme la soirée en double showcase. La salle devient incontrôlable."
            ),
            "clients": gained,
            "boro_saisai_combo": True,
        }

    if artist == "Bello&Dallas":
        roll = random.random()

        # 15 % : événement négatif
        if roll < 0.15:
            lost = random.randint(
                30,
                90
            )

            return {
                "artist": artist,
                "text": (
                    "Bello a frappé un client car il a snappé son ventre. "
                    "La sécurité a calmé la situation et une partie du public est partie."
                ),
                "clients": -lost,
            }

        # 15 % : événement drôle/positif
        if roll < 0.30:
            gained = random.randint(
                60,
                140
            )

            return {
                "artist": artist,
                "text": (
                    "Bello a sorti son ventre en plein showcase, toute la salle a rigolé "
                    "et les vidéos ont ramené encore plus de monde."
                ),
                "clients": gained,
            }

    choices = SHOWCASE_PHRASES.get(
        artist,
        [
            (
                f"{artist} a mis une grosse ambiance pendant son showcase.",
                20,
                60
            )
        ]
    )

    phrase, low, high = random.choice(
        choices
    )

    return {
        "artist": artist,
        "text": phrase,
        "clients": random.randint(
            low,
            high
        )
    }

DEFAULT_ENTRY_PRICE = 20
BASE_MAX_ENTRY_PRICE = 25.0

SHOWCASE_COST = 25_000  # prix plafond / compatibilité

def showcase_cost_for_artist(artist):
    """
    Les artistes avec le plus gros bonus coûtent jusqu'à 25 000 €.
    Le prix baisse progressivement avec leur bonus.
    """
    bonus = float(
        ARTIST_SHOWCASE_BONUS.get(
            artist,
            0.20
        )
    )

    if bonus >= 0.50:
        return 25_000
    if bonus >= 0.40:
        return 22_500
    if bonus >= 0.30:
        return 20_000
    if bonus >= 0.20:
        return 17_500

    return 15_000

# Économie de base, pensée pour une progression plus longue.
BAR_MIN = 900
BAR_MAX = 4_000
VIP_BASE_SPEND = 2_800

BOTTLE_PACKS = {
    "vodka": {
        "name": "Pack Vodka",
        "emoji": "🍾",
        "cost": 3_000,
        "receiver_bonus": 2_000,
        "description": "Petit pack pour faire plaisir à une autre boîte."
    },
    "belvedere": {
        "name": "Pack Belvedere",
        "emoji": "🥂",
        "cost": 7_500,
        "receiver_bonus": 5_000,
        "description": "Le classique du carré VIP."
    },
    "premium": {
        "name": "Pack Premium",
        "emoji": "🍾",
        "cost": 15_000,
        "receiver_bonus": 10_000,
        "description": "Un vrai envoi de patron."
    },
    "magnum": {
        "name": "Pack Magnum",
        "emoji": "👑",
        "cost": 30_000,
        "receiver_bonus": 20_000,
        "description": "Le gros pack qui fait parler toute la nuit."
    },
}


# Événements
EVENT_INTERVAL = 600       # 10 minutes
EVENT_CHANCE = 0.25        # 25 %

# Salon unique autorisé pour tout le mode Nightclub.
NIGHTCLUB_CHANNEL_ID = 1550305544009420800

# Bonus de départ réservé à ton compte.
OWNER_BONUS_USER_ID = 734865069904756766
OWNER_BONUS_AMOUNT = 1_000_000_000



def robbery_power(club):
    """
    Puissance de braquage / défense de la boîte.

    Chaque niveau de standing : +4 points.
    Chaque équipement acheté : +1 point.

    Si les deux boîtes ont la même puissance, le braquage reste à 50 %.
    """
    level = int(
        club.get(
            "level",
            0
        )
    )

    equipment_count = len(
        club.get(
            "equipment",
            []
        )
    )

    return (
        level * 4
        + equipment_count
    )


def robbery_success_chance(attacker, defender):
    """
    Chance finale de réussite :
    50 % + puissance attaquant - puissance défenseur.

    Limites : minimum 20 %, maximum 80 %.
    """
    chance = (
        50
        + robbery_power(attacker)
        - robbery_power(defender)
    )

    return max(
        20,
        min(
            80,
            chance
        )
    )


def artist_cooldown_remaining(club, artist):
    """
    Un même artiste ne peut pas être repris avant que 2 services complets
    se soient écoulés depuis son dernier showcase.
    """
    history = club.get(
        "artist_last_service",
        {}
    )

    last_service = history.get(
        artist
    )

    if last_service is None:
        return 0

    current_service = int(
        club.get(
            "service_count",
            0
        )
    )

    elapsed = (
        current_service
        - int(last_service)
    )

    return max(
        0,
        2 - elapsed
    )


def artist_is_available(club, artist):
    return artist_cooldown_remaining(
        club,
        artist
    ) <= 0

def client_range_for_level(level):
    """
    Nombre de clients par service de 3 minutes.
    La fréquentation augmente avec le standing de la boîte.
    """
    if level >= 6:
        return 575, 1380   # Le Olivia

    if level >= 5:
        return 485, 1150   # Miami Club

    if level >= 4:
        return 405, 980    # Le Bikini

    if level >= 3:
        return 325, 805    # Balajo

    if level >= 2:
        return 230, 690    # L'Ikona

    if level >= 1:
        return 140, 635    # Babinski

    return 60, 575         # Sans amélioration



def entry_price_client_multiplier(level, entry_price):
    """
    Effet léger du prix d'entrée sur le nombre de clients.

    - prix très bas : petit bonus de fréquentation
    - prix moyen : presque neutre
    - prix maximum : petite baisse de fréquentation

    L'effet reste volontairement faible : entre environ +6 % et -6 %.
    """
    minimum = 0.0
    maximum = float(
        max_entry_price(
            level
        )
    )

    if maximum <= minimum:
        return 1.0

    price = max(
        minimum,
        min(
            float(entry_price),
            maximum
        )
    )

    ratio = (
        price - minimum
    ) / (
        maximum - minimum
    )

    # 0 € => +6 %
    # moitié du max => environ neutre
    # max => -6 %
    return 1.06 - (
        0.12
        * ratio
    )


# Coûts choisis pour rendre le jeu progressif.
# Tu peux les changer plus tard uniquement dans nightclub.py.
UPGRADE_COSTS = {
    1: 100_000,      # Babinski
    2: 500_000,      # L'Ikona
    3: 1_200_000,    # Balajo
    4: 2_500_000,    # Le Bikini
    5: 5_000_000,    # Miami Club
    6: 10_000_000,   # Le Olivia
}



MANAGERS = {
    "victoria": {
        "name": "Victoria",
        "level": 1,
        "salary": 1000,
        "client_bonus": (5, 20),
        "vip_chance": 0.10,
        "showcase_chance": 0.10,
        "showcase_cooldown_ticks": 6,
        "description": "Débutante : petite pub, quelques clients en plus, rares VIP et showcases."
    },
    "josas": {
        "name": "Josas",
        "level": 2,
        "salary": 2500,
        "client_bonus": (20, 60),
        "vip_chance": 0.22,
        "showcase_chance": 0.22,
        "showcase_cooldown_ticks": 3,
        "description": "Confirmée : vraie promo, plus de clients, VIP plus fréquents et showcases réguliers."
    },
    "olivia": {
        "name": "Olivia",
        "level": 3,
        "salary": 5000,
        "client_bonus": (50, 120),
        "vip_chance": 0.35,
        "showcase_chance": 0.35,
        "showcase_cooldown_ticks": 2,
        "description": "Premium : grosse communication, nombreux clients, VIP et showcases très efficaces."
    },
}

EQUIPMENT_UPGRADES = {
    "dj": {
        "name": "DJ résident premium",
        "emoji": "🎧",
        "cost": 75_000,
        "description": "+8 % sur les entrées",
        "entry_bonus": 0.08,
    },
    "dancers": {
        "name": "Équipe de danseuses",
        "emoji": "💃",
        "cost": 120_000,
        "description": "+8 % sur les dépenses VIP",
        "vip_bonus": 0.08,
    },
    "smoke": {
        "name": "Machines à fumée",
        "emoji": "🌫️",
        "cost": 45_000,
        "description": "+5 % sur le bar",
        "bar_bonus": 0.05,
    },
    "lights": {
        "name": "Lumières & lasers",
        "emoji": "✨",
        "cost": 90_000,
        "description": "+6 % sur les entrées",
        "entry_bonus": 0.06,
    },
    "sound": {
        "name": "Sono haut de gamme",
        "emoji": "🔊",
        "cost": 150_000,
        "description": "+6 % sur le bar et les entrées",
        "bar_bonus": 0.06,
        "entry_bonus": 0.06,
    },
    "security": {
        "name": "Sécurité renforcée",
        "emoji": "🕴️",
        "cost": 110_000,
        "description": "+5 % sur les dépenses VIP",
        "vip_bonus": 0.05,
    },
    "vip_room": {
        "name": "Carré VIP privé",
        "emoji": "♛",
        "cost": 250_000,
        "description": "+12 % sur les dépenses VIP",
        "vip_bonus": 0.12,
    },
    "bar_staff": {
        "name": "Barmans premium",
        "emoji": "🍸",
        "cost": 95_000,
        "description": "+8 % sur le bar",
        "bar_bonus": 0.08,
    },
    "decor": {
        "name": "Décoration luxe",
        "emoji": "🖤",
        "cost": 180_000,
        "description": "+5 % sur les entrées et le bar",
        "entry_bonus": 0.05,
        "bar_bonus": 0.05,
    },
}

data_lock = asyncio.Lock()


# ============================================================
# TEXTE / DONNÉES
# ============================================================

def normalize(text):
    text = str(
        text or ""
    ).strip().lower()

    text = unicodedata.normalize(
        "NFD",
        text
    )

    text = "".join(
        c
        for c in text
        if unicodedata.category(c) != "Mn"
    )

    text = re.sub(
        r"[^a-z0-9& ]+",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def money(value):
    value = float(value)

    if value.is_integer():
        return (
            f"{int(value):,}"
            .replace(
                ",",
                " "
            )
            + " €"
        )

    formatted = f"{value:,.2f}"

    formatted = (
        formatted
        .replace(",", " ")
        .replace(".", ",")
    )

    return (
        formatted
        + " €"
    )


def load_data():
    if not os.path.exists(
        DATA_FILE
    ):
        return {}

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            raw = json.load(
                f
            )

        if isinstance(
            raw,
            dict
        ):
            return raw

    except Exception as e:
        print(
            "♣️ Lecture nightclub_data :",
            repr(e)
        )

    return {}


def save_data(data):
    temp = (
        DATA_FILE
        + ".tmp"
    )

    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp,
        DATA_FILE
    )


def new_club(name):
    now = time.time()

    return {
        "name":
            str(name)[:40],
        "cash":
            0,
        "entry_price":
            DEFAULT_ENTRY_PRICE,
        "level":
            0,
        "last_tick":
            now,
        "total_bar":
            0,
        "total_entry":
            0,
        "total_vip":
            0,
        "total_vip_clients":
            0,
        "total_clients":
            0,
        "last_clients":
            0,
        "last_vips":
            0,
        "last_income":
            0,
        "showcase_artist":
            None,
        "showcase_pending":
            False,
        "showcase_bonus":
            0.0,
        "showcases_done":
            0,
        "last_showcase_event":
            None,
        "artist_last_service":
            {},
        "equipment":
            [],
        "last_event_check":
            now,
        "last_event":
            None,
        "last_fun_event":
            None,
        "client_penalty_next":
            0,
        "client_bonus_next":
            0,
        "coca_cherry_pending":
            False,
        "bar_mult_next":
            1.0,
        "entry_mult_next":
            1.0,
        "vip_mult_next":
            1.0,
        "blackjack_wins":
            0,
        "blackjack_losses":
            0,
        "drinks_taken":
            0,
        "manager_id":
            None,
        "manager_last_showcase_tick":
            -999999,
        "last_robbery_service":
            -999999,
        "service_count":
            0,
        "cars":
            [],
        "watches":
            [],
        "bitcoin":
            0,
    }


def level_name(level):
    if level >= 6:
        return "Le Olivia"

    if level >= 5:
        return "Miami Club"

    if level >= 4:
        return "Le Bikini"

    if level >= 3:
        return "Balajo"

    if level >= 2:
        return "L'Ikona"

    if level >= 1:
        return "Babinski"

    return "Club indépendant"


def income_multiplier(level):
    """
    Bonus général sur bar, entrées et VIP.
    Progression volontairement raisonnable.
    """
    if level >= 6:
        return 2.25   # +125 %

    if level >= 5:
        return 2.00   # +100 %

    if level >= 4:
        return 1.80   # +80 %

    if level >= 3:
        return 1.65   # +65 %

    if level >= 2:
        return 1.50   # +50 %

    if level >= 1:
        return 1.25   # +25 %

    return 1.0


def showcase_multiplier(level):
    """
    Bonus du showcase sur les entrées du prochain service.
    Le bonus augmente doucement avec le standing.
    """
    if level >= 6:
        return 1.55   # +55 %

    if level >= 5:
        return 1.50   # +50 %

    if level >= 4:
        return 1.45   # +45 %

    if level >= 3:
        return 1.425  # +42,5 %

    if level >= 2:
        return 1.375  # +37,5 %

    return 1.25       # +25 %


def max_entry_price(level):
    """
    Prix d'entrée maximum selon le standing.
    """
    if level >= 6:
        return 65.00

    if level >= 5:
        return 57.50

    if level >= 4:
        return 50.00

    if level >= 3:
        return 43.75

    if level >= 2:
        return 37.50

    if level >= 1:
        return 31.25

    return BASE_MAX_ENTRY_PRICE



def get_manager(club):
    manager_id = club.get(
        "manager_id"
    )

    if not manager_id:
        return None

    return MANAGERS.get(
        manager_id
    )


def manager_name(club):
    manager = get_manager(
        club
    )

    if not manager:
        return "Aucun"

    return manager["name"]


def manager_service_effects(club):
    """
    Effets automatiques du manager à chaque service de 3 minutes.
    Le salaire est payé à chaque service seulement si la trésorerie le permet.
    """
    manager = get_manager(
        club
    )

    if not manager:
        return {
            "paid": 0,
            "clients": 0,
            "vip_bonus": 0,
            "showcase_started": False,
            "showcase_artist": None,
        }

    salary = int(
        manager["salary"]
    )

    cash = int(
        club.get(
            "cash",
            0
        )
    )

    if cash < salary:
        # Pas assez pour le salaire : le manager ne produit aucun effet
        # mais n'est pas viré automatiquement.
        return {
            "paid": 0,
            "clients": 0,
            "vip_bonus": 0,
            "showcase_started": False,
            "showcase_artist": None,
        }

    club["cash"] = cash - salary

    low, high = manager[
        "client_bonus"
    ]

    clients_added = random.randint(
        low,
        high
    )

    vip_bonus = (
        1
        if random.random() < manager["vip_chance"]
        else 0
    )

    showcase_started = False
    showcase_artist = None

    current_tick = int(
        club.get(
            "service_count",
            0
        )
    )

    last_tick = int(
        club.get(
            "manager_last_showcase_tick",
            -999999
        )
    )

    cooldown = int(
        manager[
            "showcase_cooldown_ticks"
        ]
    )

    can_showcase = (
        current_tick - last_tick
        >= cooldown
    )

    # Le manager ne remplace pas un showcase déjà programmé par le joueur.
    if (
        can_showcase
        and not club.get("showcase_pending")
        and random.random() < manager["showcase_chance"]
    ):
        # Le manager choisit seulement un artiste qui n'est pas en cooldown.
        available_artists = [
            artist
            for artist in ARTISTS
            if artist_is_available(
                club,
                artist
            )
        ]

        if not available_artists:
            return {
                "paid": salary,
                "clients": clients_added,
                "vip_bonus": vip_bonus,
                "showcase_started": False,
                "showcase_artist": None,
            }

        showcase_artist = random.choice(
            available_artists
        )

        club["showcase_artist"] = showcase_artist
        club["showcase_pending"] = True
        club["showcase_bonus"] = float(
            ARTIST_SHOWCASE_BONUS.get(
                showcase_artist,
                0.20
            )
        )

        club["showcases_done"] = int(
            club.get(
                "showcases_done",
                0
            )
        ) + 1

        club["manager_last_showcase_tick"] = current_tick
        showcase_started = True

    return {
        "paid": salary,
        "clients": clients_added,
        "vip_bonus": vip_bonus,
        "showcase_started": showcase_started,
        "showcase_artist": showcase_artist,
    }


def equipment_bonus(club, bonus_key):
    owned = club.get(
        "equipment",
        []
    )

    total = 0.0

    for item_id in owned:
        item = EQUIPMENT_UPGRADES.get(
            item_id,
            {}
        )

        total += float(
            item.get(
                bonus_key,
                0.0
            )
        )

    return total


def vip_count():
    roll = random.random()

    # 30 % : deux VIP
    if roll < 0.30:
        return 2

    # 50 % : un VIP
    if roll < 0.80:
        return 1

    # 20 % : aucun VIP
    return 0



def process_random_event(club):
    """
    Vérifie les événements toutes les 10 minutes.
    À chaque contrôle : 25 % de chance qu'un événement se produise.
    """
    now = time.time()

    last_check = float(
        club.get(
            "last_event_check",
            now
        )
    )

    elapsed = now - last_check

    if elapsed < EVENT_INTERVAL:
        return None

    checks = int(
        elapsed // EVENT_INTERVAL
    )

    # On avance l'horloge même s'il ne se passe rien.
    club["last_event_check"] = (
        last_check
        + checks * EVENT_INTERVAL
    )

    event_happened = None

    # Si plusieurs périodes se sont écoulées hors ligne, on ne déclenche
    # au maximum qu'un seul événement pour éviter une punition excessive.
    if random.random() > EVENT_CHANCE:
        return None

    events = [
        "police",
        "fight",
        "road",
        "power",
        "influencer",
        "vip_party",
    ]

    event = random.choice(
        events
    )

    if event == "police":
        loss = min(
            5_000,
            int(
                club.get(
                    "cash",
                    0
                )
            )
        )

        club["cash"] = int(
            club.get(
                "cash",
                0
            )
        ) - loss

        event_happened = {
            "title": "🚨 Contrôle de police",
            "text": (
                "Un mineur a été contrôlé dans l'établissement. "
                f"Amende et frais : **-{money(loss)}**."
            )
        }

    elif event == "fight":
        loss = min(
            1_000,
            int(
                club.get(
                    "cash",
                    0
                )
            )
        )

        club["cash"] = int(
            club.get(
                "cash",
                0
            )
        ) - loss

        event_happened = {
            "title": "🥊 Bagarre dans la salle",
            "text": (
                f"Quelques dégâts à réparer : **-{money(loss)}**."
            )
        }

    elif event == "road":
        club["client_penalty_next"] = int(
            club.get(
                "client_penalty_next",
                0
            )
        ) + 50

        event_happened = {
            "title": "🚧 Route bloquée",
            "text": (
                "La rue devant la boîte est bloquée. "
                "Jusqu'à **50 clients** peuvent manquer au prochain service."
            )
        }

    elif event == "power":
        club["bar_mult_next"] = min(
            float(
                club.get(
                    "bar_mult_next",
                    1.0
                )
            ),
            0.50
        )

        event_happened = {
            "title": "⚡ Coupure de courant",
            "text": (
                "Les machines du bar ont été ralenties. "
                "Le prochain service du bar rapporte **50 % de moins**."
            )
        }

    elif event == "influencer":
        club["client_bonus_next"] = int(
            club.get(
                "client_bonus_next",
                0
            )
        ) + 25

        event_happened = {
            "title": "📸 Influenceur en vue",
            "text": (
                "Un influenceur a posté la soirée. "
                "Environ **+25 clients** au prochain service."
            )
        }

    elif event == "vip_party":
        club["vip_mult_next"] = max(
            float(
                club.get(
                    "vip_mult_next",
                    1.0
                )
            ),
            1.50
        )

        event_happened = {
            "title": "♛ Table VIP surprise",
            "text": (
                "Une grosse table VIP réserve au dernier moment. "
                "Les dépenses VIP du prochain service sont **+50 %**."
            )
        }

    club["last_event"] = event_happened

    return event_happened


FUN_EVENT_CHANCE = 0.70


def process_fun_event(club):
    """
    70 % de chance qu'un petit événement drôle arrive sur un service.
    Les effets restent légers pour ne pas casser l'économie.
    """
    if random.random() > FUN_EVENT_CHANCE:
        return None

    events = [
        {
            "title": "💌 Numéro récupéré",
            "text": (
                "Une femme vous a dragué toute la soirée. "
                "Vous repartez avec son numéro et un sourire de patron."
            ),
            "clients": random.randint(4, 12),
        },
        {
            "title": "⚽ Visite surprise",
            "text": (
                "Kylian Mbappé est passé danser quelques minutes dans la boîte. "
                "Les téléphones sont sortis instantanément."
            ),
            "clients": random.randint(35, 70),
        },
        {
            "title": "🍑 Soirée mouvementée",
            "text": (
                "Des danseuses ont twerké près de votre table toute la soirée. "
                "Votre moitié l'a appris avant même votre retour à la maison."
            ),
            "clients": random.randint(8, 20),
        },
        {
            "title": "🕺 Videur en roue libre",
            "text": (
                "Le videur a quitté l'entrée trente secondes pour danser au milieu de la piste. "
                "La vidéo tourne déjà dans le serveur."
            ),
            "clients": random.randint(10, 25),
        },
        {
            "title": "🎧 Mauvais bouton",
            "text": (
                "Le DJ a coupé la musique par erreur en plein refrain. "
                "Toute la salle a continué le morceau a cappella."
            ),
            "clients": random.randint(5, 18),
        },
        {
            "title": "📱 Téléphone retrouvé",
            "text": (
                "Un client avait perdu son téléphone dans le carré VIP. "
                "Il l'a retrouvé dans le seau à glaçons et a quand même continué la soirée."
            ),
            "clients": random.randint(3, 10),
        },
        {
            "title": "🥂 Bouteille au plafond",
            "text": (
                "Un serveur a failli envoyer une bouteille au plafond en ouvrant le carré. "
                "Personne n'a compris, tout le monde a applaudi."
            ),
            "clients": random.randint(4, 14),
        },
        {
            "title": "🪩 Roi de la piste",
            "text": (
                "Un inconnu a lancé une battle de danse au milieu de la piste. "
                "Même la sécurité s'est arrêtée pour regarder."
            ),
            "clients": random.randint(12, 30),
        },
        {
            "title": "👠 Talon perdu",
            "text": (
                "Une cliente a perdu un talon en dansant, l'a ramassé et a continué comme si de rien n'était."
            ),
            "clients": random.randint(3, 12),
        },
        {
            "title": "🍟 After improbable",
            "text": (
                "À la fermeture, la moitié du carré VIP s'est retrouvée à manger des frites devant la boîte."
            ),
            "clients": random.randint(6, 16),
        },
    ]

    event = random.choice(
        events
    ).copy()

    bonus = int(
        event.get(
            "clients",
            0
        )
    )

    if bonus:
        club["client_bonus_next"] = int(
            club.get(
                "client_bonus_next",
                0
            )
        ) + bonus

        event["text"] += (
            f" **+{bonus} clients** sur le prochain service."
        )

    club["last_fun_event"] = event

    return event


def process_ticks(club):
    """
    Revenus toutes les 3 minutes.
    Le temps continue de compter même si le joueur est hors-ligne.
    Au prochain accès, tous les services écoulés sont calculés rétroactivement.
    Le système survit donc aux déconnexions et redémarrages.
    """
    now = time.time()

    last_tick = float(
        club.get(
            "last_tick",
            now
        )
    )

    elapsed = max(
        0,
        now - last_tick
    )

    intervals = int(
        elapsed // TICK_SECONDS
    )

    if intervals <= 0:
        return club


    for _ in range(
        intervals
    ):
        level = int(
            club.get(
                "level",
                0
            )
        )

        club["service_count"] = int(
            club.get(
                "service_count",
                0
            )
        ) + 1

        manager_effect = manager_service_effects(
            club
        )

        mult = income_multiplier(
            level
        )

        # BAR : 700 à 3 500 € toutes les 3 minutes.
        bar_base = random.randint(
            BAR_MIN,
            BAR_MAX
        )

        bar_income = int(
            bar_base
            * mult
            * (
                1.0
                + equipment_bonus(
                    club,
                    "bar_bonus"
                )
            )
            * float(
                club.get(
                    "bar_mult_next",
                    1.0
                )
            )
        )

        club["bar_mult_next"] = 1.0

        # CLIENTS : mécanique nécessaire pour que le prix d'entrée serve.
        # 8 à 22 clients réguliers toutes les 3 minutes.
        min_clients, max_clients = client_range_for_level(
            level
        )

        clients = random.randint(
            min_clients,
            max_clients
        )

        clients += int(
            manager_effect.get(
                "clients",
                0
            )
        )

        clients += int(
            club.get(
                "client_bonus_next",
                0
            )
        )

        clients -= int(
            club.get(
                "client_penalty_next",
                0
            )
        )

        entry_price = max(
            0.0,
            float(
                club.get(
                    "entry_price",
                    DEFAULT_ENTRY_PRICE
                )
            )
        )

        # Le prix d'entrée influence légèrement la fréquentation.
        price_client_mult = entry_price_client_multiplier(
            level,
            entry_price
        )

        clients = int(
            round(
                clients
                * price_client_mult
            )
        )

        clients = max(
            0,
            clients
        )

        club["client_bonus_next"] = 0
        club["client_penalty_next"] = 0

        entry_price = max(
            0.0,
            float(
                club.get(
                    "entry_price",
                    DEFAULT_ENTRY_PRICE
                )
            )
        )

        entry_mult = (
            mult
            * float(
                club.get(
                    "entry_mult_next",
                    1.0
                )
            )
        )

        club["entry_mult_next"] = 1.0

        coca_cherry_active = bool(
            club.get(
                "coca_cherry_pending",
                False
            )
        )

        showcase_combo_vip_bonus = 0
        showcase_active_this_service = False

        # Un showcase s'applique automatiquement au prochain service.
        if club.get(
            "showcase_pending"
        ):
            showcase_active_this_service = True
            artist = club.get(
                "showcase_artist"
            ) or "Artiste"

            artist_bonus = float(
                club.get(
                    "showcase_bonus",
                    0.0
                )
            )

            # Phrase aléatoire + bonus/malus de clients propre au showcase.
            showcase_event = generate_showcase_event(
                artist
            )

            showcase_clients = int(
                showcase_event.get(
                    "clients",
                    0
                )
            )

            # Tous les showcases rapportent désormais x2 clients.
            showcase_clients *= 2

            showcase_text = showcase_event.get(
                "text",
                ""
            )

            # ÉVÉNEMENT SPÉCIAL BORO 700 + SAISAI.
            if showcase_event.get(
                "boro_saisai_combo",
                False
            ):
                showcase_clients *= 2
                entry_mult *= 1.20
                bar_income = int(
                    bar_income
                    * 1.15
                )
                showcase_combo_vip_bonus += 1

                showcase_text += (
                    " 🔥 Double showcase : clients x2, entrées boostées, "
                    "bar en feu et un VIP supplémentaire."
                )

            # COMBO SECRET : Coca Cherry + Lagui sur le même service.
            if (
                artist == "Lagui"
                and coca_cherry_active
            ):
                showcase_clients *= 2
                entry_mult *= 1.25
                bar_income = int(
                    bar_income
                    * 1.20
                )
                showcase_combo_vip_bonus = 2

                showcase_text += (
                    " 🔥 Coca Cherry rejoint Lagui : la salle explose, "
                    "le bonus de clients est doublé, le bar et les entrées sont boostés."
                )

            clients += showcase_clients
            clients = max(
                0,
                clients
            )

            club["last_showcase_event"] = {
                "artist": artist,
                "text": showcase_text,
                "clients": showcase_clients,
                "time": time.time(),
            }

            history = club.setdefault(
                "artist_last_service",
                {}
            )

            history[artist] = int(
                club.get(
                    "service_count",
                    0
                )
            )

            # Bonus artiste + bonus de standing.
            entry_mult *= (
                1.0
                + artist_bonus
            )

            entry_mult *= showcase_multiplier(
                level
            )

            club["showcase_pending"] = False
            club["showcase_bonus"] = 0.0

        entry_income = int(
            clients
            * entry_price
            * entry_mult
            * (
                1.0
                + equipment_bonus(
                    club,
                    "entry_bonus"
                )
            )
        )

        # Coca Cherry ne reste que pour ce service.
        club["coca_cherry_pending"] = False

        # VIP
        vips = vip_count()

        vips += int(
            manager_effect.get(
                "vip_bonus",
                0
            )
        )

        vips += showcase_combo_vip_bonus

        vip_income = int(
            vips
            * VIP_BASE_SPEND
            * mult
            * (
                1.0
                + equipment_bonus(
                    club,
                    "vip_bonus"
                )
            )
            * float(
                club.get(
                    "vip_mult_next",
                    1.0
                )
            )
        )

        club["vip_mult_next"] = 1.0

        total = (
            bar_income
            + entry_income
            + vip_income
        )

        # Tous les services avec showcase rapportent x2 d'argent.
        if showcase_active_this_service:
            total *= 2

            # On double aussi les statistiques détaillées pour rester cohérent.
            bar_income *= 2
            entry_income *= 2
            vip_income *= 2

        club["cash"] = int(
            club.get(
                "cash",
                0
            )
        ) + total

        club["total_bar"] = int(
            club.get(
                "total_bar",
                0
            )
        ) + bar_income

        club["total_entry"] = int(
            club.get(
                "total_entry",
                0
            )
        ) + entry_income

        club["total_vip"] = int(
            club.get(
                "total_vip",
                0
            )
        ) + vip_income

        club["total_vip_clients"] = int(
            club.get(
                "total_vip_clients",
                0
            )
        ) + vips

        club["total_clients"] = int(
            club.get(
                "total_clients",
                0
            )
        ) + clients

        club["last_clients"] = clients
        club["last_vips"] = vips
        club["last_income"] = total

        # Petit événement drôle : 70 % de chance à chaque service.
        process_fun_event(
            club
        )

    club["last_tick"] = (
        last_tick
        + intervals
        * TICK_SECONDS
    )

    return club


async def apply_owner_bonus_once(user_id):
    """
    Donne 1 000 000 000 € une seule fois au compte propriétaire.
    Le marqueur est sauvegardé dans nightclub_data.json pour éviter
    que le bonus soit redonné à chaque redémarrage.
    """
    if int(user_id) != OWNER_BONUS_USER_ID:
        return

    async with data_lock:
        data = load_data()

        key = str(
            user_id
        )

        club = data.get(
            key
        )

        if club is None:
            return

        if club.get(
            "owner_bonus_granted"
        ):
            return

        club["cash"] = int(
            club.get(
                "cash",
                0
            )
        ) + OWNER_BONUS_AMOUNT

        club["owner_bonus_granted"] = True

        data[key] = club

        save_data(
            data
        )

        print(
            "♣️ Bonus propriétaire ajouté : +1 000 000 000 €"
        )


async def get_club(user_id):
    async with data_lock:
        data = load_data()

        key = str(
            user_id
        )

        club = data.get(
            key
        )

        if club is None:
            return None

        process_ticks(
            club
        )

        process_random_event(
            club
        )

        data[key] = club

        save_data(
            data
        )

        return club


async def create_club(user_id, name):
    async with data_lock:
        data = load_data()

        key = str(
            user_id
        )

        if key in data:
            return data[key], False

        club = new_club(
            name
        )

        data[key] = club

        save_data(
            data
        )

        return club, True


async def mutate_club(user_id, mutator):
    async with data_lock:
        data = load_data()

        key = str(
            user_id
        )

        club = data.get(
            key
        )

        if club is None:
            return None, "NO_CLUB"

        process_ticks(
            club
        )

        process_random_event(
            club
        )

        result = mutator(
            club
        )

        data[key] = club

        save_data(
            data
        )

        return club, result


# ============================================================
# EMBEDS SOMBRES
# ============================================================

def base_embed(title, description=None):
    return discord.Embed(
        title=title,
        description=description,
        color=DARK
    )


def dashboard_embed(club, user):
    level = int(
        club.get(
            "level",
            0
        )
    )

    embed = base_embed(
        f"♣️ {club['name']} — Direction",
        "🖤 *Olivia, secrétaire de nuit à votre service, patron.*"
    )

    embed.add_field(
        name="💶 Trésorerie",
        value=money(
            club.get(
                "cash",
                0
            )
        ),
        inline=True
    )

    current_level = int(
        club.get(
            "level",
            0
        )
    )

    current_entry_price = float(
        club.get(
            "entry_price",
            DEFAULT_ENTRY_PRICE
        )
    )

    client_mult = entry_price_client_multiplier(
        current_level,
        current_entry_price
    )

    client_percent = int(
        round(
            (
                client_mult
                - 1.0
            )
            * 100
        )
    )

    if client_percent > 0:
        price_effect = f"+{client_percent} % clients"
    elif client_percent < 0:
        price_effect = f"{client_percent} % clients"
    else:
        price_effect = "Fréquentation neutre"

    embed.add_field(
        name="🎟️ Entrée",
        value=(
            money(
                current_entry_price
            )
            + " / client\n"
            + "Max : "
            + money(
                max_entry_price(
                    current_level
                )
            )
            + "\n"
            + f"*{price_effect}*"
        ),
        inline=True
    )

    embed.add_field(
        name="♠️ Standing",
        value=level_name(
            level
        ),
        inline=True
    )

    embed.add_field(
        name="🥂 Dernier service",
        value=(
            f"Clients : **{club.get('last_clients', 0)}**\n"
            f"VIP : **{club.get('last_vips', 0)}**\n"
            f"Revenu : **{money(club.get('last_income', 0))}**"
        ),
        inline=False
    )

    # Minuteur dynamique Discord jusqu'au prochain service.
    next_service_ts = int(
        float(
            club.get(
                "last_tick",
                time.time()
            )
        )
        + TICK_SECONDS
    )

    embed.add_field(
        name="⏳ Prochain service",
        value=(
            f"<t:{next_service_ts}:R>\n"
            f"*Service automatique toutes les {TICK_SECONDS // 60} minutes.*"
        ),
        inline=False
    )

    showcase = club.get(
        "showcase_artist"
    )

    if club.get(
        "showcase_pending"
    ) and showcase:
        show_text = (
            f"🎤 **{showcase}** — actif sur le prochain service"
        )
    else:
        show_text = (
            "🥀 Aucun showcase en attente."
        )

    embed.add_field(
        name="🎤 Showcase",
        value=show_text,
        inline=False
    )

    last_showcase = club.get(
        "last_showcase_event"
    )

    if last_showcase:
        showcase_delta = int(
            last_showcase.get(
                "clients",
                0
            )
        )

        delta_text = (
            f"+{showcase_delta} clients"
            if showcase_delta >= 0
            else f"{showcase_delta} clients"
        )

        embed.add_field(
            name=(
                "🔥 Dernier showcase — "
                + str(
                    last_showcase.get(
                        "artist",
                        "Artiste"
                    )
                )
            ),
            value=(
                f"*{last_showcase.get('text', '')}*\n"
                f"👥 **{delta_text}**"
            ),
            inline=False
        )

    embed.add_field(
        name="🔊 Équipements",
        value=f"**{len(club.get('equipment', []))}/{len(EQUIPMENT_UPGRADES)}** installés",
        inline=True
    )

    current_manager = get_manager(
        club
    )

    if current_manager:
        manager_text = (
            f"**{current_manager['name']}** — Niv. {current_manager['level']}\n"
            f"{money(current_manager['salary'])} / 3 min"
        )
    else:
        manager_text = "Aucun"

    embed.add_field(
        name="♣️ Manager",
        value=manager_text,
        inline=True
    )

    last_fun_event = club.get(
        "last_fun_event"
    )

    if last_fun_event:
        embed.add_field(
            name=last_fun_event.get(
                "title",
                "🪩 Petite histoire de la nuit"
            ),
            value=last_fun_event.get(
                "text",
                ""
            ),
            inline=False
        )

    last_event = club.get(
        "last_event"
    )

    if last_event:
        embed.add_field(
            name=last_event.get(
                "title",
                "♣️ Événement"
            ),
            value=last_event.get(
                "text",
                "Aucun détail."
            ),
            inline=False
        )

    embed.set_footer(
        text="♣️ Les clients arrivent et les revenus sont calculés toutes les 3 minutes."
    )

    return embed


def finances_embed(club):
    embed = base_embed(
        "♣️ Registre financier",
        f"**{club['name']}**"
    )

    embed.add_field(
        name="🍸 Bar",
        value=money(
            club.get(
                "total_bar",
                0
            )
        ),
        inline=True
    )

    embed.add_field(
        name="🎟️ Entrées",
        value=money(
            club.get(
                "total_entry",
                0
            )
        ),
        inline=True
    )

    embed.add_field(
        name="👑 VIP",
        value=money(
            club.get(
                "total_vip",
                0
            )
        ),
        inline=True
    )

    embed.add_field(
        name="🕴️ Clients reçus",
        value=str(
            club.get(
                "total_clients",
                0
            )
        ),
        inline=True
    )

    embed.add_field(
        name="♛ VIP reçus",
        value=str(
            club.get(
                "total_vip_clients",
                0
            )
        ),
        inline=True
    )

    embed.add_field(
        name="🎤 Showcases",
        value=str(
            club.get(
                "showcases_done",
                0
            )
        ),
        inline=True
    )

    return embed


def upgrades_embed(club):
    level = int(
        club.get(
            "level",
            0
        )
    )

    embed = base_embed(
        "♣️ Établissement & standing",
        "🥀 *Dossier d'amélioration de votre établissement.*"
    )

    levels = [
        (
            1,
            "Babinski",
            UPGRADE_COSTS[1],
            "+25 %",
            "31,25 €"
        ),
        (
            2,
            "L'Ikona",
            UPGRADE_COSTS[2],
            "+50 %",
            "37,50 €"
        ),
        (
            3,
            "Balajo",
            UPGRADE_COSTS[3],
            "+65 %",
            "43,75 €"
        ),
        (
            4,
            "Le Bikini",
            UPGRADE_COSTS[4],
            "+80 %",
            "50 €"
        ),
        (
            5,
            "Miami Club",
            UPGRADE_COSTS[5],
            "+100 %",
            "57,50 €"
        ),
        (
            6,
            "Le Olivia",
            UPGRADE_COSTS[6],
            "+125 %",
            "65 €"
        ),
    ]

    if level >= 6:
        embed.add_field(
            name="♛ Niveau maximum",
            value=(
                "**Le Olivia**\n"
                "Votre établissement a atteint le standing maximum.\n"
                "Bonus général : **+125 %**"
            ),
            inline=False
        )

        return embed

    # Niveau actuel
    if level > 0:
        embed.add_field(
            name="♠️ Niveau actuel",
            value=(
                f"**{level_name(level)}**\n"
                f"Bonus général : **+{int((income_multiplier(level) - 1) * 100)} %**\n"
                f"Entrée max : **{money(max_entry_price(level))}**"
            ),
            inline=False
        )

    # Affiche la prochaine amélioration + les suivantes
    for level_id, name, cost, bonus, max_price in levels:
        if level_id <= level:
            continue

        embed.add_field(
            name=f"{level_id} — {name}",
            value=(
                f"Prix : **{money(cost)}**\n"
                f"Revenus : **{bonus}** sur bar, entrées et VIP\n"
                f"Entrée max : **{max_price}**"
            ),
            inline=False
        )

    embed.set_footer(
        text="♣️ Chaque amélioration augmente aussi légèrement l'efficacité des showcases."
    )

    return embed



def equipment_embed(club):
    embed = base_embed(
        "♣️ Personnel & équipements",
        "🖤 *Améliorations secondaires de votre établissement.*"
    )

    owned = set(
        club.get(
            "equipment",
            []
        )
    )

    if owned:
        owned_lines = []

        for item_id in owned:
            item = EQUIPMENT_UPGRADES.get(
                item_id
            )

            if not item:
                continue

            owned_lines.append(
                f"{item['emoji']} **{item['name']}** — {item['description']}"
            )

        if owned_lines:
            embed.add_field(
                name="♠️ Déjà installé",
                value="\n".join(
                    owned_lines
                )[:1024],
                inline=False
            )

    available = []

    for item_id, item in EQUIPMENT_UPGRADES.items():
        if item_id in owned:
            continue

        available.append(
            f"{item['emoji']} **{item['name']}** — {money(item['cost'])}\n"
            f"└ {item['description']}"
        )

    if available:
        embed.add_field(
            name="🥀 Disponible",
            value="\n".join(
                available
            )[:1024],
            inline=False
        )
    else:
        embed.add_field(
            name="♛ Équipement complet",
            value="Toutes les améliorations secondaires ont été achetées.",
            inline=False
        )

    embed.set_footer(
        text="♣️ Ces bonus se cumulent avec le standing de votre boîte."
    )

    return embed



def activities_embed(club):
    embed = base_embed(
        "♣️ Activités de nuit",
        (
            "🖤 *Pendant que la clientèle arrive, vous pouvez prendre quelques décisions.*\n\n"
            "Ces activités utilisent uniquement l'argent virtuel de votre boîte."
        )
    )

    embed.add_field(
        name="🃏 Blackjack",
        value=(
            "Mises disponibles de **1 000 € à 1 000 000 €**.\n"
            "Une victoire paie votre mise en bénéfice, une défaite la fait perdre."
        ),
        inline=False
    )

    embed.add_field(
        name="🥃 Boire un verre",
        value=(
            "Prix : **250 €**.\n"
            "50 % de chance de finir bourré : **-8 clients** au prochain service.\n"
            "Sinon : bonne ambiance, **+4 clients**."
        ),
        inline=False
    )

    embed.add_field(
        name="📢 Promo express",
        value=(
            "Prix : **2 500 €**.\n"
            "Ajoute **+12 clients** au prochain service."
        ),
        inline=False
    )

    embed.add_field(
        name="📸 Inviter un influenceur",
        value=(
            "Prix : **5 000 €**.\n"
            "60 % de réussite : **+30 clients**.\n"
            "Sinon la campagne ne prend pas."
        ),
        inline=False
    )

    embed.add_field(
        name="🍒 Coca Cherry",
        value=(
            "Prix : **7 500 €**.\n"
            "Vous ramenez **Coca Cherry** dans la boîte : elle met l'ambiance avec un show twerk.\n"
            "Effet : **+40 clients** au prochain service.\n"
            "🔥 **Combo : Coca Cherry + showcase Lagui au même service = bonus x2 + revenus boostés.**"
        ),
        inline=False
    )

    embed.set_footer(
        text="♣️ Jouez avec mesure : la trésorerie sert aussi aux améliorations."
    )

    return embed



def managers_embed(club):
    embed = base_embed(
        "♣️ Managers & manageuses",
        (
            "🖤 *Votre manager travaille automatiquement toutes les 3 minutes.*\n"
            "Il gère la publicité, tente d'attirer des VIP et peut organiser des showcases."
        )
    )

    current = get_manager(
        club
    )

    if current:
        embed.add_field(
            name="♠️ Manager actuel",
            value=(
                f"**{current['name']}** — Niveau {current['level']}\n"
                f"Salaire : **{money(current['salary'])} / 3 min**\n"
                f"{current['description']}"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="♠️ Manager actuel",
            value="Aucun manager embauché.",
            inline=False
        )

    for manager_id, manager in MANAGERS.items():
        embed.add_field(
            name=f"♣️ {manager['name']} — Niveau {manager['level']}",
            value=(
                f"Salaire : **{money(manager['salary'])} / 3 min**\n"
                f"{manager['description']}"
            ),
            inline=False
        )

    embed.set_footer(
        text="♣️ Si la trésorerie ne peut pas payer le salaire, le manager ne produit aucun bonus sur ce service."
    )

    return embed



def shop_home_embed(club):
    embed = base_embed(
        "♣️ Boutique — Olivia BTQ",
        (
            "🖤 *Dépensez l'argent de votre boîte pour votre collection.*\n\n"
            f"Trésorerie disponible : **{money(club.get('cash', 0))}**"
        )
    )

    embed.add_field(
        name="🚘 Concessionnaire",
        value="Achetez ou revendez vos voitures.",
        inline=False
    )

    embed.add_field(
        name="⌚ Boutique de montres",
        value="Achetez ou revendez vos montres.",
        inline=False
    )

    embed.add_field(
        name="₿ Bitcoin",
        value=(
            f"Prix d'achat : **{money(BITCOIN_PRICE)} / BTC**\n"
            f"Prix de revente : **{money(int(BITCOIN_PRICE * RESALE_RATE))} / BTC**"
        ),
        inline=False
    )

    embed.set_footer(
        text="♣️ Revente = 75 % du prix d'achat."
    )

    return embed


def category_embed(title, items, owned_ids, emoji):
    embed = base_embed(
        f"{emoji} {title}",
        "🖤 Achetez ou revendez vos objets."
    )

    for item_id, item in items.items():
        owned = owned_ids.count(
            item_id
        )

        embed.add_field(
            name=f"{emoji} {item['name']}",
            value=(
                f"Achat : **{money(item['price'])}**\n"
                f"Revente : **{money(int(item['price'] * RESALE_RATE))}**\n"
                f"Possédé : **{owned}**"
            ),
            inline=False
        )

    return embed


def bitcoin_embed(club):
    btc = int(
        club.get(
            "bitcoin",
            0
        )
    )

    return base_embed(
        "₿ Bitcoin",
        (
            f"Possédé : **{btc} BTC**\n"
            f"Achat : **{money(BITCOIN_PRICE)} / BTC**\n"
            f"Revente : **{money(int(BITCOIN_PRICE * RESALE_RATE))} / BTC**\n\n"
            f"Valeur boutique : **{money(btc * BITCOIN_PRICE)}**"
        )
    )


# ============================================================
# MODALS
# ============================================================

class CreateClubModal(
    discord.ui.Modal,
    title="♣️ Création de votre boîte"
):
    club_name = discord.ui.TextInput(
        label="Nom de la boîte de nuit",
        placeholder="Ex : Le Noir, Olivia Club, 700...",
        min_length=2,
        max_length=40
    )

    async def on_submit(
        self,
        interaction
    ):
        club, created = await create_club(
            interaction.user.id,
            str(
                self.club_name.value
            )
        )

        if created:
            await apply_owner_bonus_once(
                interaction.user.id
            )

            club = await get_club(
                interaction.user.id
            )

        if not created:
            await interaction.response.send_message(
                "♣️ Vous possédez déjà un établissement, patron.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                interaction.user.id
            ),
            ephemeral=True
        )


class EntryPriceModal(
    discord.ui.Modal,
    title="🎟️ Prix de l'entrée"
):
    price = discord.ui.TextInput(
        label="Prix par client (€)",
        placeholder="Ex : 25 ou 31,25",
        min_length=1,
        max_length=7
    )

    def __init__(
        self,
        owner_id
    ):
        super().__init__()

        self.owner_id = owner_id

    async def on_submit(
        self,
        interaction
    ):
        raw = (
            str(
                self.price.value
            )
            .strip()
            .replace(
                ",",
                "."
            )
        )

        try:
            price = float(
                raw
            )
        except ValueError:
            await interaction.response.send_message(
                "♣️ Entrez un prix valide, patron.",
                ephemeral=True
            )
            return

        current_club = await get_club(
            self.owner_id
        )

        if not current_club:
            await interaction.response.send_message(
                "♣️ Aucun établissement trouvé.",
                ephemeral=True
            )
            return

        level = int(
            current_club.get(
                "level",
                0
            )
        )

        maximum = max_entry_price(
            level
        )

        if price < 0 or price > maximum:
            await interaction.response.send_message(
                (
                    "♣️ Le prix maximum actuel est de **"
                    + money(maximum)
                    + "**, patron."
                ),
                ephemeral=True
            )
            return

        price = round(
            price,
            2
        )

        def change(
            club
        ):
            club["entry_price"] = price
            return "OK"

        club, _ = await mutate_club(
            self.owner_id,
            change
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )



class RenameClubModal(
    discord.ui.Modal,
    title="♣️ Renommer votre boîte"
):
    name = discord.ui.TextInput(
        label="Nouveau nom",
        placeholder="Ex : Le Palace Noir",
        min_length=2,
        max_length=40
    )

    def __init__(
        self,
        owner_id
    ):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(
        self,
        interaction
    ):
        new_name = str(
            self.name.value
        ).strip()

        def rename(
            club
        ):
            club["name"] = new_name
            return "OK"

        club, _ = await mutate_club(
            self.owner_id,
            rename
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


class DeleteClubView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=120
        )
        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Confirmer la suppression",
        emoji="🗑️",
        style=discord.ButtonStyle.danger
    )
    async def confirm_delete(
        self,
        interaction,
        button
    ):
        async with data_lock:
            data = load_data()
            key = str(
                self.owner_id
            )

            removed = data.pop(
                key,
                None
            )

            save_data(
                data
            )

        if removed is None:
            await interaction.response.edit_message(
                embed=base_embed(
                    "♣️ Suppression",
                    "Aucun établissement n'a été trouvé."
                ),
                view=None
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "🗑️ Établissement supprimé",
                (
                    "Votre boîte de nuit a été définitivement supprimée, patron.\\n\\n"
                    "Écrivez **Olivia BDN** pour recommencer."
                )
            ),
            view=None
        )

    @discord.ui.button(
        label="Annuler",
        emoji="♣️",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )



def info_embed():
    embed = base_embed(
        "♣️ Olivia BDN — Guide complet",
        (
            "🖤 *Bienvenue dans le mode gestion de boîte de nuit.*\n\n"
            "Chaque joueur possède sa propre boîte, sa trésorerie et sa progression."
        )
    )

    embed.add_field(
        name="♣️ Commandes principales",
        value=(
            "**Olivia BDN** → ouvre votre boîte\n"
            "**Olivia CLS** → classement des boîtes du serveur\n"
            "**Olivia BTQ** → ouvre la boutique\n"
            "**Olivia FLEX** → affiche voitures, montres et Bitcoin\n"
            "**Olivia TRADE @joueur** → proposer argent, BTC, voiture ou montre\n"
            "**Olivia BRAQUE @joueur** → tenter de voler 25 % de sa trésorerie\n"
            "**Olivia BOUTEILLE @joueur** → envoyer un pack à une autre boîte\n"
            "└ Standing + équipements augmentent attaque et défense\n"
            "BDN / CLS / BTQ / BRAQUE sont réservés au salon Nightclub. FLEX et TRADE fonctionnent partout."
        ),
        inline=False
    )

    embed.add_field(
        name="💶 Revenus",
        value=(
            "Les clients arrivent toutes les **3 minutes**.\n"
            "Vous gagnez de l'argent grâce au **bar**, aux **entrées** et aux **VIP**.\n"
            "Le nombre de clients augmente avec le niveau de votre boîte.\n"
            "🌙 **La boîte continue de générer ses services même quand vous êtes hors-ligne.**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎟️ Prix d'entrée",
        value=(
            "Vous choisissez votre prix d'entrée dans la limite autorisée par votre niveau.\n"
            "Plus votre boîte monte en gamme, plus le prix maximum augmente."
        ),
        inline=False
    )

    embed.add_field(
        name="🎤 Showcases",
        value=(
            "Vous pouvez programmer un artiste.\n"
            "Chaque artiste apporte un bonus différent selon sa notoriété dans le jeu.\n"
            "Le bonus est appliqué **automatiquement au prochain service**."
        ),
        inline=False
    )

    embed.add_field(
        name="♠️ Niveaux de boîte",
        value=(
            "Club indépendant → Babinski → L'Ikona → Balajo → "
            "Le Bikini → Miami Club → Le Olivia.\n"
            "Chaque niveau augmente la fréquentation et les revenus."
        ),
        inline=False
    )

    embed.add_field(
        name="♣️ Managers",
        value=(
            "**Victoria**, **Josas** et **Olivia** peuvent gérer automatiquement la publicité, "
            "les VIP et certains showcases.\n"
            "Ils sont payés à chaque service de 3 minutes et peuvent être licenciés à tout moment."
        ),
        inline=False
    )

    embed.add_field(
        name="🔊 Personnel & équipements",
        value=(
            "DJ, danseuses, fumée, lasers, sono, sécurité, carré VIP, "
            "barmans et décoration donnent des bonus supplémentaires."
        ),
        inline=False
    )

    embed.add_field(
        name="🃏 Activités",
        value=(
            "Blackjack virtuel, boire un verre, promo express et influenceur.\n"
            "Certaines activités peuvent vous faire gagner ou perdre de l'argent "
            "ou modifier le prochain service."
        ),
        inline=False
    )

    embed.add_field(
        name="🚨 Événements",
        value=(
            "Toutes les **10 minutes**, il y a **25 % de chance** qu'un événement arrive : "
            "contrôle de police, bagarre, route bloquée, coupure, influenceur, table VIP, etc."
        ),
        inline=False
    )

    embed.add_field(
        name="💸 Transferts",
        value=(
            "Vous pouvez envoyer de l'argent de votre trésorerie à un autre joueur "
            "qui possède une boîte de nuit sur le serveur."
        ),
        inline=False
    )

    embed.set_footer(
        text="♣️ Olivia — Secrétariat de nuit"
    )

    return embed



class TransferMoneyModal(
    discord.ui.Modal,
    title="💸 Envoyer de l'argent"
):
    target = discord.ui.TextInput(
        label="Joueur (@mention ou ID)",
        placeholder="@Pseudo ou 123456789...",
        min_length=2,
        max_length=60
    )

    amount = discord.ui.TextInput(
        label="Montant (€)",
        placeholder="Ex : 5000",
        min_length=1,
        max_length=12
    )

    def __init__(
        self,
        owner_id
    ):
        super().__init__()
        self.owner_id = owner_id

    async def on_submit(
        self,
        interaction
    ):
        raw_target = str(
            self.target.value
        ).strip()

        match = re.search(
            r"(\d{15,22})",
            raw_target
        )

        if not match:
            await interaction.response.send_message(
                "♣️ Je n'ai pas reconnu ce joueur, patron.",
                ephemeral=True
            )
            return

        target_id = int(
            match.group(1)
        )

        if target_id == self.owner_id:
            await interaction.response.send_message(
                "♣️ Vous ne pouvez pas vous envoyer de l'argent à vous-même, patron.",
                ephemeral=True
            )
            return

        member = interaction.guild.get_member(
            target_id
        )

        if member is None:
            try:
                member = await interaction.guild.fetch_member(
                    target_id
                )
            except Exception:
                member = None

        if member is None or member.bot:
            await interaction.response.send_message(
                "♣️ Ce joueur n'est pas disponible sur ce serveur.",
                ephemeral=True
            )
            return

        raw_amount = re.sub(
            r"[^0-9]",
            "",
            str(
                self.amount.value
            )
        )

        if not raw_amount:
            await interaction.response.send_message(
                "♣️ Entrez un montant valide, patron.",
                ephemeral=True
            )
            return

        amount = int(
            raw_amount
        )

        if amount <= 0:
            await interaction.response.send_message(
                "♣️ Le montant doit être supérieur à 0 €.",
                ephemeral=True
            )
            return

        async with data_lock:
            data = load_data()

            sender_key = str(
                self.owner_id
            )

            target_key = str(
                target_id
            )

            sender = data.get(
                sender_key
            )

            target_club = data.get(
                target_key
            )

            if sender is None:
                await interaction.response.send_message(
                    "♣️ Votre boîte de nuit est introuvable.",
                    ephemeral=True
                )
                return

            if target_club is None:
                await interaction.response.send_message(
                    "♣️ Ce joueur doit d'abord créer sa boîte avec **Olivia BDN**.",
                    ephemeral=True
                )
                return

            process_ticks(
                sender
            )
            process_random_event(
                sender
            )

            process_ticks(
                target_club
            )
            process_random_event(
                target_club
            )

            sender_cash = int(
                sender.get(
                    "cash",
                    0
                )
            )

            if sender_cash < amount:
                await interaction.response.send_message(
                    "♣️ Trésorerie insuffisante pour ce transfert, patron.",
                    ephemeral=True
                )
                return

            sender["cash"] = sender_cash - amount

            target_club["cash"] = int(
                target_club.get(
                    "cash",
                    0
                )
            ) + amount

            data[sender_key] = sender
            data[target_key] = target_club

            save_data(
                data
            )

        await interaction.response.edit_message(
            embed=base_embed(
                "💸 Transfert effectué",
                (
                    f"♣️ **{money(amount)}** ont été envoyés à {member.mention}.\n\n"
                    f"Votre nouvelle trésorerie : **{money(sender['cash'])}**"
                )
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


# ============================================================
# MENUS
# ============================================================

class PrivateMenuLauncherView(
    discord.ui.View
):
    """
    Les messages texte Discord ne peuvent pas être directement 'ephemeral'.
    Donc Olivia affiche seulement un petit bouton temporaire.
    Quand le joueur clique, le VRAI menu est visible uniquement par lui.
    """
    def __init__(
        self,
        user_id,
        mode
    ):
        super().__init__(
            timeout=30
        )

        self.user_id = user_id
        self.mode = mode

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "♣️ Ce menu ne vous appartient pas, patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Ouvrir mon menu privé",
        emoji="♣️",
        style=discord.ButtonStyle.secondary
    )
    async def open_private_menu(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.user_id
        )

        if self.mode == "btq":
            if club is None:
                await interaction.response.send_message(
                    "♣️ Vous devez d'abord créer votre boîte avec **Olivia BDN**.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(
                embed=shop_home_embed(
                    club
                ),
                view=ShopCategoryView(
                    self.user_id
                ),
                ephemeral=True
            )

            try:
                await interaction.message.delete()
            except Exception:
                pass

            return

        # Mode BDN
        if club:
            await interaction.response.send_message(
                embed=dashboard_embed(
                    club,
                    interaction.user
                ),
                view=NightclubMenuView(
                    self.user_id
                ),
                ephemeral=True
            )

            try:
                await interaction.message.delete()
            except Exception:
                pass

            return

        embed = base_embed(
            "♣️ OLIVIA — DIRECTION DE NUIT",
            (
                "🖤 Bonsoir, patron.\n\n"
                "Aucun établissement n'est encore enregistré à votre nom.\n"
                "Je peux ouvrir votre dossier et créer votre boîte de nuit immédiatement."
            )
        )

        embed.add_field(
            name="🥀 Gestion",
            value=(
                "Bar • Entrées • Clientèle VIP • Showcases • Améliorations"
            ),
            inline=False
        )

        embed.set_footer(
            text="♣️ Olivia — Secrétariat de nuit"
        )

        await interaction.response.send_message(
            embed=embed,
            view=StartNightclubView(
                self.user_id
            ),
            ephemeral=True
        )

        try:
            await interaction.message.delete()
        except Exception:
            pass


class StartNightclubView(
    discord.ui.View
):
    def __init__(
        self,
        user_id
    ):
        super().__init__(
            timeout=900
        )

        self.user_id = user_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Créer ma boîte",
        emoji="♣️",
        style=discord.ButtonStyle.secondary
    )
    async def create_button(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.user_id
        )

        if club:
            await interaction.response.edit_message(
                embed=dashboard_embed(
                    club,
                    interaction.user
                ),
                view=NightclubMenuView(
                    self.user_id
                )
            )
            return

        await interaction.response.send_modal(
            CreateClubModal()
        )

    @discord.ui.button(
        label="Ouvrir mon établissement",
        emoji="🖤",
        style=discord.ButtonStyle.secondary
    )
    async def open_button(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.user_id
        )

        if not club:
            await interaction.response.send_modal(
                CreateClubModal()
            )
            return

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.user_id
            )
        )


class NightclubMenuView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce tableau de direction appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def dashboard(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Finances",
        emoji="💶",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def finances(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=finances_embed(
                club
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Prix entrée",
        emoji="🎟️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def entry_price(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            EntryPriceModal(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Showcase",
        emoji="🎤",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def showcase(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        if not club:
            await interaction.response.send_message(
                "♣️ Aucun établissement trouvé.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "🎤 Bureau des showcases",
                (
                    "🖤 Sélectionnez l'artiste que vous souhaitez programmer.\n\n"
                    f"Prix : **{money(SHOWCASE_COST)}**\n"
                    "Effet : **+25 % minimum sur les entrées du prochain service de 3 min**.\n""Le bonus augmente avec le standing de la boîte."
                )
            ),
            view=ShowcaseView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Améliorations",
        emoji="♠️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def upgrades(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=upgrades_embed(
                club
            ),
            view=UpgradeView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Activités",
        emoji="🃏",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def activities(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=activities_embed(
                club
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Équipements",
        emoji="🔊",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def equipment(
        self,
        interaction,
        button
    ):
        # Discord exige une réponse en moins de 3 secondes.
        # On accuse réception immédiatement, puis on charge le menu.
        await interaction.response.defer()

        try:
            club = await get_club(
                self.owner_id
            )

            if club is None:
                await interaction.edit_original_response(
                    embed=base_embed(
                        "♣️ Équipements",
                        "Aucune boîte de nuit trouvée."
                    ),
                    view=NightclubMenuView(
                        self.owner_id
                    )
                )
                return

            await interaction.edit_original_response(
                embed=equipment_embed(
                    club
                ),
                view=EquipmentView(
                    self.owner_id,
                    club
                )
            )

        except Exception as e:
            print(
                "❌ Menu équipements :",
                repr(e)
            )

            await interaction.edit_original_response(
                embed=base_embed(
                    "♣️ Équipements",
                    "Une erreur est survenue pendant l'ouverture du menu."
                ),
                view=NightclubMenuView(
                    self.owner_id
                )
            )

    @discord.ui.button(
        label="Managers",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def managers(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=managers_embed(
                club
            ),
            view=ManagerView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Infos",
        emoji="ℹ️",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def info(
        self,
        interaction,
        button
    ):
        await interaction.response.edit_message(
            embed=info_embed(),
            view=NightclubMenuView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Envoyer argent",
        emoji="💸",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def transfer_money(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            TransferMoneyModal(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Renommer",
        emoji="✏️",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def rename_club(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            RenameClubModal(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Supprimer",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        row=3
    )
    async def delete_club(
        self,
        interaction,
        button
    ):
        await interaction.response.edit_message(
            embed=base_embed(
                "🗑️ Supprimer votre boîte",
                (
                    "Cette action supprime **définitivement** votre établissement, "
                    "son argent et ses améliorations."
                )
            ),
            view=DeleteClubView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Actualiser",
        emoji="🥀",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def refresh(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


class ArtistSelect(
    discord.ui.Select
):
    def __init__(
        self,
        owner_id
    ):
        self.owner_id = owner_id

        options = [
            discord.SelectOption(
                label=artist,
                value=artist,
                emoji="🎤",
                description=(
                    (
                        f"+{int(ARTIST_SHOWCASE_BONUS.get(artist, 0.20) * 100)} % bonus"
                        f" • {money(showcase_cost_for_artist(artist))}"
                    )
                    + (" • car Lagui c’est le meilleur" if artist == "Lagui" else "")
                )[:100]
            )
            for artist in ARTISTS
        ]

        super().__init__(
            placeholder="Choisir un artiste...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        artist = self.values[0]

        def book(
            club
        ):
            if club.get(
                "showcase_pending"
            ):
                return "ALREADY"

            remaining = artist_cooldown_remaining(
                club,
                artist
            )

            if remaining > 0:
                return (
                    "COOLDOWN",
                    remaining
                )

            artist_cost = showcase_cost_for_artist(
                artist
            )

            if int(
                club.get(
                    "cash",
                    0
                )
            ) < artist_cost:
                return (
                    "NO_MONEY",
                    artist_cost
                )

            club["cash"] = int(
                club.get(
                    "cash",
                    0
                )
            ) - artist_cost

            club["showcase_artist"] = artist
            club["showcase_pending"] = True
            club["showcase_bonus"] = float(
                ARTIST_SHOWCASE_BONUS.get(
                    artist,
                    0.20
                )
            )
            club["showcases_done"] = int(
                club.get(
                    "showcases_done",
                    0
                )
            ) + 1

            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            book
        )

        if isinstance(
            result,
            tuple
        ) and result[0] == "NO_MONEY":
            await interaction.response.send_message(
                f"♣️ Trésorerie insuffisante. Il faut **{money(result[1])}**, patron.",
                ephemeral=True
            )
            return

        if result == "ALREADY":
            await interaction.response.send_message(
                "♣️ Un showcase est déjà programmé pour le prochain service, patron.",
                ephemeral=True
            )
            return

        if isinstance(
            result,
            tuple
        ) and result[0] == "COOLDOWN":
            remaining = int(
                result[1]
            )

            await interaction.response.send_message(
                (
                    f"♣️ **{artist}** vient déjà de passer dans votre boîte.\n"
                    f"⏳ Attendez encore **{remaining} service"
                    + ("s" if remaining > 1 else "")
                    + "** avant de le reprendre, patron."
                ),
                ephemeral=True
            )
            return

        embed = base_embed(
            "🎤 Showcase confirmé",
            (
                f"♣️ **{artist}** est programmé dans **{club['name']}**.\n\n"
                f"💶 Frais : **{money(showcase_cost_for_artist(artist))}**\n"
                f"🎟️ Bonus artiste : **+{int(ARTIST_SHOWCASE_BONUS.get(artist, 0.20) * 100)} %**\n"
                + ("🖤 *car Lagui c’est le meilleur*\n" if artist == "Lagui" else "")
                + "🥀 Le bonus sera appliqué automatiquement au prochain service.\n"
                + "🔥 **Tous les showcases donnent x2 clients de showcase et x2 revenus sur le service.**"
            )
        )

        await interaction.response.edit_message(
            embed=embed,
            view=NightclubMenuView(
                self.owner_id
            )
        )


class ShowcaseView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

        self.add_item(
            ArtistSelect(
                owner_id
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Retour direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


def draw_card():
    # Valeurs simplifiées type blackjack.
    return random.choice(
        [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    )


def dealer_total():
    total = 0

    while total < 17:
        total += draw_card()

        # Ajustement simple d'un As 11 -> 1 si on dépasse.
        if total > 21:
            total -= 10

    return total


class BlackjackBetSelect(
    discord.ui.Select
):
    def __init__(
        self,
        owner_id
    ):
        self.owner_id = owner_id

        options = [
            discord.SelectOption(
                label="1 000 €",
                value="1000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="5 000 €",
                value="5000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="10 000 €",
                value="10000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="25 000 €",
                value="25000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="50 000 €",
                value="50000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="100 000 €",
                value="100000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="250 000 €",
                value="250000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="500 000 €",
                value="500000",
                emoji="🃏"
            ),
            discord.SelectOption(
                label="1 000 000 €",
                value="1000000",
                emoji="🃏"
            ),
        ]

        super().__init__(
            placeholder="Choisir votre mise...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        bet = int(
            self.values[0]
        )

        def play_blackjack(
            club
        ):
            cash = int(
                club.get(
                    "cash",
                    0
                )
            )

            if cash < bet:
                return {
                    "status": "NO_MONEY"
                }

            # Main joueur automatique en 2 cartes, puis tire jusque 16.
            player = draw_card() + draw_card()

            if player > 21:
                player -= 10

            while player < 16:
                player += draw_card()

                if player > 21:
                    player -= 10

            dealer = dealer_total()

            if player > 21:
                result = "LOSE"

            elif dealer > 21 or player > dealer:
                result = "WIN"

            elif player == dealer:
                result = "PUSH"

            else:
                result = "LOSE"

            if result == "WIN":
                club["cash"] = cash + bet
                club["blackjack_wins"] = int(
                    club.get(
                        "blackjack_wins",
                        0
                    )
                ) + 1

            elif result == "LOSE":
                club["cash"] = cash - bet
                club["blackjack_losses"] = int(
                    club.get(
                        "blackjack_losses",
                        0
                    )
                ) + 1

            return {
                "status": result,
                "player": player,
                "dealer": dealer,
                "bet": bet,
            }

        club, result = await mutate_club(
            self.owner_id,
            play_blackjack
        )

        if result["status"] == "NO_MONEY":
            await interaction.response.send_message(
                "♣️ Trésorerie insuffisante pour cette mise, patron.",
                ephemeral=True
            )
            return

        status = result["status"]

        if status == "WIN":
            message = (
                f"🃏 **Victoire.** Vous : {result['player']} — Banque : {result['dealer']}\n"
                f"💶 Bénéfice : **+{money(result['bet'])}**"
            )

        elif status == "PUSH":
            message = (
                f"🃏 **Égalité.** Vous : {result['player']} — Banque : {result['dealer']}\n"
                "La mise vous revient."
            )

        else:
            message = (
                f"🃏 **Défaite.** Vous : {result['player']} — Banque : {result['dealer']}\n"
                f"💶 Perte : **-{money(result['bet'])}**"
            )

        embed = base_embed(
            "🃏 Blackjack privé",
            message
        )

        await interaction.response.edit_message(
            embed=embed,
            view=ActivitiesView(
                self.owner_id
            )
        )


class BlackjackView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

        self.add_item(
            BlackjackBetSelect(
                owner_id
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Cette table appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Retour",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=activities_embed(
                club
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )


class ActivitiesView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Blackjack",
        emoji="🃏",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def blackjack(
        self,
        interaction,
        button
    ):
        await interaction.response.edit_message(
            embed=base_embed(
                "🃏 Table de blackjack",
                "Choisissez votre mise, patron."
            ),
            view=BlackjackView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Boire un verre",
        emoji="🥃",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def drink(
        self,
        interaction,
        button
    ):
        def drink_action(
            club
        ):
            cash = int(
                club.get(
                    "cash",
                    0
                )
            )

            if cash < 250:
                return "NO_MONEY"

            club["cash"] = cash - 250
            club["drinks_taken"] = int(
                club.get(
                    "drinks_taken",
                    0
                )
            ) + 1

            if random.random() < 0.50:
                club["client_penalty_next"] = int(
                    club.get(
                        "client_penalty_next",
                        0
                    )
                ) + 8

                return "DRUNK"

            club["client_bonus_next"] = int(
                club.get(
                    "client_bonus_next",
                    0
                )
            ) + 4

            return "GOOD"

        club, result = await mutate_club(
            self.owner_id,
            drink_action
        )

        if result == "NO_MONEY":
            msg = "♣️ Il vous manque 250 €, patron."

        elif result == "DRUNK":
            msg = (
                "🥃 Le verre est de trop, patron. "
                "**-8 clients** au prochain service."
            )

        else:
            msg = (
                "🥃 Bonne ambiance ce soir. "
                "**+4 clients** au prochain service."
            )

        await interaction.response.edit_message(
            embed=base_embed(
                "🥃 Bar privé",
                msg
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Promo express",
        emoji="📢",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def promo(
        self,
        interaction,
        button
    ):
        def promo_action(
            club
        ):
            cash = int(
                club.get(
                    "cash",
                    0
                )
            )

            if cash < 2500:
                return "NO_MONEY"

            club["cash"] = cash - 2500

            club["client_bonus_next"] = int(
                club.get(
                    "client_bonus_next",
                    0
                )
            ) + 12

            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            promo_action
        )

        msg = (
            "📢 Campagne lancée : **+12 clients** au prochain service."
            if result == "OK"
            else "♣️ Il faut **2 500 €** pour lancer la promotion, patron."
        )

        await interaction.response.edit_message(
            embed=base_embed(
                "📢 Promotion express",
                msg
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Influenceur",
        emoji="📸",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def influencer(
        self,
        interaction,
        button
    ):
        def influence_action(
            club
        ):
            cash = int(
                club.get(
                    "cash",
                    0
                )
            )

            if cash < 5000:
                return "NO_MONEY"

            club["cash"] = cash - 5000

            if random.random() < 0.60:
                club["client_bonus_next"] = int(
                    club.get(
                        "client_bonus_next",
                        0
                    )
                ) + 30

                return "WIN"

            return "MISS"

        club, result = await mutate_club(
            self.owner_id,
            influence_action
        )

        if result == "NO_MONEY":
            msg = "♣️ Il faut **5 000 €** pour l'inviter, patron."

        elif result == "WIN":
            msg = "📸 La publication explose : **+30 clients** au prochain service."

        else:
            msg = "🥀 La publication n'a presque rien donné. Les **5 000 €** sont dépensés."

        await interaction.response.edit_message(
            embed=base_embed(
                "📸 Influenceur",
                msg
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Coca Cherry",
        emoji="🍒",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def coca_cherry(
        self,
        interaction,
        button
    ):
        def coca_action(
            club
        ):
            cash = int(
                club.get(
                    "cash",
                    0
                )
            )

            cost = 7500

            if cash < cost:
                return "NO_MONEY"

            club["cash"] = cash - cost

            club["client_bonus_next"] = int(
                club.get(
                    "client_bonus_next",
                    0
                )
            ) + 40

            club["coca_cherry_pending"] = True

            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            coca_action
        )

        if result == "NO_MONEY":
            msg = (
                "♣️ Il faut **7 500 €** pour faire venir Coca Cherry, patron."
            )

        else:
            msg = (
                "🍒 **Coca Cherry est arrivée.**\\n"
                "Elle met l'ambiance avec un show twerk et attire du monde.\\n\\n"
                "📈 **+40 clients** au prochain service.\n"
                "🔥 Si **Lagui** fait son showcase sur ce même service : **COMBO x2**."
            )

        await interaction.response.edit_message(
            embed=base_embed(
                "🍒 Coca Cherry",
                msg
            ),
            view=ActivitiesView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Retour direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )




class ShopCategoryView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )
        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Cette boutique appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Concessionnaire",
        emoji="🚘",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def cars(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=category_embed(
                "Concessionnaire",
                CARS,
                club.get(
                    "cars",
                    []
                ),
                "🚘"
            ),
            view=ItemShopView(
                self.owner_id,
                "cars"
            )
        )

    @discord.ui.button(
        label="Montres",
        emoji="⌚",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def watches(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=category_embed(
                "Boutique de montres",
                WATCHES,
                club.get(
                    "watches",
                    []
                ),
                "⌚"
            ),
            view=ItemShopView(
                self.owner_id,
                "watches"
            )
        )

    @discord.ui.button(
        label="Bitcoin",
        emoji="🪙",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def bitcoin(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=bitcoin_embed(
                club
            ),
            view=BitcoinView(
                self.owner_id
            )
        )


class ItemSelect(
    discord.ui.Select
):
    def __init__(
        self,
        owner_id,
        category
    ):
        self.owner_id = owner_id
        self.category = category

        items = (
            CARS
            if category == "cars"
            else WATCHES
        )

        options = [
            discord.SelectOption(
                label=item["name"][:100],
                value=item_id,
                description=(
                    f"Achat {money(item['price'])} • Vente {money(int(item['price'] * RESALE_RATE))}"
                )[:100]
            )
            for item_id, item in items.items()
        ]

        super().__init__(
            placeholder="Choisir un article...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        item_id = self.values[0]

        view = ItemActionView(
            self.owner_id,
            self.category,
            item_id
        )

        items = (
            CARS
            if self.category == "cars"
            else WATCHES
        )

        item = items[
            item_id
        ]

        await interaction.response.edit_message(
            embed=base_embed(
                f"♣️ {item['name']}",
                (
                    f"Achat : **{money(item['price'])}**\n"
                    f"Revente : **{money(int(item['price'] * RESALE_RATE))}**"
                )
            ),
            view=view
        )


class ItemShopView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id,
        category
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id
        self.category = category

        self.add_item(
            ItemSelect(
                owner_id,
                category
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Cette boutique appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Retour boutique",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=shop_home_embed(
                club
            ),
            view=ShopCategoryView(
                self.owner_id
            )
        )


class ItemActionView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id,
        category,
        item_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id
        self.category = category
        self.item_id = item_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Cette boutique appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    def get_item(self):
        items = (
            CARS
            if self.category == "cars"
            else WATCHES
        )

        return items[
            self.item_id
        ]

    @discord.ui.button(
        label="Acheter",
        emoji="💶",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def buy(
        self,
        interaction,
        button
    ):
        item = self.get_item()

        def do_buy(
            club
        ):
            price = int(
                item["price"]
            )

            if int(
                club.get(
                    "cash",
                    0
                )
            ) < price:
                return "NO_MONEY"

            club["cash"] = int(
                club.get(
                    "cash",
                    0
                )
            ) - price

            club.setdefault(
                self.category,
                []
            ).append(
                self.item_id
            )

            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            do_buy
        )

        if result == "NO_MONEY":
            await interaction.response.send_message(
                "♣️ Trésorerie insuffisante, patron.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "♣️ Achat confirmé",
                (
                    f"Vous avez acheté **{item['name']}** pour **{money(item['price'])}**."
                )
            ),
            view=ItemShopView(
                self.owner_id,
                self.category
            )
        )

    @discord.ui.button(
        label="Revendre",
        emoji="💸",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def sell(
        self,
        interaction,
        button
    ):
        item = self.get_item()

        def do_sell(
            club
        ):
            owned = club.setdefault(
                self.category,
                []
            )

            if self.item_id not in owned:
                return "NOT_OWNED"

            owned.remove(
                self.item_id
            )

            resale = int(
                item["price"]
                * RESALE_RATE
            )

            club["cash"] = int(
                club.get(
                    "cash",
                    0
                )
            ) + resale

            return resale

        club, result = await mutate_club(
            self.owner_id,
            do_sell
        )

        if result == "NOT_OWNED":
            await interaction.response.send_message(
                "♣️ Vous ne possédez pas cet article.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "💸 Vente confirmée",
                (
                    f"**{item['name']}** revendu pour **{money(result)}**."
                )
            ),
            view=ItemShopView(
                self.owner_id,
                self.category
            )
        )

    @discord.ui.button(
        label="Retour",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        items = (
            CARS
            if self.category == "cars"
            else WATCHES
        )

        title = (
            "Concessionnaire"
            if self.category == "cars"
            else "Boutique de montres"
        )

        emoji = (
            "🚘"
            if self.category == "cars"
            else "⌚"
        )

        await interaction.response.edit_message(
            embed=category_embed(
                title,
                items,
                club.get(
                    self.category,
                    []
                ),
                emoji
            ),
            view=ItemShopView(
                self.owner_id,
                self.category
            )
        )


class BitcoinAmountModal(
    discord.ui.Modal
):
    amount = discord.ui.TextInput(
        label="Nombre de Bitcoin",
        placeholder="Ex : 1, 5, 25, 100...",
        min_length=1,
        max_length=10
    )

    def __init__(
        self,
        owner_id,
        mode
    ):
        title = (
            "🪙 Acheter des Bitcoin"
            if mode == "buy"
            else "💸 Revendre des Bitcoin"
        )

        super().__init__(
            title=title
        )

        self.owner_id = owner_id
        self.mode = mode

    async def on_submit(
        self,
        interaction
    ):
        raw = re.sub(
            r"[^0-9]",
            "",
            str(
                self.amount.value
            )
        )

        if not raw:
            await interaction.response.send_message(
                "♣️ Entrez une quantité valide, patron.",
                ephemeral=True
            )
            return

        quantity = int(
            raw
        )

        if quantity <= 0:
            await interaction.response.send_message(
                "♣️ La quantité doit être supérieure à 0.",
                ephemeral=True
            )
            return

        if quantity > 1_000_000:
            await interaction.response.send_message(
                "♣️ Quantité trop importante pour une seule opération.",
                ephemeral=True
            )
            return

        if self.mode == "buy":
            total = (
                quantity
                * BITCOIN_PRICE
            )

            def buy(
                club
            ):
                cash = int(
                    club.get(
                        "cash",
                        0
                    )
                )

                if cash < total:
                    return "NO_MONEY"

                club["cash"] = (
                    cash
                    - total
                )

                club["bitcoin"] = int(
                    club.get(
                        "bitcoin",
                        0
                    )
                ) + quantity

                return "OK"

            club, result = await mutate_club(
                self.owner_id,
                buy
            )

            if result == "NO_MONEY":
                await interaction.response.send_message(
                    (
                        f"♣️ Il faut **{money(total)}** pour acheter "
                        f"**{quantity} BTC**, patron."
                    ),
                    ephemeral=True
                )
                return

            await interaction.response.edit_message(
                embed=bitcoin_embed(
                    club
                ),
                view=BitcoinView(
                    self.owner_id
                )
            )

        else:
            resale_price = int(
                BITCOIN_PRICE
                * RESALE_RATE
            )

            total = (
                quantity
                * resale_price
            )

            def sell(
                club
            ):
                btc = int(
                    club.get(
                        "bitcoin",
                        0
                    )
                )

                if btc < quantity:
                    return "NO_BTC"

                club["bitcoin"] = (
                    btc
                    - quantity
                )

                club["cash"] = int(
                    club.get(
                        "cash",
                        0
                    )
                ) + total

                return "OK"

            club, result = await mutate_club(
                self.owner_id,
                sell
            )

            if result == "NO_BTC":
                await interaction.response.send_message(
                    (
                        f"♣️ Vous ne possédez pas **{quantity} BTC**, patron."
                    ),
                    ephemeral=True
                )
                return

            await interaction.response.edit_message(
                embed=bitcoin_embed(
                    club
                ),
                view=BitcoinView(
                    self.owner_id
                )
            )


class BitcoinView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Cette boutique appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Acheter BTC",
        emoji="🪙",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def buy_btc(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            BitcoinAmountModal(
                self.owner_id,
                "buy"
            )
        )

    @discord.ui.button(
        label="Revendre BTC",
        emoji="💸",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def sell_btc(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            BitcoinAmountModal(
                self.owner_id,
                "sell"
            )
        )

    @discord.ui.button(
        label="Retour boutique",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=shop_home_embed(
                club
            ),
            view=ShopCategoryView(
                self.owner_id
            )
        )


class ManagerSelect(
    discord.ui.Select
):
    def __init__(
        self,
        owner_id
    ):
        self.owner_id = owner_id

        options = []

        for manager_id, manager in MANAGERS.items():
            options.append(
                discord.SelectOption(
                    label=f"{manager['name']} — Niveau {manager['level']}",
                    value=manager_id,
                    description=(
                        f"{money(manager['salary'])}/3 min • {manager['description']}"
                    )[:100],
                    emoji="♣️"
                )
            )

        super().__init__(
            placeholder="Choisir un manager...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        manager_id = self.values[0]

        def hire(
            club
        ):
            club["manager_id"] = manager_id
            return "OK"

        club, _ = await mutate_club(
            self.owner_id,
            hire
        )

        manager = MANAGERS[
            manager_id
        ]

        await interaction.response.edit_message(
            embed=base_embed(
                "♣️ Contrat signé",
                (
                    f"**{manager['name']}** devient votre manager.\n"
                    f"Salaire : **{money(manager['salary'])} toutes les 3 minutes**."
                )
            ),
            view=ManagerView(
                self.owner_id
            )
        )


class ManagerView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id
        self.add_item(
            ManagerSelect(
                owner_id
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Virer le manager",
        emoji="🗑️",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def fire_manager(
        self,
        interaction,
        button
    ):
        def fire(
            club
        ):
            if not club.get(
                "manager_id"
            ):
                return "NONE"

            club["manager_id"] = None
            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            fire
        )

        if result == "NONE":
            await interaction.response.send_message(
                "♣️ Vous n'avez aucun manager à virer.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=managers_embed(
                club
            ),
            view=ManagerView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Retour direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


class EquipmentSelect(
    discord.ui.Select
):
    def __init__(
        self,
        owner_id,
        club
    ):
        self.owner_id = owner_id

        owned = set(
            club.get(
                "equipment",
                []
            )
        )

        options = []

        for item_id, item in EQUIPMENT_UPGRADES.items():
            if item_id in owned:
                continue

            options.append(
                discord.SelectOption(
                    label=item["name"][:100],
                    value=item_id,
                    description=(
                        f"{money(item['cost'])} • {item['description']}"
                    )[:100]
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="Tout est déjà acheté",
                    value="none"
                )
            ]

        super().__init__(
            placeholder="Acheter une amélioration...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        # Évite le message "Olivia n'a pas répondu à temps".
        await interaction.response.defer()

        item_id = self.values[0]

        if item_id == "none":
            await interaction.followup.send(
                "♣️ Votre établissement possède déjà tout l'équipement disponible, patron.",
                ephemeral=True
            )
            return

        item = EQUIPMENT_UPGRADES[
            item_id
        ]

        def buy_item(
            club
        ):
            owned = club.setdefault(
                "equipment",
                []
            )

            if item_id in owned:
                return "OWNED"

            if int(
                club.get(
                    "cash",
                    0
                )
            ) < int(
                item["cost"]
            ):
                return "NO_MONEY"

            club["cash"] = int(
                club.get(
                    "cash",
                    0
                )
            ) - int(
                item["cost"]
            )

            owned.append(
                item_id
            )

            return "OK"

        club, result = await mutate_club(
            self.owner_id,
            buy_item
        )

        if result == "NO_MONEY":
            await interaction.followup.send(
                (
                    "♣️ Trésorerie insuffisante, patron.\n"
                    f"Il faut **{money(item['cost'])}**."
                ),
                ephemeral=True
            )
            return

        if result == "OWNED":
            await interaction.followup.send(
                "♣️ Cette amélioration est déjà installée.",
                ephemeral=True
            )
            return

        await interaction.edit_original_response(
            embed=equipment_embed(
                club
            ),
            view=EquipmentView(
                self.owner_id,
                club
            )
        )


class EquipmentView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id,
        club
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

        # Le menu déroulant est affiché DIRECTEMENT.
        # Le joueur choisit exactement ce qu'il veut acheter.
        self.add_item(
            EquipmentSelect(
                owner_id,
                club
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Retour direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )


class EquipmentPurchaseView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id,
        club
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

        self.add_item(
            EquipmentSelect(
                owner_id,
                club
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Retour",
        emoji="♣️",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=equipment_embed(
                club
            ),
            view=EquipmentView(
                self.owner_id,
                club
            )
        )


class UpgradeView(
    discord.ui.View
):
    def __init__(
        self,
        owner_id
    ):
        super().__init__(
            timeout=900
        )

        self.owner_id = owner_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "♣️ Ce dossier appartient à un autre patron.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Acheter l'amélioration",
        emoji="♠️",
        style=discord.ButtonStyle.secondary
    )
    async def buy(
        self,
        interaction,
        button
    ):
        def upgrade(
            club
        ):
            current = int(
                club.get(
                    "level",
                    0
                )
            )

            if current >= 6:
                return "MAX"

            target = current + 1

            cost = UPGRADE_COSTS[
                target
            ]

            if int(
                club.get(
                    "cash",
                    0
                )
            ) < cost:
                return (
                    "NO_MONEY",
                    cost
                )

            club["cash"] = int(
                club.get(
                    "cash",
                    0
                )
            ) - cost

            club["level"] = target

            return (
                "OK",
                target
            )

        club, result = await mutate_club(
            self.owner_id,
            upgrade
        )

        if result == "MAX":
            await interaction.response.send_message(
                "♣️ Votre établissement est déjà au niveau maximum, patron.",
                ephemeral=True
            )
            return

        if isinstance(
            result,
            tuple
        ) and result[0] == "NO_MONEY":
            await interaction.response.send_message(
                (
                    "♣️ Trésorerie insuffisante, patron.\n"
                    f"Il faut **{money(result[1])}**."
                ),
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=upgrades_embed(
                club
            ),
            view=UpgradeView(
                self.owner_id
            )
        )

    @discord.ui.button(
        label="Retour direction",
        emoji="♣️",
        style=discord.ButtonStyle.secondary
    )
    async def back(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.owner_id
        )

        await interaction.response.edit_message(
            embed=dashboard_embed(
                club,
                interaction.user
            ),
            view=NightclubMenuView(
                self.owner_id
            )
        )



async def ranking_embed(guild):
    async with data_lock:
        data = load_data()

        rows = []

        for user_id, club in data.items():
            process_ticks(
                club
            )
            process_random_event(
                club
            )

            member = None

            try:
                member = guild.get_member(
                    int(
                        user_id
                    )
                )
            except Exception:
                member = None

            # On ne classe que les utilisateurs encore présents dans le serveur.
            if member is None:
                continue

            rows.append(
                {
                    "user":
                        member.mention,
                    "club":
                        club.get(
                            "name",
                            "Sans nom"
                        ),
                    "cash":
                        int(
                            club.get(
                                "cash",
                                0
                            )
                        ),
                    "level":
                        int(
                            club.get(
                                "level",
                                0
                            )
                        ),
                }
            )

        save_data(
            data
        )

    rows.sort(
        key=lambda x: (
            x["cash"],
            x["level"]
        ),
        reverse=True
    )

    embed = base_embed(
        "♣️ Classement des boîtes de nuit",
        "🖤 *Classement par trésorerie des établissements du serveur.*"
    )

    if not rows:
        embed.description = (
            "Aucune boîte de nuit n'est encore enregistrée sur ce serveur."
        )
        return embed

    lines = []

    medals = [
        "🥇",
        "🥈",
        "🥉",
    ]

    for index, row in enumerate(
        rows[:20],
        start=1
    ):
        badge = (
            medals[index - 1]
            if index <= 3
            else f"`#{index}`"
        )

        lines.append(
            (
                f"{badge} **{row['club']}** — {row['user']}\\n"
                f"└ ♠️ {level_name(row['level'])} • 💶 {money(row['cash'])}"
            )
        )

    embed.add_field(
        name="🏆 Direction générale",
        value="\\n".join(
            lines
        )[:1024],
        inline=False
    )

    embed.set_footer(
        text="♣️ Cliquez sur le @ d’un joueur pour ouvrir son profil Discord. Les équipements ne sont pas affichés."
    )

    return embed



# ============================================================
# TRADE ENTRE JOUEURS
# ============================================================

def trade_embed(sender, target):
    return base_embed(
        "♣️ TRADE",
        (
            f"Échange entre {sender.mention} et {target.mention}.\n\n"
            "Choisissez ce que vous souhaitez proposer : argent, Bitcoin, voiture ou montre.\n"
            "Le destinataire devra accepter avant que l'objet ou l'argent soit transféré."
        )
    )


class TradeMoneyModal(
    discord.ui.Modal,
    title="💶 Proposer de l'argent"
):
    amount = discord.ui.TextInput(
        label="Montant (€)",
        placeholder="Ex : 50000",
        min_length=1,
        max_length=15
    )

    def __init__(
        self,
        sender_id,
        target_id
    ):
        super().__init__()
        self.sender_id = sender_id
        self.target_id = target_id

    async def on_submit(
        self,
        interaction
    ):
        raw = re.sub(
            r"[^0-9]",
            "",
            str(
                self.amount.value
            )
        )

        if not raw:
            await interaction.response.send_message(
                "♣️ Montant invalide.",
                ephemeral=True
            )
            return

        amount = int(
            raw
        )

        if amount <= 0:
            await interaction.response.send_message(
                "♣️ Le montant doit être supérieur à 0 €.",
                ephemeral=True
            )
            return

        club = await get_club(
            self.sender_id
        )

        if not club or int(
            club.get(
                "cash",
                0
            )
        ) < amount:
            await interaction.response.send_message(
                "♣️ Trésorerie insuffisante pour cette proposition.",
                ephemeral=True
            )
            return

        target = interaction.guild.get_member(
            self.target_id
        )

        if target is None:
            try:
                target = await interaction.guild.fetch_member(
                    self.target_id
                )
            except Exception:
                target = None

        if target is None:
            await interaction.response.send_message(
                "♣️ Joueur introuvable.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=base_embed(
                "💶 Proposition de trade",
                (
                    f"{interaction.user.mention} propose **{money(amount)}** "
                    f"à {target.mention}."
                )
            ),
            view=TradeConfirmView(
                self.sender_id,
                self.target_id,
                "money",
                amount
            )
        )


class TradeBitcoinModal(
    discord.ui.Modal,
    title="🪙 Proposer des Bitcoin"
):
    amount = discord.ui.TextInput(
        label="Nombre de BTC",
        placeholder="Ex : 1, 5, 20...",
        min_length=1,
        max_length=10
    )

    def __init__(
        self,
        sender_id,
        target_id
    ):
        super().__init__()
        self.sender_id = sender_id
        self.target_id = target_id

    async def on_submit(
        self,
        interaction
    ):
        raw = re.sub(
            r"[^0-9]",
            "",
            str(
                self.amount.value
            )
        )

        if not raw:
            await interaction.response.send_message(
                "♣️ Quantité invalide.",
                ephemeral=True
            )
            return

        amount = int(
            raw
        )

        club = await get_club(
            self.sender_id
        )

        if not club or int(
            club.get(
                "bitcoin",
                0
            )
        ) < amount:
            await interaction.response.send_message(
                "♣️ Vous ne possédez pas assez de Bitcoin.",
                ephemeral=True
            )
            return

        target = interaction.guild.get_member(
            self.target_id
        )

        if target is None:
            try:
                target = await interaction.guild.fetch_member(
                    self.target_id
                )
            except Exception:
                target = None

        if target is None:
            await interaction.response.send_message(
                "♣️ Joueur introuvable.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=base_embed(
                "🪙 Proposition de trade",
                (
                    f"{interaction.user.mention} propose **{amount} BTC** "
                    f"à {target.mention}."
                )
            ),
            view=TradeConfirmView(
                self.sender_id,
                self.target_id,
                "bitcoin",
                amount
            )
        )


class TradeItemSelect(
    discord.ui.Select
):
    def __init__(
        self,
        sender_id,
        target_id,
        category,
        owned_ids
    ):
        self.sender_id = sender_id
        self.target_id = target_id
        self.category = category

        items = (
            CARS
            if category == "cars"
            else WATCHES
        )

        options = []

        seen = set()

        for item_id in owned_ids:
            if item_id in seen:
                continue

            seen.add(
                item_id
            )

            item = items.get(
                item_id
            )

            if not item:
                continue

            count = owned_ids.count(
                item_id
            )

            options.append(
                discord.SelectOption(
                    label=(
                        f"{item['name']} x{count}"
                        if count > 1
                        else item["name"]
                    )[:100],
                    value=item_id,
                    description=(
                        f"Valeur boutique : {money(item['price'])}"
                    )[:100]
                )
            )

        if not options:
            options = [
                discord.SelectOption(
                    label="Aucun objet disponible",
                    value="none"
                )
            ]

        super().__init__(
            placeholder="Choisir l'objet à proposer...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )

    async def callback(
        self,
        interaction
    ):
        item_id = self.values[0]

        if item_id == "none":
            await interaction.response.send_message(
                "♣️ Vous n'avez aucun objet disponible dans cette catégorie.",
                ephemeral=True
            )
            return

        items = (
            CARS
            if self.category == "cars"
            else WATCHES
        )

        item = items[
            item_id
        ]

        target = interaction.guild.get_member(
            self.target_id
        )

        if target is None:
            await interaction.response.send_message(
                "♣️ Joueur introuvable.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "♣️ Proposition de trade",
                (
                    f"{interaction.user.mention} propose **{item['name']}** "
                    f"à {target.mention}."
                )
            ),
            view=TradeConfirmView(
                self.sender_id,
                self.target_id,
                self.category,
                item_id
            )
        )


class TradeItemView(
    discord.ui.View
):
    def __init__(
        self,
        sender_id,
        target_id,
        category,
        owned_ids
    ):
        super().__init__(
            timeout=900
        )

        self.sender_id = sender_id
        self.target_id = target_id

        self.add_item(
            TradeItemSelect(
                sender_id,
                target_id,
                category,
                owned_ids
            )
        )

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.sender_id:
            await interaction.response.send_message(
                "♣️ Seul le joueur qui propose le trade peut choisir l'objet.",
                ephemeral=True
            )
            return False

        return True


class TradeMenuView(
    discord.ui.View
):
    def __init__(
        self,
        sender_id,
        target_id
    ):
        super().__init__(
            timeout=900
        )

        self.sender_id = sender_id
        self.target_id = target_id

    async def interaction_check(
        self,
        interaction
    ):
        if interaction.user.id != self.sender_id:
            await interaction.response.send_message(
                "♣️ Seul le joueur qui a ouvert le trade peut choisir l'offre.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Argent",
        emoji="💶",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def money_offer(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            TradeMoneyModal(
                self.sender_id,
                self.target_id
            )
        )

    @discord.ui.button(
        label="Bitcoin",
        emoji="🪙",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def bitcoin_offer(
        self,
        interaction,
        button
    ):
        await interaction.response.send_modal(
            TradeBitcoinModal(
                self.sender_id,
                self.target_id
            )
        )

    @discord.ui.button(
        label="Voiture",
        emoji="🚘",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def car_offer(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.sender_id
        )

        await interaction.response.edit_message(
            embed=base_embed(
                "🚘 Choisir une voiture",
                "Sélectionnez la voiture à proposer."
            ),
            view=TradeItemView(
                self.sender_id,
                self.target_id,
                "cars",
                club.get(
                    "cars",
                    []
                )
            )
        )

    @discord.ui.button(
        label="Montre",
        emoji="⌚",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def watch_offer(
        self,
        interaction,
        button
    ):
        club = await get_club(
            self.sender_id
        )

        await interaction.response.edit_message(
            embed=base_embed(
                "⌚ Choisir une montre",
                "Sélectionnez la montre à proposer."
            ),
            view=TradeItemView(
                self.sender_id,
                self.target_id,
                "watches",
                club.get(
                    "watches",
                    []
                )
            )
        )


class TradeConfirmView(
    discord.ui.View
):
    def __init__(
        self,
        sender_id,
        target_id,
        trade_type,
        value
    ):
        super().__init__(
            timeout=600
        )

        self.sender_id = sender_id
        self.target_id = target_id
        self.trade_type = trade_type
        self.value = value

    @discord.ui.button(
        label="Accepter",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def accept(
        self,
        interaction,
        button
    ):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                "♣️ Seul le destinataire peut accepter ce trade.",
                ephemeral=True
            )
            return

        async with data_lock:
            data = load_data()

            sender_key = str(
                self.sender_id
            )

            target_key = str(
                self.target_id
            )

            sender = data.get(
                sender_key
            )

            target = data.get(
                target_key
            )

            if sender is None or target is None:
                await interaction.response.send_message(
                    "♣️ Les deux joueurs doivent posséder une boîte de nuit.",
                    ephemeral=True
                )
                return

            process_ticks(
                sender
            )

            process_ticks(
                target
            )

            if self.trade_type == "money":
                amount = int(
                    self.value
                )

                if int(
                    sender.get(
                        "cash",
                        0
                    )
                ) < amount:
                    await interaction.response.send_message(
                        "♣️ Le joueur n'a plus assez d'argent pour ce trade.",
                        ephemeral=True
                    )
                    return

                sender["cash"] = int(
                    sender.get(
                        "cash",
                        0
                    )
                ) - amount

                target["cash"] = int(
                    target.get(
                        "cash",
                        0
                    )
                ) + amount

                detail = money(
                    amount
                )

            elif self.trade_type == "bitcoin":
                amount = int(
                    self.value
                )

                if int(
                    sender.get(
                        "bitcoin",
                        0
                    )
                ) < amount:
                    await interaction.response.send_message(
                        "♣️ Le joueur n'a plus assez de Bitcoin.",
                        ephemeral=True
                    )
                    return

                sender["bitcoin"] = int(
                    sender.get(
                        "bitcoin",
                        0
                    )
                ) - amount

                target["bitcoin"] = int(
                    target.get(
                        "bitcoin",
                        0
                    )
                ) + amount

                detail = f"{amount} BTC"

            elif self.trade_type in (
                "cars",
                "watches"
            ):
                item_id = str(
                    self.value
                )

                owned = sender.setdefault(
                    self.trade_type,
                    []
                )

                if item_id not in owned:
                    await interaction.response.send_message(
                        "♣️ Le joueur ne possède plus cet objet.",
                        ephemeral=True
                    )
                    return

                owned.remove(
                    item_id
                )

                target.setdefault(
                    self.trade_type,
                    []
                ).append(
                    item_id
                )

                items = (
                    CARS
                    if self.trade_type == "cars"
                    else WATCHES
                )

                detail = items.get(
                    item_id,
                    {
                        "name": item_id
                    }
                )["name"]

            else:
                await interaction.response.send_message(
                    "♣️ Type de trade invalide.",
                    ephemeral=True
                )
                return

            data[sender_key] = sender
            data[target_key] = target

            save_data(
                data
            )

        sender_member = interaction.guild.get_member(
            self.sender_id
        )

        sender_mention = (
            sender_member.mention
            if sender_member
            else f"<@{self.sender_id}>"
        )

        await interaction.response.edit_message(
            embed=base_embed(
                "✅ Trade accepté",
                (
                    f"{sender_mention} → {interaction.user.mention}\n"
                    f"**{detail}** a été transféré."
                )
            ),
            view=None
        )

    @discord.ui.button(
        label="Refuser",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def refuse(
        self,
        interaction,
        button
    ):
        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                "♣️ Seul le destinataire peut refuser ce trade.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            embed=base_embed(
                "❌ Trade refusé",
                "La proposition a été refusée."
            ),
            view=None
        )


class BottlePackSelect(
    discord.ui.Select
):
    def __init__(
        self,
        sender_id,
        target_id
    ):
        self.sender_id = sender_id
        self.target_id = target_id

        options = [
            discord.SelectOption(
                label=pack["name"],
                value=pack_id,
                emoji=pack["emoji"],
                description=(
                    f"Prix {money(pack['cost'])} • "
                    f"Boîte reçoit {money(pack['receiver_bonus'])}"
                )[:100]
            )
            for pack_id, pack in BOTTLE_PACKS.items()
        ]

        super().__init__(
            placeholder="Choisir un pack de bouteilles...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(
        self,
        interaction
    ):
        if interaction.user.id != self.sender_id:
            await interaction.response.send_message(
                "♣️ Ce cadeau ne vous appartient pas, patron.",
                ephemeral=True
            )
            return

        pack_id = self.values[0]
        pack = BOTTLE_PACKS[
            pack_id
        ]

        async with data_lock:
            data = load_data()

            sender_key = str(
                self.sender_id
            )
            target_key = str(
                self.target_id
            )

            sender = data.get(
                sender_key
            )
            receiver = data.get(
                target_key
            )

            if sender is None or receiver is None:
                await interaction.response.send_message(
                    "♣️ Une des deux boîtes n'existe plus.",
                    ephemeral=True
                )
                return

            process_ticks(
                sender
            )
            process_ticks(
                receiver
            )

            cost = int(
                pack["cost"]
            )

            if int(
                sender.get(
                    "cash",
                    0
                )
            ) < cost:
                await interaction.response.send_message(
                    f"♣️ Il faut **{money(cost)}** pour envoyer ce pack.",
                    ephemeral=True
                )
                return

            sender["cash"] = int(
                sender.get(
                    "cash",
                    0
                )
            ) - cost

            receiver["cash"] = int(
                receiver.get(
                    "cash",
                    0
                )
            ) + int(
                pack["receiver_bonus"]
            )

            receiver["client_bonus_next"] = int(
                receiver.get(
                    "client_bonus_next",
                    0
                )
            ) + max(
                5,
                int(
                    pack["receiver_bonus"]
                    / 500
                )
            )

            data[sender_key] = sender
            data[target_key] = receiver

            save_data(
                data
            )

        target = interaction.guild.get_member(
            self.target_id
        )

        if target is None:
            try:
                target = await interaction.guild.fetch_member(
                    self.target_id
                )
            except Exception:
                target = None

        target_mention = (
            target.mention
            if target
            else f"<@{self.target_id}>"
        )

        await interaction.response.edit_message(
            embed=base_embed(
                "🍾 Pack envoyé",
                (
                    f"{interaction.user.mention} envoie **{pack['name']}** "
                    f"à la boîte de {target_mention}.\\n\\n"
                    f"💸 Coût : **{money(pack['cost'])}**\\n"
                    f"💶 La boîte reçoit : **+{money(pack['receiver_bonus'])}**\\n"
                    "🥂 Le pack attire aussi quelques clients au prochain service."
                )
            ),
            view=None
        )


class BottlePackView(
    discord.ui.View
):
    def __init__(
        self,
        sender_id,
        target_id
    ):
        super().__init__(
            timeout=300
        )

        self.add_item(
            BottlePackSelect(
                sender_id,
                target_id
            )
        )


# ============================================================
# ROUTEUR PUBLIC
# ============================================================

def is_nightclub_trigger(text):
    n = normalize(
        text
    )

    # Retire "Olivia" si présent.
    n = re.sub(
        r"^olivia\s*",
        "",
        n
    ).strip()

    # Commande courte du mode boîte de nuit.
    # "Olivia BDN" ouvre le menu.
    if n == "bdn":
        return True

    return False


async def handle_public_message(
    message,
    bot
):
    """
    Retourne True uniquement pour le jeu Nightclub.
    Les autres messages restent totalement au main.py / Olivia Music.
    """
    content = str(
        message.content or ""
    ).strip()

    if not content:
        return False

    # FLEX est autorisé dans tous les salons.
    # BDN / CLS / BTQ restent limités au salon Nightclub.

    # On exige Olivia pour ne pas capturer les conversations normales du serveur.
    if not re.match(
        r"^\s*olivia\b",
        content,
        re.I
    ):
        return False

    normalized = normalize(
        content
    )

    normalized = re.sub(
        r"^olivia\s*",
        "",
        normalized
    ).strip()

    # CLEAR global :
    # uniquement toi peux l'utiliser, dans n'importe quel salon du serveur.
    if normalized == "clear":
        if message.author.id != 734865069904756766:
            await message.channel.send(
                "♣️ Vous n'avez pas accès à cette commande."
            )
            return True

        try:
            deleted = await message.channel.purge(
                limit=None,
                reason="Olivia clear"
            )

            print(
                f"🧹 Clear : {len(deleted)} messages supprimés dans #{message.channel.name}"
            )

        except discord.Forbidden:
            await message.channel.send(
                "♣️ Il me manque la permission **Gérer les messages** dans ce salon."
            )

        except Exception as e:
            print(
                "❌ Clear :",
                repr(e)
            )

            await message.channel.send(
                "♣️ Je n'ai pas réussi à vider ce salon, patron."
            )

        return True

    # TRADE est disponible dans tous les salons du serveur.
    if normalized.startswith("trade"):
        mention_match = re.search(
            r"<@!?(\d{15,22})>",
            content
        )

        if not mention_match:
            await message.channel.send(
                "♣️ Utilisation : **Olivia TRADE @joueur**"
            )
            return True

        target_id = int(
            mention_match.group(1)
        )

        if target_id == message.author.id:
            await message.channel.send(
                "♣️ Vous ne pouvez pas trade avec vous-même, patron."
            )
            return True

        target = message.guild.get_member(
            target_id
        )

        # Si le membre n'est pas dans le cache Discord, on le récupère
        # directement depuis l'API du serveur.
        if target is None:
            try:
                target = await message.guild.fetch_member(
                    target_id
                )
            except Exception as e:
                print(
                    "⚠️ TRADE fetch_member :",
                    repr(e)
                )
                target = None

        if target is None:
            await message.channel.send(
                "♣️ Je ne trouve pas ce joueur sur le serveur, patron."
            )
            return True

        if target.bot:
            await message.channel.send(
                "♣️ Vous ne pouvez pas trade avec un bot, patron."
            )
            return True

        sender_club = await get_club(
            message.author.id
        )

        target_club = await get_club(
            target_id
        )

        if sender_club is None:
            await message.channel.send(
                "♣️ Vous devez d'abord créer votre boîte avec **Olivia BDN**."
            )
            return True

        if target_club is None:
            await message.channel.send(
                f"♣️ {target.mention} doit d'abord créer sa boîte avec **Olivia BDN**."
            )
            return True

        await message.channel.send(
            embed=trade_embed(
                message.author,
                target
            ),
            view=TradeMenuView(
                message.author.id,
                target_id
            )
        )
        return True

    # FLEX est disponible dans TOUS les salons du serveur.
    if normalized == "flex":
        club = await get_club(
            message.author.id
        )

        if club is None:
            await message.channel.send(
                "♣️ Vous devez d'abord créer votre boîte avec **Olivia BDN**."
            )
            return True

        await message.channel.send(
            embed=flex_embed(
                club,
                message.author
            )
        )
        return True

    # Tout ce qui suit est réservé au salon Nightclub.
    if message.channel.id != NIGHTCLUB_CHANNEL_ID:
        return False

    # BRAQUAGE : disponible uniquement dans le salon Nightclub.
    # Un essai tous les 4 services.
    if normalized.startswith("braque"):
        mention_match = re.search(
            r"<@!?(\d{15,22})>",
            content
        )

        if not mention_match:
            await message.channel.send(
                "♣️ Utilisation : **Olivia BRAQUE @joueur**"
            )
            return True

        target_id = int(
            mention_match.group(1)
        )

        if target_id == message.author.id:
            await message.channel.send(
                "♣️ Vous ne pouvez pas braquer votre propre boîte, patron."
            )
            return True

        target = message.guild.get_member(
            target_id
        )

        if target is None:
            try:
                target = await message.guild.fetch_member(
                    target_id
                )
            except Exception:
                target = None

        if target is None:
            await message.channel.send(
                "♣️ Je ne trouve pas ce joueur sur le serveur, patron."
            )
            return True

        if target.bot:
            await message.channel.send(
                "♣️ Impossible de braquer la boîte d'un bot, patron."
            )
            return True

        async with data_lock:
            data = load_data()

            attacker_key = str(
                message.author.id
            )

            target_key = str(
                target_id
            )

            attacker = data.get(
                attacker_key
            )

            victim = data.get(
                target_key
            )

            if attacker is None:
                await message.channel.send(
                    "♣️ Vous devez d'abord créer votre boîte avec **Olivia BDN**."
                )
                return True

            if victim is None:
                await message.channel.send(
                    f"♣️ {target.mention} ne possède pas encore de boîte de nuit."
                )
                return True

            # Met à jour les services avant de vérifier le cooldown.
            process_ticks(
                attacker
            )

            process_ticks(
                victim
            )

            current_service = int(
                attacker.get(
                    "service_count",
                    0
                )
            )

            last_robbery = int(
                attacker.get(
                    "last_robbery_service",
                    -999999
                )
            )

            services_since = (
                current_service
                - last_robbery
            )

            if services_since < 4:
                remaining = (
                    4
                    - services_since
                )

                await message.channel.send(
                    (
                        "🚨 Vos hommes doivent se faire oublier, patron.\n"
                        f"Attendez encore **{remaining} service"
                        + ("s" if remaining > 1 else "")
                        + "** avant un nouveau braquage."
                    )
                )
                return True

            victim_cash = int(
                victim.get(
                    "cash",
                    0
                )
            )

            if victim_cash <= 0:
                await message.channel.send(
                    f"🥀 La boîte de {target.mention} n'a rien à voler pour le moment."
                )
                return True

            # Le cooldown démarre dès qu'un vrai braquage est tenté.
            attacker["last_robbery_service"] = current_service

            success_chance = robbery_success_chance(
                attacker,
                victim
            )

            if random.random() < (
                success_chance
                / 100
            ):
                stolen = int(
                    victim_cash
                    * 0.25
                )

                victim["cash"] = max(
                    0,
                    victim_cash - stolen
                )

                attacker["cash"] = int(
                    attacker.get(
                        "cash",
                        0
                    )
                ) + stolen

                gained_clients = random.randint(
                    25,
                    70
                )

                lost_clients = random.randint(
                    20,
                    60
                )

                attacker["client_bonus_next"] = int(
                    attacker.get(
                        "client_bonus_next",
                        0
                    )
                ) + gained_clients

                victim["client_penalty_next"] = int(
                    victim.get(
                        "client_penalty_next",
                        0
                    )
                ) + lost_clients

                result_title = "💰 Braquage réussi"
                result_text = (
                    f"♣️ Les hommes de {message.author.mention} ont frappé "
                    f"la boîte de {target.mention}.\n\n"
                    f"💶 Butin : **{money(stolen)}**\n"
                    "📉 **25 %** de la trésorerie adverse a été récupérée.\n"
                    f"👥 Votre réputation monte : **+{gained_clients} clients** au prochain service.\n"
                    f"🥀 La boîte adverse perd **-{lost_clients} clients** au prochain service.\n"
                    f"🎯 Chance de réussite : **{success_chance} %**"
                )

            else:
                attacker_cash = int(
                    attacker.get(
                        "cash",
                        0
                    )
                )

                lost = int(
                    attacker_cash
                    * 0.25
                )

                attacker["cash"] = max(
                    0,
                    attacker_cash - lost
                )

                lost_clients = random.randint(
                    25,
                    70
                )

                gained_clients = random.randint(
                    20,
                    60
                )

                attacker["client_penalty_next"] = int(
                    attacker.get(
                        "client_penalty_next",
                        0
                    )
                ) + lost_clients

                victim["client_bonus_next"] = int(
                    victim.get(
                        "client_bonus_next",
                        0
                    )
                ) + gained_clients

                result_title = "🚔 Braquage raté"
                result_text = (
                    f"♣️ Le coup contre la boîte de {target.mention} a mal tourné.\n\n"
                    f"💸 Pertes : **{money(lost)}**\n"
                    "🚨 Vous perdez **25 %** de votre propre trésorerie.\n"
                    f"🥀 Votre réputation prend un coup : **-{lost_clients} clients** au prochain service.\n"
                    f"👥 La boîte adverse profite du buzz : **+{gained_clients} clients** au prochain service.\n"
                    f"🛡️ La défense adverse a tenu. Chance de réussite : **{success_chance} %**"
                )

            data[attacker_key] = attacker
            data[target_key] = victim

            save_data(
                data
            )

        embed = base_embed(
            result_title,
            result_text
        )

        embed.set_footer(
            text="♣️ Un nouveau braquage sera possible après 4 services."
        )

        await message.channel.send(
            embed=embed
        )

        return True

    if normalized.startswith("bouteille"):
        mention_match = re.search(
            r"<@!?(\d{15,22})>",
            content
        )

        if not mention_match:
            await message.channel.send(
                "♣️ Utilisation : **Olivia BOUTEILLE @joueur**"
            )
            return True

        target_id = int(
            mention_match.group(1)
        )

        if target_id == message.author.id:
            await message.channel.send(
                "♣️ Envoyez plutôt les bouteilles à une autre boîte, patron."
            )
            return True

        target = message.guild.get_member(
            target_id
        )

        if target is None:
            try:
                target = await message.guild.fetch_member(
                    target_id
                )
            except Exception:
                target = None

        if target is None or target.bot:
            await message.channel.send(
                "♣️ Je n'ai pas reconnu ce joueur, patron."
            )
            return True

        sender_club = await get_club(
            message.author.id
        )

        target_club = await get_club(
            target_id
        )

        if sender_club is None:
            await message.channel.send(
                "♣️ Créez d'abord votre boîte avec **Olivia BDN**."
            )
            return True

        if target_club is None:
            await message.channel.send(
                f"♣️ {target.mention} doit d'abord posséder une boîte de nuit."
            )
            return True

        await message.channel.send(
            embed=base_embed(
                "🍾 Service bouteilles",
                (
                    f"Destinataire : {target.mention}\\n"
                    "Choisissez le pack à envoyer à sa boîte."
                )
            ),
            view=BottlePackView(
                message.author.id,
                target_id
            )
        )

        return True

    if normalized == "btq":
        # On supprime la commande du joueur pour garder le salon propre.
        try:
            await message.delete()
        except Exception:
            pass

        await message.channel.send(
            content=(
                f"♣️ {message.author.mention} — votre boutique privée est prête."
            ),
            view=PrivateMenuLauncherView(
                message.author.id,
                "btq"
            ),
            delete_after=30
        )
        return True

    if normalized == "cls":
        await message.channel.send(
            embed=await ranking_embed(
                message.guild
            )
        )
        return True

    if not is_nightclub_trigger(
        content
    ):
        return False

    # Menu BDN privé : seul le petit bouton temporaire apparaît dans le salon.
    try:
        await message.delete()
    except Exception:
        pass

    await message.channel.send(
        content=(
            f"♣️ {message.author.mention} — votre direction privée est prête."
        ),
        view=PrivateMenuLauncherView(
            message.author.id,
            "bdn"
        ),
        delete_after=30
    )

    return True
