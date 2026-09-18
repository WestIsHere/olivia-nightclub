"""
Tests du moteur (sans serveur). Lancer :  python tests/test_engine.py
Vérifie que les mécaniques du bot sont reproduites avec les bonnes valeurs.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import engine  # noqa: E402
from server.config import build_config  # noqa: E402

cfg = build_config()
rng = random.Random(42)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("  ok —", msg)


print("Niveaux")
check(engine.level_name(cfg, 0) == "Club indépendant", "niveau 0 = Club indépendant")
check(engine.level_name(cfg, 6) == "Le Olivia", "niveau 6 = Le Olivia")
check(engine.upgrade_cost(cfg, 1) == 100_000 and engine.upgrade_cost(cfg, 6) == 10_000_000, "coûts d'amélioration")
check(engine.income_multiplier(cfg, 4) == 1.80, "multiplicateur niveau 4 = 1.80")
check(engine.max_entry_price(cfg, 3) == 43.75, "entrée max niveau 3 = 43,75")
check(engine.client_range_for_level(cfg, 2) == (230, 690), "clients niveau 2 = 230–690")
check(abs(engine.entry_price_client_multiplier(cfg, 0, 0) - 1.06) < 1e-9, "prix 0 € → +6 %")
check(abs(engine.entry_price_client_multiplier(cfg, 0, 25) - 0.94) < 1e-9, "prix max → -6 %")

print("Showcases")
check(engine.showcase_cost_for_artist(cfg, "Lagui") == 25_000, "Lagui = 25 000 €")
check(engine.showcase_cost_for_artist(cfg, "Bello&Dallas") == 15_000, "Bello&Dallas = 15 000 €")
check(engine.showcase_cost_for_artist(cfg, "3robi") == 20_000, "3robi = 20 000 €")
check(cfg["artist_order"][:2] == ["Lagui", "Boro 700"], "ordre des artistes")

print("Club & services")
club = engine.new_club(cfg, "Test Club", now=1000.0)
check(club["cash"] == 0 and club["entry_price"] == 20, "nouveau club : 0 €, entrée 20 €")
reports = engine.process_ticks(cfg, club, now=1000.0 + 180 * 3 + 5, rng=rng)
check(len(reports) == 3, "3 services écoulés")
check(club["service_count"] == 3, "service_count = 3")
check(club["last_tick"] == 1000.0 + 180 * 3, "last_tick avance par pas de 180 s")
check(club["cash"] == sum(r["total"] for r in reports), "trésorerie = somme des services")
for r in reports:
    check(60 <= r["base_clients"] <= 575, f"clients de base dans la plage (service {r['service_no']})")
    check(r["total"] == r["bar"] + r["entry"] + r["vip"], "total = bar + entrées + VIP")

print("Manager")
club["cash"] = 100_000
club["manager_id"] = "olivia"
eff = engine.manager_service_effects(cfg, club, rng)
check(eff["paid"] == 5000 and club["cash"] == 95_000, "salaire Olivia 5 000 € payé")
check(50 <= eff["clients"] <= 120, "bonus clients Olivia 50–120")
club["cash"] = 100
eff = engine.manager_service_effects(cfg, club, rng)
check(eff["paid"] == 0 and eff["unpaid"] and club["cash"] == 100, "salaire impayé → aucun effet, pas viré")
club["manager_id"] = None

print("Prix d'entrée")
club["level"] = 2
ok, code, p = engine.set_entry_price(cfg, club, "37,50")
check(ok and club["entry_price"] == 37.5, "prix 37,50 accepté au niveau 2")
ok, code, p = engine.set_entry_price(cfg, club, 40)
check(not ok and code == "MAX", "prix 40 refusé au niveau 2")

print("Équipements / niveau")
club["cash"] = 1_000_000
ok, code, p = engine.buy_equipment(cfg, club, "sound")
check(ok and club["cash"] == 850_000, "sono 150 000 €")
check(engine.equipment_bonus(cfg, club, "bar_bonus") == 0.06, "bonus bar sono 6 %")
ok, code, p = engine.buy_equipment(cfg, club, "sound")
check(not ok and code == "OWNED", "double achat refusé")
club["level"] = 0
ok, code, p = engine.upgrade_level(cfg, club)
check(ok and club["level"] == 1 and club["cash"] == 750_000, "amélioration Babinski 100 000 €")

print("Combo Coca Cherry + Lagui")
club["cash"] = 1_000_000
ok, code, p = engine.activity_coca_cherry(cfg, club, rng)
check(ok and club["coca_cherry_pending"] and club["client_bonus_next"] >= 40, "Coca Cherry 7 500 €, +40 clients")
ok, code, p = engine.book_showcase(cfg, club, "Lagui")
check(ok and club["showcase_pending"] and club["showcase_bonus"] == 1.0, "Lagui programmé (+100 %)")
ok, code, p = engine.book_showcase(cfg, club, "Gims")
check(not ok and code == "ALREADY", "second showcase refusé")
club["last_tick"] = 5000.0
reports = engine.process_ticks(cfg, club, now=5000.0 + 181, rng=rng)
r = reports[0]
check(r["showcase"] is not None and r["showcase"]["artist"] == "Lagui", "showcase Lagui appliqué")
check("coca_lagui" in r["combos"], "combo Coca Cherry × Lagui déclenché")
check(r["vips"] >= 2, "+2 VIP du combo")
check(not club["showcase_pending"] and not club["coca_cherry_pending"], "showcase et Coca consommés")
check(engine.artist_cooldown_remaining(cfg, club, "Lagui") == 2, "Lagui en cooldown 2 services")
ok, code, p = engine.book_showcase(cfg, club, "Lagui")
check(not ok and code == "COOLDOWN", "Lagui refusé pendant le cooldown")

print("Événements")
club["last_event_check"] = 0
club["cash"] = 100_000
found = None
for _ in range(50):
    ev = engine.process_random_event(cfg, club, now=10_000 + _ * 600, rng=rng)
    if ev:
        found = ev
        break
check(found is not None, f"un événement fini par arriver ({found['title'] if found else ''})")
fun = None
for _ in range(20):
    fun = engine.process_fun_event(cfg, club, rng)
    if fun:
        break
check(fun is not None and fun["clients"] > 0, f"événement fun ({fun['title'] if fun else ''})")

print("Blackjack")
club["cash"] = 50_000
ok, code, p = engine.blackjack_auto(cfg, club, 1000, rng)
check(ok and code in ("WIN", "LOSE", "PUSH"), f"blackjack auto : {code} ({p['player']} vs {p['dealer']})")
ok, code, p = engine.blackjack_start(cfg, club, 5000, rng)
check(ok, f"blackjack interactif : {code}")
if code == "PLAYING":
    ok, code, p = engine.blackjack_stand(cfg, club, rng)
    check(code in ("WIN", "LOSE", "PUSH"), f"résolution : {code}")
check(club["blackjack_game"] is None, "aucune main en cours après résolution")
ok, code, p = engine.blackjack_auto(cfg, club, 999, rng)
check(not ok and code == "INVALID_BET", "mise hors liste refusée")

print("Boutique")
club["cash"] = 200_000
ok, code, p = engine.shop_buy(cfg, club, "cars", "porsche_911")
check(ok and club["cash"] == 50_000 and "porsche_911" in club["cars"], "Porsche 911 150 000 €")
ok, code, p = engine.shop_sell(cfg, club, "cars", "porsche_911")
check(ok and p["gain"] == 112_500 and club["cash"] == 162_500, "revente 75 % = 112 500 €")
ok, code, p = engine.bitcoin_buy(cfg, club, 2)
check(ok and club["bitcoin"] == 2 and club["cash"] == 32_500, "2 BTC à 65 000 €")
ok, code, p = engine.bitcoin_sell(cfg, club, 1)
check(ok and p["gain"] == 48_750, "revente BTC 48 750 €")
check(engine.net_worth(cfg, club) == club["cash"] + 65_000, "richesse totale")

print("Transferts / bouteilles / braquage")
other = engine.new_club(cfg, "Autre", now=1000.0)
club["cash"] = 100_000
ok, code, p = engine.transfer_money(cfg, club, other, 10_000)
check(ok and club["cash"] == 90_000 and other["cash"] == 10_000, "transfert 10 000 €")
ok, code, p = engine.send_bottle_pack(cfg, club, other, "magnum")
check(ok and club["cash"] == 60_000 and other["cash"] == 30_000 and p["clients"] == 40, "Pack Magnum : -30 000 / +20 000 / +40 clients")
check(engine.robbery_power(cfg, club) == 1 * 4 + 1, "puissance = 4/niveau + 1/équipement")
check(engine.robbery_success_chance(cfg, club, other) == 55, "chance = 50 + 5 - 0 = 55 %")
club["service_count"] = 10
ok, code, p = engine.perform_robbery(cfg, club, other, rng)
check(ok and code in ("SUCCESS", "FAIL"), f"braquage : {code} ({p['amount']} €)")
ok, code, p = engine.perform_robbery(cfg, club, other, rng)
check(not ok and code == "COOLDOWN" and p["remaining"] == 4, "cooldown 4 services")

print("Trade")
club["cars"] = ["urus"]
ok, code, p = engine.trade_apply(cfg, club, other, "cars", "urus")
check(ok and "urus" in other["cars"] and "urus" not in club["cars"], "trade voiture")
ok, code, p = engine.trade_apply(cfg, club, other, "bitcoin", 999)
check(not ok and code == "NO_BTC", "trade BTC refusé")

print("Statut / estimation")
club["last_clients"] = 630
check(engine.club_status(cfg, club) in ("COMPLET", "TRÈS ACTIF", "OUVERT", "CALME"), f"statut = {engine.club_status(cfg, club)}")
est = engine.estimate_service(cfg, club)
check(est["total"] > 0, f"estimation service ≈ {est['total']} €")

print("\nTous les tests moteur passent.")
