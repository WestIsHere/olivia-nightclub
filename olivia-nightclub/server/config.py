"""
GAME_CONFIG — configuration économique centralisée.

Les valeurs de base viennent du bot Discord (nightclub_v35 + flex.py),
avec un catalogue rap 2016–2026 étendu et rééquilibré pour le jeu web.
Rien n'est hardcodé dans le frontend : le client reçoit la partie publique
de cette configuration via l'API, et l'administrateur peut surcharger
n'importe quelle valeur depuis le panneau admin (stocké en base).

Les améliorations "web" clairement séparées du jeu original sont
regroupées dans la clé "web" (ex : blackjack interactif).
"""

import copy
from .artists import RAP_ARTISTS, RAP_PHRASES
from .showcase_media import DEFAULT_VIDEOS

# ------------------------------------------------------------------
# Artistes : bonus d'entrées (ARTIST_SHOWCASE_BONUS) + ordre d'affichage
# ------------------------------------------------------------------
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

ARTIST_ORDER = ["Lagui", "Boro 700"] + [
    a for a in ARTIST_SHOWCASE_BONUS if a not in ("Lagui", "Boro 700")
]

# Phrases de showcase : (texte, clients_min, clients_max)
SHOWCASE_PHRASES = {
    "Boro 700": [
        ["Boro 700 est arrivé comme un patron, le carré s'est rempli en quelques minutes.", 65, 135],
        ["Boro 700 a retourné la scène et ramené une grosse vague de clients.", 70, 140],
        ["Le passage de Boro 700 a mis toute la boîte en tension.", 60, 130],
        ["Boro 700 a fait lever toute la salle, personne ne voulait partir.", 65, 135],
        ["Boro 700 a transformé la soirée en vraie nuit de patron.", 75, 145],
    ],
    "Lagui": [
        ["Lagui a retourné la boîte, la foule connaissait chaque parole.", 90, 180],
        ["Lagui a fait trembler les murs, personne ne voulait quitter la piste.", 100, 200],
        ["Lagui est monté sur scène et la soirée est partie en folie.", 80, 170],
        ["Lagui a terminé son showcase sous les cris de toute la salle.", 95, 190],
        ["Le showcase de Lagui a fait parler toute la ville cette nuit.", 110, 210],
    ],
    "Gims": [
        ["Gims a lancé ses classiques, toute la salle a chanté avec lui.", 70, 140],
        ["Gims a rempli la piste dès son arrivée sur scène.", 65, 135],
        ["Le passage de Gims a attiré une grosse foule devant la boîte.", 75, 150],
        ["Gims a mis une ambiance énorme jusqu'à la fin du showcase.", 70, 145],
    ],
    "PLK": [
        ["PLK a mis le feu au carré, les clients se sont rapprochés de la scène.", 65, 135],
        ["PLK a enchaîné les morceaux et la boîte s'est remplie.", 60, 130],
        ["Le showcase de PLK a ramené du monde jusqu'à l'entrée.", 70, 140],
        ["PLK a retourné le public avec une fin de showcase explosive.", 65, 145],
    ],
    "Leto": [
        ["Leto a fait monter la pression dès son premier morceau.", 55, 125],
        ["Leto a retourné le carré VIP, la salle était bouillante.", 60, 130],
        ["Le public a suivi Leto du début à la fin du showcase.", 50, 120],
        ["Leto a ramené une vraie ambiance de nuit dans toute la boîte.", 60, 135],
    ],
    "L2B": [
        ["L2B a débarqué à plusieurs et la salle s'est immédiatement réveillée.", 55, 125],
        ["L2B a enchaîné les sons, la piste ne s'est pas vidée.", 50, 120],
        ["Le showcase de L2B a attiré une grosse bande de clients.", 60, 130],
        ["L2B a mis une ambiance collective énorme dans la boîte.", 55, 125],
    ],
    "La Mano": [
        ["La Mano a mis tout le monde debout dès son entrée.", 50, 115],
        ["La Mano a chauffé la salle et les clients ont afflué.", 55, 120],
        ["Le showcase de La Mano a fait monter l'ambiance d'un cran.", 45, 110],
        ["La Mano a terminé son passage sous une salle en folie.", 50, 120],
    ],
    "Nono la grinta": [
        ["Nono la grinta a ramené une énergie folle sur scène.", 45, 110],
        ["Nono la grinta a fait sauter toute la première rangée.", 50, 115],
        ["Le showcase de Nono la grinta a attiré du monde au dernier moment.", 40, 105],
        ["Nono la grinta a laissé la salle en ébullition.", 45, 110],
    ],
    "Timal": [
        ["Timal a retourné la piste avec un showcase très chaud.", 45, 105],
        ["Timal a fait chanter la salle jusqu'à la dernière minute.", 40, 100],
        ["Le passage de Timal a ramené plusieurs groupes de clients.", 45, 110],
        ["Timal a mis une grosse ambiance devant la scène.", 40, 105],
    ],
    "TK": [
        ["TK a chauffé la salle et les téléphones se sont levés partout.", 40, 100],
        ["TK a fait bouger toute la piste pendant son showcase.", 35, 95],
        ["Le showcase de TK a ramené de nouveaux clients dans la nuit.", 40, 100],
        ["TK a terminé son passage avec toute la salle debout.", 35, 95],
    ],
    "Niaks": [
        ["Niaks a mis la pression sur scène, le public a suivi.", 35, 95],
        ["Niaks a retourné le premier rang pendant son showcase.", 35, 90],
        ["Le passage de Niaks a ramené une nouvelle vague de clients.", 40, 100],
        ["Niaks a gardé la piste pleine jusqu'à la fin.", 35, 95],
    ],
    "Le Crime": [
        ["Le Crime a mis une ambiance sombre et lourde dans toute la boîte.", 35, 90],
        ["Le Crime a captivé la salle pendant tout son showcase.", 30, 85],
        ["Le showcase de Le Crime a ramené des curieux jusque devant l'entrée.", 35, 95],
        ["Le Crime a terminé son passage sous les cris du public.", 30, 90],
    ],
    "3robi": [
        ["3robi a ramené une grosse énergie et le public a suivi.", 30, 85],
        ["3robi a fait bouger la salle dès les premières secondes.", 35, 90],
        ["Le showcase de 3robi a ramené du monde sur la piste.", 30, 85],
        ["3robi a transformé la fin de soirée en vrai concert.", 35, 95],
    ],
    "Mensa": [
        ["Mensa a surpris la salle avec un showcase très propre.", 30, 80],
        ["Mensa a ramené une nouvelle ambiance dans la boîte.", 25, 75],
        ["Le public s'est rapproché de la scène pendant le passage de Mensa.", 30, 85],
        ["Mensa a fini son showcase avec une salle bien remplie.", 25, 80],
    ],
    "RnBoi": [
        ["RnBoi a posé une ambiance mélodique, les clients sont restés sur la piste.", 25, 75],
        ["RnBoi a attiré du monde autour de la scène.", 30, 80],
        ["Le showcase de RnBoi a donné une autre vibe à toute la boîte.", 25, 75],
        ["RnBoi a terminé son passage avec un public conquis.", 30, 85],
    ],
    "Timar": [
        ["Timar a mis une bonne pression sur scène et la salle a répondu.", 25, 70],
        ["Timar a ramené plusieurs nouveaux groupes dans la boîte.", 25, 75],
        ["Le showcase de Timar a gardé les clients jusqu'à tard.", 20, 70],
        ["Timar a fini son passage devant une piste bien remplie.", 25, 75],
    ],
    "La Rvfleuse": [
        ["La Rvfleuse a réveillé la salle avec un passage énergique.", 20, 65],
        ["La Rvfleuse a attiré plusieurs curieux devant la scène.", 20, 70],
        ["Le showcase de La Rvfleuse a donné un coup de boost à la soirée.", 25, 70],
        ["La Rvfleuse a gardé la piste animée jusqu'à la fin.", 20, 65],
    ],
    "Bello&Dallas": [
        ["Bello & Dallas ont retourné la boîte, le public a suivi jusqu'au dernier son.", 25, 80],
        ["Bello & Dallas ont mis une ambiance chaotique mais la salle a adoré.", 30, 85],
        ["Le duo Bello & Dallas a fait rester les clients bien après le showcase.", 25, 75],
        ["Bello & Dallas ont chauffé le carré et ramené du monde devant la scène.", 30, 80],
    ],
}

