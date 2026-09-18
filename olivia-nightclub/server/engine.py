"""
Moteur de jeu — port fidèle des mécaniques du bot Discord (nightclub_v35).

Toutes les fonctions sont pures vis-à-vis de la base : elles reçoivent
la configuration (cfg), l'état d'un club (dict, même structure que
nightclub_data.json du bot) et un générateur aléatoire.

Correspondance bot → moteur :
  process_ticks                → process_ticks
  process_random_event         → process_random_event
  process_fun_event            → process_fun_event
  manager_service_effects      → manager_service_effects
  generate_showcase_event      → generate_showcase_event
  entry_price_client_multiplier→ entry_price_client_multiplier
  robbery_*                    → robbery_power / robbery_success_chance / perform_robbery
  Blackjack (BlackjackBetSelect) → blackjack_auto (original) / blackjack_* (interactif)
  Activités (ActivitiesView)   → activity_*
  Boutique (ItemActionView…)   → shop_*
  Transferts / bouteilles      → transfer_money / send_bottle_pack
"""

import random
import time

# ------------------------------------------------------------------
# Helpers de configuration
# ------------------------------------------------------------------

def level_info(cfg, level):
    levels = cfg["levels"]
    level = max(0, min(int(level), len(levels) - 1))
    return levels[level]


def max_level(cfg):
    return len(cfg["levels"]) - 1


def level_name(cfg, level):
    return level_info(cfg, level)["name"]


def income_multiplier(cfg, level):
    return float(level_info(cfg, level)["income_mult"])


def showcase_multiplier(cfg, level):
    return float(level_info(cfg, level)["showcase_mult"])


def max_entry_price(cfg, level):
    return float(level_info(cfg, level)["max_entry"])


def client_range_for_level(cfg, level):
    info = level_info(cfg, level)
    return int(info["clients_min"]), int(info["clients_max"])


def upgrade_cost(cfg, target_level):
    return int(level_info(cfg, target_level)["upgrade_cost"])


def entry_price_client_multiplier(cfg, level, entry_price):
    """0 € => +6 %, moitié du max => neutre, max => -6 %."""
    minimum = 0.0
    maximum = float(max_entry_price(cfg, level))
    if maximum <= minimum:
        return 1.0
    price = max(minimum, min(float(entry_price), maximum))
    ratio = (price - minimum) / (maximum - minimum)
    eff = cfg["entry_price_effect"]
    return (1.0 + float(eff["max_bonus"])) - (float(eff["span"]) * ratio)


def artist_bonus(cfg, artist):
    return float(cfg["artists"].get(artist, {}).get("bonus", cfg["artist_default_bonus"]))


def showcase_cost_for_artist(cfg, artist):
    price = cfg["artists"].get(artist, {}).get("cost")
    if price is not None:
        return int(price)
    bonus = artist_bonus(cfg, artist)
    for threshold, price in cfg["showcase_cost_tiers"]:
        if bonus >= float(threshold):
            return int(price)
    return int(cfg["showcase_cost_floor"])


def artist_cooldown_remaining(cfg, club, artist):
    history = club.get("artist_last_service", {}) or {}
    last_service = history.get(artist)
    if last_service is None:
        return 0
    current = int(club.get("service_count", 0))
    elapsed = current - int(last_service)
    return max(0, int(cfg["artist_cooldown_services"]) - elapsed)


def artist_is_available(cfg, club, artist):
    return artist_cooldown_remaining(cfg, club, artist) <= 0


def get_manager(cfg, club):
    manager_id = club.get("manager_id")
    if not manager_id:
        return None
    manager = cfg["managers"].get(manager_id)
    if manager is None:
        return None
    return dict(manager, id=manager_id)


def equipment_bonus(cfg, club, bonus_key):
    total = 0.0
    for item_id in club.get("equipment", []) or []:
        item = cfg["equipment"].get(item_id, {})
        total += float(item.get(bonus_key, 0.0))
    return total


def net_worth(cfg, club):
    shop = cfg["shop"]
    total = int(club.get("cash", 0))
    for item_id in club.get("cars", []) or []:
        total += int(shop["cars"].get(item_id, {}).get("price", 0))
    for item_id in club.get("watches", []) or []:
        total += int(shop["watches"].get(item_id, {}).get("price", 0))
    total += int(club.get("bitcoin", 0)) * int(shop["bitcoin_price"])
    return total


def new_club(cfg, name, now=None):
    now = time.time() if now is None else now
    return {
        "name": str(name)[: int(cfg["club_name_max"])],
        "cash": int(cfg["starting_cash"]),
        "entry_price": cfg["default_entry_price"],
        "level": 0,
        "last_tick": now,
        "total_bar": 0,
        "total_entry": 0,
        "total_vip": 0,
        "total_vip_clients": 0,
        "total_clients": 0,
        "last_clients": 0,
        "last_vips": 0,
        "last_income": 0,
        "showcase_artist": None,
        "showcase_pending": False,
        "showcase_bonus": 0.0,
        "showcases_done": 0,
        "last_showcase_event": None,
        "artist_last_service": {},
        "equipment": [],
        "last_event_check": now,
        "last_event": None,
        "last_fun_event": None,
        "client_penalty_next": 0,
        "client_bonus_next": 0,
        "coca_cherry_pending": False,
        "bar_mult_next": 1.0,
        "entry_mult_next": 1.0,
        "vip_mult_next": 1.0,
        "blackjack_wins": 0,
        "blackjack_losses": 0,
        "drinks_taken": 0,
        "manager_id": None,
        "manager_last_showcase_tick": -999999,
        "last_robbery_service": -999999,
        "service_count": 0,
        "cars": [],
        "watches": [],
        "bitcoin": 0,
        # Champs web (n'existent pas dans le bot, ignorés par lui)
        "created_at": now,
        "blackjack_game": None,
        "combos_discovered": [],
    }


