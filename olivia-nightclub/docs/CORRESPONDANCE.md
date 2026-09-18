# Correspondance — Mécanique Discord → Fonction web → Interface → Données

Source de vérité : `reference/nightclub_bot.py` (+ `reference/flex.py`).

| Mécanique Discord (bot) | Fonction web (`server/`) | Interface web | Données backend |
|---|---|---|---|
| `TICK_SECONDS = 180`, `process_ticks` (bar, clients, entrées, VIP, manager, équipements, showcase, combos, fun event) | `engine.process_ticks` (identique, retourne un rapport par service) ; `services.touch_club` ; boucle `process_world` (5 s) | Compteur « Prochain service », overlay **SERVICE TERMINÉ**, Direction, Finances | `clubs.state` (JSON = format bot), `service_log`, `transactions(kind=service/salary)`, notifications `service` |
| Hors-ligne : services rétroactifs depuis `last_tick` | `engine.process_ticks` (timestamps) + `services.away_recap` | Overlay **BON RETOUR, PATRON** | `users.last_seen`, `service_log`, `transactions` |
| `BAR_MIN/BAR_MAX`, `VIP_BASE_SPEND`, `vip_count` (30/50/20 %) | `config.DEFAULT_CONFIG` (`bar_min`, `bar_max`, `vip_base_spend`, `vip_roll`) ; `engine.vip_count` | Statistiques (page Progression) | `settings.config_overrides` |
| `client_range_for_level`, `income_multiplier`, `showcase_multiplier`, `max_entry_price`, `level_name`, `UPGRADE_COSTS` | `config["levels"]` (7 niveaux) ; `engine.level_info` & co ; `engine.upgrade_level` | Progression visuelle (Club indépendant → … → Le Olivia), bouton Améliorer, animation NIVEAU SUPÉRIEUR, façade qui change | `clubs.state.level`, `transactions(upgrade)`, `city_feed(upgrade)` |
| `EntryPriceModal`, `entry_price_client_multiplier` (+6 % → −6 %) | `engine.set_entry_price`, `engine.estimate_service`, `services.action_entry_price` | Dialogue prix avec **impact estimé avant confirmation** (fréquentation, revenu/client, revenu/service) | `clubs.state.entry_price` |
| `MANAGERS` (Victoria/Josas/Olivia), `manager_service_effects` (salaire si trésorerie suffisante, bonus clients, chance VIP, showcase auto + cooldown) | `config["managers"]`, `engine.manager_service_effects`, `engine.hire_manager/fire_manager` | Page Manager : ENGAGER / REMPLACER / LICENCIER, fiche complète | `clubs.state.manager_id`, `manager_last_showcase_tick`, notifications `manager` |
| `EQUIPMENT_UPGRADES` (9 équipements, `equipment_bonus`) | `config["equipment"]`, `engine.buy_equipment`, `engine.equipment_bonus` | Page Équipements (prix, description, bonus, INSTALLÉ, animation d'achat) + **apparition sur la façade** (lasers, fumée, sono, carré VIP, danseuses, DJ, sécurité, bar, décoration) | `clubs.state.equipment[]`, `transactions(equipment)` |
| `ARTIST_SHOWCASE_BONUS`, `ARTISTS` (ordre), `showcase_cost_for_artist` (paliers), `artist_cooldown_remaining` (2 services), `SHOWCASE_PHRASES`, `generate_showcase_event`, x2 clients, x2 revenus | `config["artists"/"showcase_*"]`, `engine.book_showcase`, `engine.generate_showcase_event`, application dans `process_ticks` | Page Showcases (popularité, coût, cooldown, clients potentiels, impact estimé), enseigne « SHOWCASE CE SOIR », spots | `clubs.state.showcase_*`, `artist_last_service`, `showcases_done`, `transactions(showcase)`, `city_feed(showcase)` |
| Boro 700 + Saisai (60 %), Bello&Dallas (15 % négatif / 15 % positif) | `config["special_showcases"]`, `engine.generate_showcase_event` | Indications sur la fiche artiste, texte du service | `clubs.state.last_showcase_event` |
| Combo secret Coca Cherry + Lagui | `config["combos"]`, `process_ticks` | Overlay **🔥 COMBO DÉCLENCHÉ**, section « Combos secrets » (indices puis découverte) | `clubs.state.coca_cherry_pending`, `combos_discovered[]`, `service_log.combos` |
| `process_random_event` (10 min, 25 %) : police −5 000, bagarre −1 000, route −50 clients, coupure bar ×0,5, influenceur +25, table VIP ×1,5 | `config["events"]`, `engine.process_random_event` | Bannière live 🚨, Dernier événement, notifications, effets visuels sur la façade | `clubs.state.last_event`, `last_event_check`, `*_next`, `transactions(event)` |
| `process_fun_event` (70 %, 10 événements) | `config["fun_events"]`, `engine.process_fun_event` | « Activité en direct », overlay de service | `clubs.state.last_fun_event`, `client_bonus_next`, `service_log.fun_title` |
| Blackjack (mises 1 000 → 1 000 000, cartes `[2..10×4,11]`, joueur ≤16, banque ≤17, gain = mise) | `engine.blackjack_auto` (original) / `blackjack_start/hit/stand` (table interactive, mêmes cartes/gains) ; `config["web"]["blackjack_mode"]` | Table de blackjack (mise, cartes, banque, totaux, résultat, historique V/D) | `clubs.state.blackjack_wins/losses`, `blackjack_game`, `transactions(blackjack)` |
| Boire un verre (250 €, 50 % : −8 / +4), Promo express (2 500 €, +12), Influenceur (5 000 €, 60 % : +30), Coca Cherry (7 500 €, +40, combo) | `config["activities"]`, `engine.activity_*` | Salle Activités (coût, résultat, risque, récompense) | `clubs.state.client_bonus_next/penalty_next`, `drinks_taken`, `transactions(activity)` |
| `flex.py` : `CARS`, `WATCHES`, `BITCOIN_PRICE = 65 000`, `RESALE_RATE = 0.75` ; achat/revente ; `BitcoinAmountModal` (max 1 000 000) | `config["shop"]`, `engine.shop_buy/shop_sell/bitcoin_buy/bitcoin_sell`, `engine.net_worth` | Boutique (Voitures / Montres / Bitcoin), collection, valeur, plus/moins-value | `clubs.state.cars[]`, `watches[]`, `bitcoin`, `transactions(shop_*/btc_*)` |
| `Olivia FLEX` | `services.profile_view` | Profil joueur (collection, BTC, stats, blackjack) | vue publique |
| `TransferMoneyModal` | `engine.transfer_money`, `services.action_transfer` (`mutate_pair`) | Banque → Envoyer de l'argent (joueur, montant, confirmation) | `transactions(transfer_out/in)`, notifications |
| `Olivia BOUTEILLE` (`BOTTLE_PACKS`, clients = max(5, bonus/500)) | `engine.send_bottle_pack`, `services.action_bottle` | Banque → Service bouteilles, animation **🍾 PACK ENVOYÉ**, notification destinataire | `transactions(bottle_out/in)`, `city_feed(bottle)` |
| `Olivia TRADE` (argent / BTC / voiture / montre, accepter / refuser) | `engine.trade_check/trade_apply`, `services.action_trade_*` | Banque → Proposer un trade, propositions reçues/en attente/historique | `trades`, notifications `trade` |
| `Olivia BRAQUE` (`robbery_power`, chance 50±, 20–80 %, 25 %, cooldown 4 services, clients ±) | `engine.robbery_*`, `engine.perform_robbery`, `services.action_robbery` | Banque → Braquage (chance, butin, perte), visite d'un club (chance affichée) | `clubs.state.last_robbery_service`, `transactions(robbery)`, `city_feed(robbery)` |
| `ranking_embed` (trésorerie puis niveau) | `services.leaderboard` (+ richesse, revenus 24 h, clients, VIP, showcases, progression) | Page Classement | `clubs`, `service_log` |
| `RenameClubModal`, `DeleteClubView`, `CreateClubModal`, `new_club` | `engine.rename_club`, `services.delete_club`, `services.register/create_club_for`, `engine.new_club` | Renommer (Ma boîte), création à l'inscription | `users`, `clubs` |
| `apply_owner_bonus_once` (ID Discord) | `services.admin_grant` (panneau admin) | Admin → ajuster la trésorerie | `transactions(admin)` |
| `nightclub_data.json` (`load_data/save_data`) | `db.Database` (SQLite, `clubs.state` = même JSON), `services.admin_import_bot` | Admin → Importer les joueurs du bot | `clubs`, `users.discord_id` |
| Menus Discord (Direction, Finances, Prix entrée, Showcase, Améliorations, Activités, Équipements, Managers, Infos, Envoyer argent, Renommer, Supprimer, Actualiser ; BTQ ; CLS) | routes `/api/*` | Navigation + menu radial « Ma boîte » (Direction, Finances, Showcases, Équipements, Manager, Activités, Boutique, Banque, Statistiques) | — |

## Événements temps réel audio (serveur → clients, SSE)

| Événement | Émis par | Payload | Portée client |
|---|---|---|---|
| `robbery_created` | `services.action_robbery` après validation | robbery_id, attacker_id/name/club, victim_id/name/club, result, amount, chance, timestamp | **GLOBAL** : `AudioManager.playRobbery()` + `showRobberyAlert()` chez tous les connectés |
| `showcase_started` | `services.showcase_started` (réservation joueur ou showcase du manager) | showcase_id, club_id, club_name, artist, source, started_at, ends_at | **LOCAL** : joué seulement si `audio.activeClubView === club_id` |
| `showcase_ended` | `services.showcase_ended` (service consommé, club supprimé) | showcase_id, club_id, artist, ended_at, reason | LOCAL : arrêt si la vue correspond |
| `showcase_changed` | réservé (aucune mécanique ne change l'artiste d'un showcase en attente) | idem `showcase_started` | traité comme `showcase_started` |
| `audio_manifest` | Admin → rescan / activation d'un asset | reason | rechargement du manifeste |

## Nouveautés web (n'existent pas dans le bot, ne modifient pas l'économie)

- Ville (carte des clubs, statuts, façades qui évoluent), visite d'un club, profil.
- Flux « Actualités de la nuit », notifications persistantes, historique financier complet.
- Overlays : service terminé, retour hors-ligne, combo, niveau supérieur, pack envoyé, braquage.
- Blackjack interactif (option), classements secondaires, panneau administrateur, configuration surchargeable.