DEFAULT_CONFIG = {
    # ---------------- Temps ----------------
    "tick_seconds": 180,            # TICK_SECONDS : un service toutes les 3 minutes
    "event_interval": 600,          # EVENT_INTERVAL : contrôle événement toutes les 10 min
    "event_chance": 0.25,           # EVENT_CHANCE
    "fun_event_chance": 0.70,       # FUN_EVENT_CHANCE

    # ---------------- Économie de base ----------------
    "bar_min": 900,                 # BAR_MIN
    "bar_max": 4000,                # BAR_MAX
    "vip_base_spend": 2800,         # VIP_BASE_SPEND
    "default_entry_price": 20,      # DEFAULT_ENTRY_PRICE
    "starting_cash": 0,             # new_club()["cash"]
    "club_name_max": 40,

    # VIP par service : 30 % deux VIP, 50 % un VIP, 20 % aucun
    "vip_roll": {"two": 0.30, "one": 0.50},

    # ---------------- Niveaux (level_name / income_multiplier / showcase_multiplier /
    # max_entry_price / client_range_for_level / UPGRADE_COSTS) ----------------
    "levels": [
        {"level": 0, "name": "Club indépendant", "income_mult": 1.00, "showcase_mult": 1.25,
         "max_entry": 25.00, "clients_min": 60,  "clients_max": 575,  "upgrade_cost": 0},
        {"level": 1, "name": "Babinski",         "income_mult": 1.25, "showcase_mult": 1.25,
         "max_entry": 31.25, "clients_min": 140, "clients_max": 635,  "upgrade_cost": 100_000},
        {"level": 2, "name": "L'Ikona",          "income_mult": 1.50, "showcase_mult": 1.375,
         "max_entry": 37.50, "clients_min": 230, "clients_max": 690,  "upgrade_cost": 500_000},
        {"level": 3, "name": "Balajo",           "income_mult": 1.65, "showcase_mult": 1.425,
         "max_entry": 43.75, "clients_min": 325, "clients_max": 805,  "upgrade_cost": 1_200_000},
        {"level": 4, "name": "Le Bikini",        "income_mult": 1.80, "showcase_mult": 1.45,
         "max_entry": 50.00, "clients_min": 405, "clients_max": 980,  "upgrade_cost": 2_500_000},
        {"level": 5, "name": "Miami Club",       "income_mult": 2.00, "showcase_mult": 1.50,
         "max_entry": 57.50, "clients_min": 485, "clients_max": 1150, "upgrade_cost": 5_000_000},
        {"level": 6, "name": "Le Olivia",        "income_mult": 2.25, "showcase_mult": 1.55,
         "max_entry": 65.00, "clients_min": 575, "clients_max": 1380, "upgrade_cost": 10_000_000},
    ],

    # entry_price_client_multiplier : 0 € => +6 %, max => -6 %
    "entry_price_effect": {"max_bonus": 0.06, "span": 0.12},

    # ---------------- Managers (MANAGERS) ----------------
    "managers": {
        "victoria": {
            "name": "Victoria", "level": 1, "salary": 1000,
            "client_bonus": [5, 20], "vip_chance": 0.10, "showcase_chance": 0.10,
            "showcase_cooldown_ticks": 6,
            "description": "Débutante : petite pub, quelques clients en plus, rares VIP et showcases.",
        },
        "josas": {
            "name": "Josas", "level": 2, "salary": 2500,
            "client_bonus": [20, 60], "vip_chance": 0.22, "showcase_chance": 0.22,
            "showcase_cooldown_ticks": 3,
            "description": "Confirmée : vraie promo, plus de clients, VIP plus fréquents et showcases réguliers.",
        },
        "olivia": {
            "name": "Olivia", "level": 3, "salary": 5000,
            "client_bonus": [50, 120], "vip_chance": 0.35, "showcase_chance": 0.35,
            "showcase_cooldown_ticks": 2,
            "description": "Premium : grosse communication, nombreux clients, VIP et showcases très efficaces.",
        },
    },

    # ---------------- Équipements (EQUIPMENT_UPGRADES) ----------------
    "equipment": {
        "dj":        {"name": "DJ résident premium",  "emoji": "🎧", "cost": 75_000,
                      "description": "+8 % sur les entrées", "entry_bonus": 0.08},
        "dancers":   {"name": "Équipe de danseuses",  "emoji": "💃", "cost": 120_000,
                      "description": "+8 % sur les dépenses VIP", "vip_bonus": 0.08},
        "smoke":     {"name": "Machines à fumée",     "emoji": "🌫️", "cost": 45_000,
                      "description": "+5 % sur le bar", "bar_bonus": 0.05},
        "lights":    {"name": "Lumières & lasers",    "emoji": "✨", "cost": 90_000,
                      "description": "+6 % sur les entrées", "entry_bonus": 0.06},
        "sound":     {"name": "Sono haut de gamme",   "emoji": "🔊", "cost": 150_000,
                      "description": "+6 % sur le bar et les entrées", "bar_bonus": 0.06, "entry_bonus": 0.06},
        "security":  {"name": "Sécurité renforcée",   "emoji": "🕴️", "cost": 110_000,
                      "description": "+5 % sur les dépenses VIP", "vip_bonus": 0.05},
        "vip_room":  {"name": "Carré VIP privé",      "emoji": "♛", "cost": 250_000,
                      "description": "+12 % sur les dépenses VIP", "vip_bonus": 0.12},
        "bar_staff": {"name": "Barmans premium",      "emoji": "🍸", "cost": 95_000,
                      "description": "+8 % sur le bar", "bar_bonus": 0.08},
        "decor":     {"name": "Décoration luxe",      "emoji": "🖤", "cost": 180_000,
                      "description": "+5 % sur les entrées et le bar", "entry_bonus": 0.05, "bar_bonus": 0.05},
    },

    # ---------------- Showcases ----------------
    "artists": {**{name: {"bonus": bonus} for name, bonus in ARTIST_SHOWCASE_BONUS.items()},
                **RAP_ARTISTS},
    "artist_order": list(ARTIST_ORDER) + [name for name in RAP_ARTISTS if name not in ARTIST_ORDER],
    "artist_default_bonus": 0.20,
    # showcase_cost_for_artist : paliers [bonus_min, prix] puis prix plancher
    "showcase_cost_tiers": [[0.50, 25_000], [0.40, 22_500], [0.30, 20_000], [0.20, 17_500]],
    "showcase_cost_floor": 15_000,
    "artist_cooldown_services": 2,      # un même artiste : 2 services complets
    "showcase_clients_mult": 2,         # "Tous les showcases rapportent x2 clients"
    "showcase_income_mult": 2,          # "Tous les services avec showcase rapportent x2 d'argent"
    "showcase_phrases": {**SHOWCASE_PHRASES, **RAP_PHRASES},
    "showcase_default_phrase": ["{artist} a mis une grosse ambiance pendant son showcase.", 20, 60],

    # Événements spéciaux de showcase
    "special_showcases": {
        "boro_saisai": {
            "artist": "Boro 700", "chance": 0.60, "clients": [80, 160],
            "clients_mult": 2, "entry_mult": 1.20, "bar_mult": 1.15, "vip_bonus": 1,
            "text": ("Boro 700 a pacté avec la boîte : Saisai débarque par surprise "
                     "et transforme la soirée en double showcase. La salle devient incontrôlable."),
            "suffix": " 🔥 Double showcase : clients x2, entrées boostées, bar en feu et un VIP supplémentaire.",
        },
        "bello_negative": {
            "artist": "Bello&Dallas", "chance": 0.15, "clients": [30, 90],
            "text": ("Bello a frappé un client car il a snappé son ventre. "
                     "La sécurité a calmé la situation et une partie du public est partie."),
        },
        "bello_positive": {
            "artist": "Bello&Dallas", "chance": 0.15, "clients": [60, 140],
            "text": ("Bello a sorti son ventre en plein showcase, toute la salle a rigolé "
                     "et les vidéos ont ramené encore plus de monde."),
        },
    },

    # ---------------- Combos secrets ----------------
    "combos": {
        "coca_lagui": {
            "name": "Coca Cherry × Lagui", "artist": "Lagui", "requires": "coca_cherry_pending",
            "clients_mult": 2, "entry_mult": 1.25, "bar_mult": 1.20, "vip_bonus": 2,
            "suffix": (" 🔥 Coca Cherry rejoint Lagui : la salle explose, "
                       "le bonus de clients est doublé, le bar et les entrées sont boostés."),
            "hint": "Une certaine boisson et un certain artiste, le même soir…",
        },
        "boro_saisai": {
            "name": "Boro 700 × Saisai", "artist": "Boro 700", "requires": None,
            "hint": "Certains artistes viennent accompagnés…",
        },
    },

    # ---------------- Événements spéciaux (process_random_event) ----------------
    "events": {
        "police":     {"title": "🚨 Contrôle de police", "loss": 5_000,
                       "text": "Un mineur a été contrôlé dans l'établissement. Amende et frais : -{loss}."},
        "fight":      {"title": "🥊 Bagarre dans la salle", "loss": 1_000,
                       "text": "Quelques dégâts à réparer : -{loss}."},
        "road":       {"title": "🚧 Route bloquée", "client_penalty": 50,
                       "text": "La rue devant la boîte est bloquée. Jusqu'à 50 clients peuvent manquer au prochain service."},
        "power":      {"title": "⚡ Coupure de courant", "bar_mult": 0.50,
                       "text": "Les machines du bar ont été ralenties. Le prochain service du bar rapporte 50 % de moins."},
        "influencer": {"title": "📸 Influenceur en vue", "client_bonus": 25,
                       "text": "Un influenceur a posté la soirée. Environ +25 clients au prochain service."},
        "vip_party":  {"title": "♛ Table VIP surprise", "vip_mult": 1.50,
                       "text": "Une grosse table VIP réserve au dernier moment. Les dépenses VIP du prochain service sont +50 %."},
    },

    # ---------------- Événements fun (process_fun_event) ----------------
    "fun_events": [
        {"title": "💌 Numéro récupéré", "clients": [4, 12],
         "text": "Une femme vous a dragué toute la soirée. Vous repartez avec son numéro et un sourire de patron."},
        {"title": "⚽ Visite surprise", "clients": [35, 70],
         "text": "Kylian Mbappé est passé danser quelques minutes dans la boîte. Les téléphones sont sortis instantanément."},
        {"title": "🍑 Soirée mouvementée", "clients": [8, 20],
         "text": "Des danseuses ont twerké près de votre table toute la soirée. Votre moitié l'a appris avant même votre retour à la maison."},
        {"title": "🕺 Videur en roue libre", "clients": [10, 25],
         "text": "Le videur a quitté l'entrée trente secondes pour danser au milieu de la piste. La vidéo tourne déjà dans le serveur."},
        {"title": "🎧 Mauvais bouton", "clients": [5, 18],
         "text": "Le DJ a coupé la musique par erreur en plein refrain. Toute la salle a continué le morceau a cappella."},
        {"title": "📱 Téléphone retrouvé", "clients": [3, 10],
         "text": "Un client avait perdu son téléphone dans le carré VIP. Il l'a retrouvé dans le seau à glaçons et a quand même continué la soirée."},
        {"title": "🥂 Bouteille au plafond", "clients": [4, 14],
         "text": "Un serveur a failli envoyer une bouteille au plafond en ouvrant le carré. Personne n'a compris, tout le monde a applaudi."},
        {"title": "🪩 Roi de la piste", "clients": [12, 30],
         "text": "Un inconnu a lancé une battle de danse au milieu de la piste. Même la sécurité s'est arrêtée pour regarder."},
        {"title": "👠 Talon perdu", "clients": [3, 12],
         "text": "Une cliente a perdu un talon en dansant, l'a ramassé et a continué comme si de rien n'était."},
        {"title": "🍟 After improbable", "clients": [6, 16],
         "text": "À la fermeture, la moitié du carré VIP s'est retrouvée à manger des frites devant la boîte."},
    ],

    # ---------------- Activités ----------------
    "activities": {
        "blackjack": {
            "name": "Blackjack", "emoji": "🃏",
            "bets": [1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
            "min_bet": 1_000, "max_bet": 1_000_000,
            "cards": [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11],
            "player_stand_at": 16,     # bot : le joueur tire jusqu'à 16
            "dealer_stand_at": 17,     # bot : la banque tire jusqu'à 17
        },
        "drink": {"name": "Boire un verre", "emoji": "🥃", "cost": 250,
                  "drunk_chance": 0.50, "penalty": 8, "bonus": 4},
        "promo": {"name": "Promo express", "emoji": "📢", "cost": 2_500, "bonus": 12},
        "influencer": {"name": "Inviter un influenceur", "emoji": "📸", "cost": 5_000,
                       "chance": 0.60, "bonus": 30},
        "coca_cherry": {"name": "Coca Cherry", "emoji": "🍒", "cost": 7_500, "bonus": 40},
    },

    # ---------------- Packs de bouteilles (BOTTLE_PACKS) ----------------
    "bottle_packs": {
        "vodka":     {"name": "Pack Vodka",     "emoji": "🍾", "cost": 3_000,  "receiver_bonus": 2_000,
                      "description": "Petit pack pour faire plaisir à une autre boîte."},
        "belvedere": {"name": "Pack Belvedere", "emoji": "🥂", "cost": 7_500,  "receiver_bonus": 5_000,
                      "description": "Le classique du carré VIP."},
        "premium":   {"name": "Pack Premium",   "emoji": "🍾", "cost": 15_000, "receiver_bonus": 10_000,
                      "description": "Un vrai envoi de patron."},
        "magnum":    {"name": "Pack Magnum",    "emoji": "👑", "cost": 30_000, "receiver_bonus": 20_000,
                      "description": "Le gros pack qui fait parler toute la nuit."},
    },
    # clients offerts au destinataire : max(5, receiver_bonus / 500)
    "bottle_clients_min": 5,
    "bottle_clients_divisor": 500,

    # ---------------- Braquage ----------------
    "robbery": {
        "cooldown_services": 4,
        "steal_rate": 0.25,          # 25 % de la trésorerie adverse
        "fail_loss_rate": 0.25,      # 25 % de sa propre trésorerie
        "base_chance": 50,
        "level_power": 4,            # +4 par niveau
        "equipment_power": 1,        # +1 par équipement
        "min_chance": 20,
        "max_chance": 80,
        "success_attacker_clients": [25, 70],
        "success_victim_penalty": [20, 60],
        "fail_attacker_penalty": [25, 70],
        "fail_victim_clients": [20, 60],
    },

    # ---------------- Boutique (flex.py) ----------------
    "shop": {
        "resale_rate": 0.75,
        "bitcoin_price": 65_000,
        "bitcoin_max_per_op": 1_000_000,
        "cars": {
            "audi_rs3":    {"name": "Audi RS3",               "price": 30_000},
            "bmw_m5":      {"name": "BMW M5",                 "price": 50_000},
            "audi_rs6":    {"name": "Audi RS6",               "price": 75_000},
            "porsche_911": {"name": "Porsche 911",            "price": 150_000},
            "class_g":     {"name": "Class G",                "price": 250_000},
            "urus":        {"name": "Lamborghini URUS",       "price": 350_000},
            "svj":         {"name": "Lamborghini SVJ",        "price": 500_000},
            "laferrari":   {"name": "LaFerrari",              "price": 1_000_000},
            "centenario":  {"name": "Lamborghini Centenario", "price": 2_000_000},
        },
        "watches": {
            "day_date":     {"name": "Rolex Day-Date",        "price": 50_000},
            "daytona":      {"name": "Rolex Daytona",         "price": 150_000},
            "ap_royal":     {"name": "Audemars Piguet Royal", "price": 250_000},
            "gmt_master":   {"name": "Rolex GMT-Master",      "price": 500_000},
            "patek_grand":  {"name": "Patek Philippe Grand",  "price": 1_000_000},
            "rolex_olivia": {"name": "Rolex Olivia",          "price": 5_000_000},
        },
    },

    # ---------------- Audio (système web, n'influence jamais le gameplay) ----------------
    "audio": {
        # Tant qu'un dossier d'artiste est vide, utiliser showcases/_placeholder
        "showcase_fallback_placeholder": True,
        # Volume de l'ambiance pendant un extrait de showcase (0.35 = -65 %)
        "ambient_ducking": 0.35,
        # Pause (secondes, min/max) entre deux extraits tant que le showcase est actif
        "showcase_clip_gap": [4, 9],
        # Anti-spam FX braquage : au plus fx_spam_max sons par fx_spam_window secondes,
        # volumes décroissants, écart minimal entre deux sons
        "fx_spam_window": 10,
        "fx_spam_max": 3,
        "fx_spam_volumes": [1.0, 0.7, 0.5],
        "fx_min_gap": 1.2,
        "fade_seconds": 0.35,
        # Showcases via le lecteur YouTube officiel (IFrame Player API) : extraits de clips
        # officiels joués dans la vue du club. Pas de téléchargement, lecteur visible (règles YouTube).
        "youtube_enabled": True,
        "showcase_videos": DEFAULT_VIDEOS,
        "youtube_clip_seconds": 30,          # durée d'un extrait (0 = vidéo entière)
        "youtube_start_range": [20, 75],     # départ aléatoire dans la vidéo (secondes)
        # Préférences par défaut d'un nouveau joueur (0..1)
        "default_prefs": {"master": 0.8, "fx": 0.9, "showcase": 0.7, "ambient": 0.2,
                          "notifications": 0.6, "muted": False},
    },

    # ---------------- Améliorations WEB (séparées du jeu original) ----------------
    "web": {
        # "interactive" : vraie table (tirer / rester), mêmes cartes, mêmes gains.
        # "auto"        : exactement l'algorithme du bot (main jouée automatiquement).
        "blackjack_mode": "interactive",
        # Nombre d'actualités conservées dans le flux "Actualités de la nuit"
        "feed_limit": 60,
        # Notifications conservées par joueur
        "notifications_limit": 300,
        # Statuts de club (ratio d'occupation = (clients - min) / (max - min))
        "status_thresholds": {"full": 0.90, "very_active": 0.60, "quiet": 0.25},
        "event_active_seconds": 600,
    },
}


def deep_merge(base, override):
    """Fusion récursive : override écrase base sans casser la structure."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return copy.deepcopy(override)
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def build_config(overrides=None):
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if overrides:
        cfg = deep_merge(cfg, overrides)
    # Un ancien ordre sauvegardé par l'admin ne doit pas masquer les ajouts.
    cfg["artist_order"] = list(dict.fromkeys(
        [a for a in cfg["artist_order"] if a in cfg["artists"]] + list(cfg["artists"])
    ))
    return cfg


# Clés envoyées au client (tout ce qui sert à l'affichage ; rien de secret).
PUBLIC_KEYS = [
    "tick_seconds", "event_interval", "event_chance", "fun_event_chance",
    "bar_min", "bar_max", "vip_base_spend", "default_entry_price", "club_name_max",
    "vip_roll", "levels", "entry_price_effect", "managers", "equipment",
    "artists", "artist_order", "artist_default_bonus", "showcase_cost_tiers",
    "showcase_cost_floor", "artist_cooldown_services", "showcase_clients_mult",
    "showcase_income_mult", "showcase_phrases", "showcase_default_phrase", "events", "activities",
    "bottle_packs", "bottle_clients_min", "bottle_clients_divisor", "robbery",
    "shop", "web", "audio",
]


def public_config(cfg):
    out = {k: cfg[k] for k in PUBLIC_KEYS if k in cfg}
    # Les combos ne sont révélés que par leur indice (découverte progressive).
    out["combo_hints"] = [
        {"id": cid, "hint": c.get("hint", "")} for cid, c in cfg.get("combos", {}).items()
    ]
    return out