def ensure_club_fields(cfg, club):
    """Complète un club importé du bot avec les champs manquants."""
    template = new_club(cfg, club.get("name", "Sans nom"), club.get("last_tick", time.time()))
    for key, value in template.items():
        club.setdefault(key, value)
    return club


# ------------------------------------------------------------------
# Manager
# ------------------------------------------------------------------

def manager_service_effects(cfg, club, rng):
    manager = get_manager(cfg, club)
    empty = {"paid": 0, "clients": 0, "vip_bonus": 0, "showcase_started": False,
             "showcase_artist": None, "unpaid": False}
    if not manager:
        return empty

    salary = int(manager["salary"])
    cash = int(club.get("cash", 0))
    if cash < salary:
        # Pas assez pour le salaire : aucun effet, mais pas viré.
        return dict(empty, unpaid=True)

    club["cash"] = cash - salary

    low, high = manager["client_bonus"]
    clients_added = rng.randint(int(low), int(high))
    vip_bonus = 1 if rng.random() < float(manager["vip_chance"]) else 0

    showcase_started = False
    showcase_artist = None
    current_tick = int(club.get("service_count", 0))
    last_tick = int(club.get("manager_last_showcase_tick", -999999))
    cooldown = int(manager["showcase_cooldown_ticks"])
    can_showcase = (current_tick - last_tick) >= cooldown

    if can_showcase and not club.get("showcase_pending") and rng.random() < float(manager["showcase_chance"]):
        available = [a for a in cfg["artist_order"] if artist_is_available(cfg, club, a)]
        if available:
            showcase_artist = rng.choice(available)
            club["showcase_artist"] = showcase_artist
            club["showcase_pending"] = True
            club["showcase_bonus"] = artist_bonus(cfg, showcase_artist)
            club["showcases_done"] = int(club.get("showcases_done", 0)) + 1
            club["manager_last_showcase_tick"] = current_tick
            showcase_started = True

    return {"paid": salary, "clients": clients_added, "vip_bonus": vip_bonus,
            "showcase_started": showcase_started, "showcase_artist": showcase_artist,
            "unpaid": False}


# ------------------------------------------------------------------
# VIP / événements
# ------------------------------------------------------------------

def vip_count(cfg, rng):
    roll = rng.random()
    two = float(cfg["vip_roll"]["two"])
    one = float(cfg["vip_roll"]["one"])
    if roll < two:
        return 2
    if roll < two + one:
        return 1
    return 0


def format_money(value):
    value = float(value)
    if value.is_integer():
        return f"{int(value):,}".replace(",", " ") + " €"
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " €"


def process_random_event(cfg, club, now=None, rng=None):
    """Contrôle toutes les 10 min ; 25 % de chance ; au plus un événement par appel."""
    rng = rng or random
    now = time.time() if now is None else now
    interval = int(cfg["event_interval"])
    last_check = float(club.get("last_event_check", now))
    elapsed = now - last_check
    if elapsed < interval:
        return None

    checks = int(elapsed // interval)
    club["last_event_check"] = last_check + checks * interval

    if rng.random() > float(cfg["event_chance"]):
        return None

    events = cfg["events"]
    event_id = rng.choice(list(events.keys()))
    spec = events[event_id]
    cash = int(club.get("cash", 0))
    result = {"id": event_id, "title": spec["title"], "time": now, "cash_delta": 0}

    if "loss" in spec:
        loss = min(int(spec["loss"]), cash)
        club["cash"] = cash - loss
        result["cash_delta"] = -loss
        result["text"] = spec["text"].replace("{loss}", format_money(loss))
    elif "client_penalty" in spec:
        club["client_penalty_next"] = int(club.get("client_penalty_next", 0)) + int(spec["client_penalty"])
        result["text"] = spec["text"]
    elif "bar_mult" in spec:
        club["bar_mult_next"] = min(float(club.get("bar_mult_next", 1.0)), float(spec["bar_mult"]))
        result["text"] = spec["text"]
    elif "client_bonus" in spec:
        club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + int(spec["client_bonus"])
        result["text"] = spec["text"]
    elif "vip_mult" in spec:
        club["vip_mult_next"] = max(float(club.get("vip_mult_next", 1.0)), float(spec["vip_mult"]))
        result["text"] = spec["text"]
    else:
        result["text"] = spec.get("text", "")

    club["last_event"] = {"id": event_id, "title": result["title"], "text": result["text"], "time": now}
    return result


def process_fun_event(cfg, club, rng, now=None):
    """70 % de chance d'un petit événement drôle ; bonus clients au prochain service."""
    if rng.random() > float(cfg["fun_event_chance"]):
        return None
    now = time.time() if now is None else now
    spec = rng.choice(cfg["fun_events"])
    low, high = spec["clients"]
    bonus = rng.randint(int(low), int(high))
    text = spec["text"]
    if bonus:
        club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + bonus
        text += f" +{bonus} clients sur le prochain service."
    event = {"title": spec["title"], "text": text, "clients": bonus, "time": now}
    club["last_fun_event"] = event
    return event


# ------------------------------------------------------------------
# Showcase
# ------------------------------------------------------------------

def generate_showcase_event(cfg, artist, rng):
    specials = cfg["special_showcases"]

    boro = specials.get("boro_saisai")
    if boro and artist == boro["artist"] and rng.random() < float(boro["chance"]):
        low, high = boro["clients"]
        return {"artist": artist, "text": boro["text"], "clients": rng.randint(int(low), int(high)),
                "boro_saisai_combo": True}

    neg = specials.get("bello_negative")
    pos = specials.get("bello_positive")
    if neg and artist == neg["artist"]:
        roll = rng.random()
        if roll < float(neg["chance"]):
            low, high = neg["clients"]
            return {"artist": artist, "text": neg["text"], "clients": -rng.randint(int(low), int(high))}
        if pos and roll < float(neg["chance"]) + float(pos["chance"]):
            low, high = pos["clients"]
            return {"artist": artist, "text": pos["text"], "clients": rng.randint(int(low), int(high))}

    phrases = cfg["showcase_phrases"].get(artist)
    if not phrases:
        tpl, low, high = cfg["showcase_default_phrase"]
        phrases = [[tpl.replace("{artist}", artist), low, high]]
    phrase, low, high = rng.choice(phrases)
    return {"artist": artist, "text": phrase, "clients": rng.randint(int(low), int(high))}


# ------------------------------------------------------------------
# Services (process_ticks)
# ------------------------------------------------------------------

def process_ticks(cfg, club, now=None, rng=None):
    """
    Calcule tous les services écoulés depuis last_tick.
    Retourne la liste des rapports de service (un par service), dans l'ordre.
    """
    rng = rng or random
    now = time.time() if now is None else now
    tick = int(cfg["tick_seconds"])
    last_tick = float(club.get("last_tick", now))
    elapsed = max(0.0, now - last_tick)
    intervals = int(elapsed // tick)
    reports = []
    if intervals <= 0:
        return reports

    for i in range(intervals):
        service_time = last_tick + (i + 1) * tick
        level = int(club.get("level", 0))
        club["service_count"] = int(club.get("service_count", 0)) + 1
        service_no = club["service_count"]

        manager_effect = manager_service_effects(cfg, club, rng)
        mult = income_multiplier(cfg, level)

        # BAR
        bar_base = rng.randint(int(cfg["bar_min"]), int(cfg["bar_max"]))
        bar_income = int(bar_base * mult * (1.0 + equipment_bonus(cfg, club, "bar_bonus"))
                         * float(club.get("bar_mult_next", 1.0)))
        club["bar_mult_next"] = 1.0

        # CLIENTS
        min_clients, max_clients = client_range_for_level(cfg, level)
        base_clients = rng.randint(min_clients, max_clients)
        clients = base_clients
        clients += int(manager_effect.get("clients", 0))
        bonus_next = int(club.get("client_bonus_next", 0))
        penalty_next = int(club.get("client_penalty_next", 0))
        clients += bonus_next
        clients -= penalty_next

        entry_price = max(0.0, float(club.get("entry_price", cfg["default_entry_price"])))
        price_client_mult = entry_price_client_multiplier(cfg, level, entry_price)
        clients = int(round(clients * price_client_mult))
        clients = max(0, clients)

        club["client_bonus_next"] = 0
        club["client_penalty_next"] = 0

        entry_mult = mult * float(club.get("entry_mult_next", 1.0))
        club["entry_mult_next"] = 1.0

        coca_cherry_active = bool(club.get("coca_cherry_pending", False))
        showcase_combo_vip_bonus = 0
        showcase_active = False
        showcase_report = None
        combos_triggered = []

        if club.get("showcase_pending"):
            showcase_active = True
            artist = club.get("showcase_artist") or "Artiste"
            a_bonus = float(club.get("showcase_bonus", 0.0))
            showcase_event = generate_showcase_event(cfg, artist, rng)
            showcase_clients = int(showcase_event.get("clients", 0))
            showcase_clients *= int(cfg["showcase_clients_mult"])
            showcase_text = showcase_event.get("text", "")

            # ÉVÉNEMENT SPÉCIAL BORO 700 + SAISAI
            if showcase_event.get("boro_saisai_combo"):
                spec = cfg["special_showcases"]["boro_saisai"]
                showcase_clients *= int(spec["clients_mult"])
                entry_mult *= float(spec["entry_mult"])
                bar_income = int(bar_income * float(spec["bar_mult"]))
                showcase_combo_vip_bonus += int(spec["vip_bonus"])
                showcase_text += spec["suffix"]
                combos_triggered.append("boro_saisai")

            # COMBO SECRET : Coca Cherry + Lagui sur le même service
            combo = cfg["combos"].get("coca_lagui")
            if combo and artist == combo["artist"] and coca_cherry_active:
                showcase_clients *= int(combo["clients_mult"])
                entry_mult *= float(combo["entry_mult"])
                bar_income = int(bar_income * float(combo["bar_mult"]))
                showcase_combo_vip_bonus = int(combo["vip_bonus"])
                showcase_text += combo["suffix"]
                combos_triggered.append("coca_lagui")

            clients += showcase_clients
            clients = max(0, clients)

            club["last_showcase_event"] = {"artist": artist, "text": showcase_text,
                                           "clients": showcase_clients, "time": service_time}
            history = club.setdefault("artist_last_service", {})
            history[artist] = int(club.get("service_count", 0))

            entry_mult *= (1.0 + a_bonus)
            entry_mult *= showcase_multiplier(cfg, level)

            club["showcase_pending"] = False
            club["showcase_bonus"] = 0.0
            showcase_report = {"artist": artist, "text": showcase_text, "clients": showcase_clients,
                               "bonus": a_bonus}

        entry_income = int(clients * entry_price * entry_mult * (1.0 + equipment_bonus(cfg, club, "entry_bonus")))

        club["coca_cherry_pending"] = False

        # VIP
        vips = vip_count(cfg, rng)
        vips += int(manager_effect.get("vip_bonus", 0))
        vips += showcase_combo_vip_bonus
        vip_income = int(vips * int(cfg["vip_base_spend"]) * mult
                         * (1.0 + equipment_bonus(cfg, club, "vip_bonus"))
                         * float(club.get("vip_mult_next", 1.0)))
        club["vip_mult_next"] = 1.0

        total = bar_income + entry_income + vip_income
        if showcase_active:
            k = int(cfg["showcase_income_mult"])
            total *= k
            bar_income *= k
            entry_income *= k
            vip_income *= k

        club["cash"] = int(club.get("cash", 0)) + total
        club["total_bar"] = int(club.get("total_bar", 0)) + bar_income
        club["total_entry"] = int(club.get("total_entry", 0)) + entry_income
        club["total_vip"] = int(club.get("total_vip", 0)) + vip_income
        club["total_vip_clients"] = int(club.get("total_vip_clients", 0)) + vips
        club["total_clients"] = int(club.get("total_clients", 0)) + clients
        club["last_clients"] = clients
        club["last_vips"] = vips
        club["last_income"] = total

        if combos_triggered:
            discovered = club.setdefault("combos_discovered", [])
            for cid in combos_triggered:
                if cid not in discovered:
                    discovered.append(cid)

        fun_event = process_fun_event(cfg, club, rng, service_time)

        reports.append({
            "service_no": service_no,
            "time": service_time,
            "level": level,
            "clients": clients,
            "base_clients": base_clients,
            "bonus_clients": bonus_next,
            "penalty_clients": penalty_next,
            "vips": vips,
            "bar": bar_income,
            "entry": entry_income,
            "vip": vip_income,
            "total": total,
            "salary": int(manager_effect.get("paid", 0)),
            "manager_unpaid": bool(manager_effect.get("unpaid")),
            "manager_clients": int(manager_effect.get("clients", 0)),
            "manager_showcase": manager_effect.get("showcase_artist"),
            "showcase": showcase_report,
            "combos": combos_triggered,
            "fun_event": fun_event,
            "cash_after": int(club["cash"]),
        })

    club["last_tick"] = last_tick + intervals * tick
    return reports


def next_service_time(cfg, club):
    return float(club.get("last_tick", time.time())) + int(cfg["tick_seconds"])


# ------------------------------------------------------------------
# Estimation (pour l'UI "impact estimé" — déterministe, valeurs moyennes)
# ------------------------------------------------------------------

def estimate_service(cfg, club, entry_price=None, level=None):
    level = int(club.get("level", 0)) if level is None else int(level)
    price = float(club.get("entry_price", cfg["default_entry_price"])) if entry_price is None else float(entry_price)
    mult = income_multiplier(cfg, level)
    cmin, cmax = client_range_for_level(cfg, level)
    manager = get_manager(cfg, club)
    m_clients = 0.0
    m_vip = 0.0
    salary = 0
    if manager:
        m_clients = (manager["client_bonus"][0] + manager["client_bonus"][1]) / 2.0
        m_vip = float(manager["vip_chance"])
        salary = int(manager["salary"])
    price_mult = entry_price_client_multiplier(cfg, level, price)
    clients = ((cmin + cmax) / 2.0 + m_clients) * price_mult
    bar = (cfg["bar_min"] + cfg["bar_max"]) / 2.0 * mult * (1.0 + equipment_bonus(cfg, club, "bar_bonus"))
    entry = clients * price * mult * (1.0 + equipment_bonus(cfg, club, "entry_bonus"))
    two = float(cfg["vip_roll"]["two"])
    one = float(cfg["vip_roll"]["one"])
    vips = 2 * two + 1 * one + m_vip
    vip = vips * cfg["vip_base_spend"] * mult * (1.0 + equipment_bonus(cfg, club, "vip_bonus"))
    return {
        "clients": int(round(clients)),
        "clients_min": int(round(cmin * price_mult)),
        "clients_max": int(round(cmax * price_mult)),
        "price_mult": price_mult,
        "bar": int(bar), "entry": int(entry), "vip": int(vip),
        "vips": round(vips, 2),
        "total": int(bar + entry + vip),
        "salary": salary,
        "net": int(bar + entry + vip) - salary,
    }


def club_status(cfg, club, now=None):
    now = time.time() if now is None else now
    web = cfg["web"]
    if club.get("showcase_pending"):
        return "SHOWCASE EN COURS"
    last_event = club.get("last_event") or {}
    if last_event and now - float(last_event.get("time", 0)) < int(web["event_active_seconds"]):
        return "ÉVÉNEMENT EN COURS"
    cmin, cmax = client_range_for_level(cfg, int(club.get("level", 0)))
    last = int(club.get("last_clients", 0))
    if last <= 0 and int(club.get("service_count", 0)) == 0:
        return "OUVERT"
    ratio = (last - cmin) / float(max(1, cmax - cmin))
    th = web["status_thresholds"]
    if ratio >= float(th["full"]):
        return "COMPLET"
    if ratio >= float(th["very_active"]):
        return "TRÈS ACTIF"
    if ratio < float(th["quiet"]):
        return "CALME"
    return "OUVERT"


def occupancy(cfg, club):
    cmin, cmax = client_range_for_level(cfg, int(club.get("level", 0)))
    last = int(club.get("last_clients", 0))
    return max(0.0, min(1.5, last / float(max(1, cmax))))


# ------------------------------------------------------------------
# Actions joueur — chaque fonction retourne (ok: bool, code: str, payload: dict)
# ------------------------------------------------------------------

def set_entry_price(cfg, club, price):
    try:
        price = float(str(price).replace(",", "."))
    except (TypeError, ValueError):
        return False, "INVALID", {}
    maximum = max_entry_price(cfg, int(club.get("level", 0)))
    if price < 0 or price > maximum:
        return False, "MAX", {"max": maximum}
    price = round(price, 2)
    old = float(club.get("entry_price", cfg["default_entry_price"]))
    club["entry_price"] = price
    return True, "OK", {"old": old, "new": price}


def rename_club(cfg, club, name):
    name = str(name or "").strip()
    if len(name) < 2:
        return False, "INVALID", {}
    club["name"] = name[: int(cfg["club_name_max"])]
    return True, "OK", {"name": club["name"]}


def upgrade_level(cfg, club):
    current = int(club.get("level", 0))
    if current >= max_level(cfg):
        return False, "MAX", {}
    target = current + 1
    cost = upgrade_cost(cfg, target)
    if int(club.get("cash", 0)) < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = int(club.get("cash", 0)) - cost
    club["level"] = target
    return True, "OK", {"level": target, "cost": cost, "name": level_name(cfg, target)}


def buy_equipment(cfg, club, item_id):
    item = cfg["equipment"].get(item_id)
    if not item:
        return False, "UNKNOWN", {}
    owned = club.setdefault("equipment", [])
    if item_id in owned:
        return False, "OWNED", {}
    cost = int(item["cost"])
    if int(club.get("cash", 0)) < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = int(club.get("cash", 0)) - cost
    owned.append(item_id)
    return True, "OK", {"item": dict(item, id=item_id), "cost": cost}


def hire_manager(cfg, club, manager_id):
    manager = cfg["managers"].get(manager_id)
    if not manager:
        return False, "UNKNOWN", {}
    previous = club.get("manager_id")
    club["manager_id"] = manager_id
    return True, "OK", {"manager": dict(manager, id=manager_id), "previous": previous}


def fire_manager(cfg, club):
    if not club.get("manager_id"):
        return False, "NONE", {}
    previous = club.get("manager_id")
    club["manager_id"] = None
    return True, "OK", {"previous": previous}


def book_showcase(cfg, club, artist):
    if artist not in cfg["artists"]:
        return False, "UNKNOWN", {}
    if club.get("showcase_pending"):
        return False, "ALREADY", {"artist": club.get("showcase_artist")}
    remaining = artist_cooldown_remaining(cfg, club, artist)
    if remaining > 0:
        return False, "COOLDOWN", {"remaining": remaining}
    cost = showcase_cost_for_artist(cfg, artist)
    if int(club.get("cash", 0)) < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = int(club.get("cash", 0)) - cost
    club["showcase_artist"] = artist
    club["showcase_pending"] = True
    club["showcase_bonus"] = artist_bonus(cfg, artist)
    club["showcases_done"] = int(club.get("showcases_done", 0)) + 1
    return True, "OK", {"artist": artist, "cost": cost, "bonus": club["showcase_bonus"]}


# ---------------- Activités ----------------

def activity_drink(cfg, club, rng):
    spec = cfg["activities"]["drink"]
    cost = int(spec["cost"])
    cash = int(club.get("cash", 0))
    if cash < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = cash - cost
    club["drinks_taken"] = int(club.get("drinks_taken", 0)) + 1
    if rng.random() < float(spec["drunk_chance"]):
        club["client_penalty_next"] = int(club.get("client_penalty_next", 0)) + int(spec["penalty"])
        return True, "DRUNK", {"cost": cost, "clients": -int(spec["penalty"])}
    club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + int(spec["bonus"])
    return True, "GOOD", {"cost": cost, "clients": int(spec["bonus"])}


def activity_promo(cfg, club, rng):
    spec = cfg["activities"]["promo"]
    cost = int(spec["cost"])
    cash = int(club.get("cash", 0))
    if cash < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = cash - cost
    club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + int(spec["bonus"])
    return True, "OK", {"cost": cost, "clients": int(spec["bonus"])}


def activity_influencer(cfg, club, rng):
    spec = cfg["activities"]["influencer"]
    cost = int(spec["cost"])
    cash = int(club.get("cash", 0))
    if cash < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = cash - cost
    if rng.random() < float(spec["chance"]):
        club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + int(spec["bonus"])
        return True, "WIN", {"cost": cost, "clients": int(spec["bonus"])}
    return True, "MISS", {"cost": cost, "clients": 0}


def activity_coca_cherry(cfg, club, rng):
    spec = cfg["activities"]["coca_cherry"]
    cost = int(spec["cost"])
    cash = int(club.get("cash", 0))
    if cash < cost:
        return False, "NO_MONEY", {"cost": cost}
    club["cash"] = cash - cost
    club["client_bonus_next"] = int(club.get("client_bonus_next", 0)) + int(spec["bonus"])
    club["coca_cherry_pending"] = True
    return True, "OK", {"cost": cost, "clients": int(spec["bonus"])}


# ---------------- Blackjack ----------------

SUITS = ["♠", "♥", "♦", "♣"]


def _draw_value(cfg, rng):
    return rng.choice(list(cfg["activities"]["blackjack"]["cards"]))


def _make_card(cfg, rng):
    value = _draw_value(cfg, rng)
    if value == 11:
        rank = "A"
    elif value == 10:
        rank = rng.choice(["10", "J", "Q", "K"])
    else:
        rank = str(value)
    return {"value": value, "rank": rank, "suit": rng.choice(SUITS)}


def _hand_total(cards):
    """Total avec gestion correcte des As (11 → 1 tant que ça dépasse 21)."""
    total = sum(c["value"] for c in cards)
    aces = sum(1 for c in cards if c["value"] == 11)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def blackjack_auto(cfg, club, bet, rng):
    """Algorithme ORIGINAL du bot : main automatique, ajustement simplifié des As."""
    spec = cfg["activities"]["blackjack"]
    bet = int(bet)
    if bet not in [int(b) for b in spec["bets"]]:
        return False, "INVALID_BET", {}
    cash = int(club.get("cash", 0))
    if cash < bet:
        return False, "NO_MONEY", {"cost": bet}

    player_cards = [_make_card(cfg, rng), _make_card(cfg, rng)]
    player = player_cards[0]["value"] + player_cards[1]["value"]
    if player > 21:
        player -= 10
    while player < int(spec["player_stand_at"]):
        card = _make_card(cfg, rng)
        player_cards.append(card)
        player += card["value"]
        if player > 21:
            player -= 10

    dealer_cards = []
    dealer = 0
    while dealer < int(spec["dealer_stand_at"]):
        card = _make_card(cfg, rng)
        dealer_cards.append(card)
        dealer += card["value"]
        if dealer > 21:
            dealer -= 10

    if player > 21:
        result = "LOSE"
    elif dealer > 21 or player > dealer:
        result = "WIN"
    elif player == dealer:
        result = "PUSH"
    else:
        result = "LOSE"

    delta = _apply_blackjack_result(club, result, bet, cash)
    return True, result, {"player": player, "dealer": dealer, "bet": bet, "delta": delta,
                          "player_cards": player_cards, "dealer_cards": dealer_cards, "mode": "auto"}


def _apply_blackjack_result(club, result, bet, cash):
    if result == "WIN":
        club["cash"] = cash + bet
        club["blackjack_wins"] = int(club.get("blackjack_wins", 0)) + 1
        return bet
    if result == "LOSE":
        club["cash"] = cash - bet
        club["blackjack_losses"] = int(club.get("blackjack_losses", 0)) + 1
        return -bet
    return 0


def blackjack_start(cfg, club, bet, rng):
    """Mode interactif (amélioration web) : mêmes cartes, mêmes gains, mais le joueur décide."""
    spec = cfg["activities"]["blackjack"]
    bet = int(bet)
    if bet not in [int(b) for b in spec["bets"]]:
        return False, "INVALID_BET", {}
    if club.get("blackjack_game"):
        return False, "IN_PROGRESS", {"game": public_blackjack(club["blackjack_game"])}
    cash = int(club.get("cash", 0))
    if cash < bet:
        return False, "NO_MONEY", {"cost": bet}
    game = {
        "bet": bet,
        "player": [_make_card(cfg, rng), _make_card(cfg, rng)],
        "dealer": [_make_card(cfg, rng), _make_card(cfg, rng)],
        "status": "PLAYING",
        "started": time.time(),
    }
    # Blackjack naturel : on passe directement à la résolution.
    if _hand_total(game["player"]) == 21:
        club["blackjack_game"] = game
        return blackjack_stand(cfg, club, rng)
    club["blackjack_game"] = game
    return True, "PLAYING", {"game": public_blackjack(game)}


def blackjack_hit(cfg, club, rng):
    game = club.get("blackjack_game")
    if not game or game.get("status") != "PLAYING":
        return False, "NO_GAME", {}
    game["player"].append(_make_card(cfg, rng))
    if _hand_total(game["player"]) > 21:
        return _resolve_blackjack(club, game, "LOSE")
    if _hand_total(game["player"]) == 21:
        return blackjack_stand(cfg, club, rng)
    return True, "PLAYING", {"game": public_blackjack(game)}


def blackjack_stand(cfg, club, rng):
    game = club.get("blackjack_game")
    if not game or game.get("status") != "PLAYING":
        return False, "NO_GAME", {}
    stand_at = int(cfg["activities"]["blackjack"]["dealer_stand_at"])
    while _hand_total(game["dealer"]) < stand_at:
        game["dealer"].append(_make_card(cfg, rng))
    player = _hand_total(game["player"])
    dealer = _hand_total(game["dealer"])
    if player > 21:
        result = "LOSE"
    elif dealer > 21 or player > dealer:
        result = "WIN"
    elif player == dealer:
        result = "PUSH"
    else:
        result = "LOSE"
    return _resolve_blackjack(club, game, result)


def _resolve_blackjack(club, game, result):
    bet = int(game["bet"])
    cash = int(club.get("cash", 0))
    delta = _apply_blackjack_result(club, result, bet, cash)
    game["status"] = result
    club["blackjack_game"] = None
    return True, result, {"player": _hand_total(game["player"]), "dealer": _hand_total(game["dealer"]),
                          "bet": bet, "delta": delta, "player_cards": game["player"],
                          "dealer_cards": game["dealer"], "mode": "interactive",
                          "game": public_blackjack(game, reveal=True)}


def public_blackjack(game, reveal=False):
    if not game:
        return None
    dealer = game["dealer"]
    finished = game.get("status") != "PLAYING" or reveal
    return {
        "bet": game["bet"],
        "status": game["status"],
        "player": game["player"],
        "player_total": _hand_total(game["player"]),
        "dealer": dealer if finished else [dealer[0], {"hidden": True}],
        "dealer_total": _hand_total(dealer) if finished else dealer[0]["value"],
    }


# ---------------- Boutique ----------------

def _shop_items(cfg, category):
    if category not in ("cars", "watches"):
        return None
    return cfg["shop"][category]


def shop_buy(cfg, club, category, item_id):
    items = _shop_items(cfg, category)
    if items is None or item_id not in items:
        return False, "UNKNOWN", {}
    item = items[item_id]
    price = int(item["price"])
    if int(club.get("cash", 0)) < price:
        return False, "NO_MONEY", {"cost": price}
    club["cash"] = int(club.get("cash", 0)) - price
    club.setdefault(category, []).append(item_id)
    return True, "OK", {"item": dict(item, id=item_id), "cost": price, "category": category}


def shop_sell(cfg, club, category, item_id):
    items = _shop_items(cfg, category)
    if items is None or item_id not in items:
        return False, "UNKNOWN", {}
    owned = club.setdefault(category, [])
    if item_id not in owned:
        return False, "NOT_OWNED", {}
    owned.remove(item_id)
    item = items[item_id]
    resale = int(int(item["price"]) * float(cfg["shop"]["resale_rate"]))
    club["cash"] = int(club.get("cash", 0)) + resale
    return True, "OK", {"item": dict(item, id=item_id), "gain": resale, "category": category}


def bitcoin_buy(cfg, club, quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "INVALID", {}
    if quantity <= 0:
        return False, "INVALID", {}
    if quantity > int(cfg["shop"]["bitcoin_max_per_op"]):
        return False, "TOO_MANY", {}
    price = int(cfg["shop"]["bitcoin_price"])
    total = quantity * price
    cash = int(club.get("cash", 0))
    if cash < total:
        return False, "NO_MONEY", {"cost": total}
    club["cash"] = cash - total
    club["bitcoin"] = int(club.get("bitcoin", 0)) + quantity
    return True, "OK", {"quantity": quantity, "cost": total, "unit": price}


def bitcoin_sell(cfg, club, quantity):
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return False, "INVALID", {}
    if quantity <= 0:
        return False, "INVALID", {}
    if quantity > int(cfg["shop"]["bitcoin_max_per_op"]):
        return False, "TOO_MANY", {}
    btc = int(club.get("bitcoin", 0))
    if btc < quantity:
        return False, "NO_BTC", {}
    unit = int(int(cfg["shop"]["bitcoin_price"]) * float(cfg["shop"]["resale_rate"]))
    total = quantity * unit
    club["bitcoin"] = btc - quantity
    club["cash"] = int(club.get("cash", 0)) + total
    return True, "OK", {"quantity": quantity, "gain": total, "unit": unit}


# ---------------- Transferts / bouteilles / trade ----------------

def transfer_money(cfg, sender, target, amount):
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return False, "INVALID", {}
    if amount <= 0:
        return False, "INVALID", {}
    cash = int(sender.get("cash", 0))
    if cash < amount:
        return False, "NO_MONEY", {"cost": amount}
    sender["cash"] = cash - amount
    target["cash"] = int(target.get("cash", 0)) + amount
    return True, "OK", {"amount": amount}


def send_bottle_pack(cfg, sender, receiver, pack_id):
    pack = cfg["bottle_packs"].get(pack_id)
    if not pack:
        return False, "UNKNOWN", {}
    cost = int(pack["cost"])
    if int(sender.get("cash", 0)) < cost:
        return False, "NO_MONEY", {"cost": cost}
    sender["cash"] = int(sender.get("cash", 0)) - cost
    bonus = int(pack["receiver_bonus"])
    receiver["cash"] = int(receiver.get("cash", 0)) + bonus
    clients = max(int(cfg["bottle_clients_min"]), int(bonus / int(cfg["bottle_clients_divisor"])))
    receiver["client_bonus_next"] = int(receiver.get("client_bonus_next", 0)) + clients
    return True, "OK", {"pack": dict(pack, id=pack_id), "cost": cost, "bonus": bonus, "clients": clients}


def trade_check(cfg, sender, trade_type, value):
    """Vérifie que l'expéditeur possède bien ce qu'il propose."""
    if trade_type == "money":
        amount = int(value)
        if amount <= 0:
            return False, "INVALID"
        if int(sender.get("cash", 0)) < amount:
            return False, "NO_MONEY"
        return True, "OK"
    if trade_type == "bitcoin":
        amount = int(value)
        if amount <= 0:
            return False, "INVALID"
        if int(sender.get("bitcoin", 0)) < amount:
            return False, "NO_BTC"
        return True, "OK"
    if trade_type in ("cars", "watches"):
        if str(value) not in (sender.get(trade_type, []) or []):
            return False, "NOT_OWNED"
        return True, "OK"
    return False, "INVALID_TYPE"


def trade_apply(cfg, sender, target, trade_type, value):
    ok, code = trade_check(cfg, sender, trade_type, value)
    if not ok:
        return False, code, {}
    if trade_type == "money":
        amount = int(value)
        sender["cash"] = int(sender.get("cash", 0)) - amount
        target["cash"] = int(target.get("cash", 0)) + amount
        return True, "OK", {"detail": format_money(amount), "amount": amount}
    if trade_type == "bitcoin":
        amount = int(value)
        sender["bitcoin"] = int(sender.get("bitcoin", 0)) - amount
        target["bitcoin"] = int(target.get("bitcoin", 0)) + amount
        return True, "OK", {"detail": f"{amount} BTC", "amount": amount}
    item_id = str(value)
    sender[trade_type].remove(item_id)
    target.setdefault(trade_type, []).append(item_id)
    name = cfg["shop"][trade_type].get(item_id, {"name": item_id})["name"]
    return True, "OK", {"detail": name, "item_id": item_id}


# ---------------- Braquage ----------------

def robbery_power(cfg, club):
    r = cfg["robbery"]
    level = int(club.get("level", 0))
    equipment_count = len(club.get("equipment", []) or [])
    return level * int(r["level_power"]) + equipment_count * int(r["equipment_power"])


def robbery_success_chance(cfg, attacker, defender):
    r = cfg["robbery"]
    chance = int(r["base_chance"]) + robbery_power(cfg, attacker) - robbery_power(cfg, defender)
    return max(int(r["min_chance"]), min(int(r["max_chance"]), chance))


def robbery_cooldown_remaining(cfg, club):
    r = cfg["robbery"]
    current = int(club.get("service_count", 0))
    last = int(club.get("last_robbery_service", -999999))
    since = current - last
    return max(0, int(r["cooldown_services"]) - since)


def perform_robbery(cfg, attacker, victim, rng):
    r = cfg["robbery"]
    remaining = robbery_cooldown_remaining(cfg, attacker)
    if remaining > 0:
        return False, "COOLDOWN", {"remaining": remaining}
    victim_cash = int(victim.get("cash", 0))
    if victim_cash <= 0:
        return False, "NOTHING", {}

    current = int(attacker.get("service_count", 0))
    attacker["last_robbery_service"] = current
    chance = robbery_success_chance(cfg, attacker, victim)

    if rng.random() < chance / 100.0:
        stolen = int(victim_cash * float(r["steal_rate"]))
        victim["cash"] = max(0, victim_cash - stolen)
        attacker["cash"] = int(attacker.get("cash", 0)) + stolen
        gained = rng.randint(*[int(x) for x in r["success_attacker_clients"]])
        lost = rng.randint(*[int(x) for x in r["success_victim_penalty"]])
        attacker["client_bonus_next"] = int(attacker.get("client_bonus_next", 0)) + gained
        victim["client_penalty_next"] = int(victim.get("client_penalty_next", 0)) + lost
        return True, "SUCCESS", {"amount": stolen, "chance": chance,
                                 "attacker_clients": gained, "victim_clients": -lost}

    attacker_cash = int(attacker.get("cash", 0))
    lost_money = int(attacker_cash * float(r["fail_loss_rate"]))
    attacker["cash"] = max(0, attacker_cash - lost_money)
    lost = rng.randint(*[int(x) for x in r["fail_attacker_penalty"]])
    gained = rng.randint(*[int(x) for x in r["fail_victim_clients"]])
    attacker["client_penalty_next"] = int(attacker.get("client_penalty_next", 0)) + lost
    victim["client_bonus_next"] = int(victim.get("client_bonus_next", 0)) + gained
    return True, "FAIL", {"amount": lost_money, "chance": chance,
                          "attacker_clients": -lost, "victim_clients": gained}
