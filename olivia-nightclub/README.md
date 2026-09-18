# ♣ OLIVIA Nightclubs — jeu web multijoueur

Transformation du bot Discord `nightclub_v35` en jeu de gestion de boîte de nuit
web, multijoueur et persistant. **Le moteur reproduit les mécaniques du bot à
l'identique** (mêmes valeurs, probabilités, cooldowns, combos, événements) ;
l'interface est entièrement nouvelle.

## Lancer le jeu

```bash
pip install -r requirements.txt
python run.py
```

Sur Windows, double-cliquer sur `start.bat` fait les deux (utilise Python 3.12
installé dans `%LOCALAPPDATA%\Programs\Python`, sinon le lanceur `py`).

Puis ouvrir <http://localhost:8000>. Depuis le PC qui héberge le serveur, cocher
**Activer mon accès administrateur sur cet ordinateur** à l'inscription, ou utiliser
ce bouton dans **Paramètres** pour un compte existant. Les administrateurs déjà
enregistrés conservent leurs droits. Un joueur distant ne devient pas administrateur
simplement parce qu'il est le premier inscrit.

La version actuelle inclut la refonte visuelle, le catalogue de rap 2016–2026,
les clips YouTube propres à chaque showcase et la suppression ciblée des clubs.
Voir [la présentation de la refonte](docs/REFONTE_UI.md).

Tests du moteur (sans serveur) : `python tests/test_engine.py`.

Pour jouer à plusieurs : les autres joueurs ouvrent `http://<ton-ip>:8000` sur le
réseau local, ou déploie le dossier sur un hébergeur Python (Railway, Render, VPS…)
avec la commande `python run.py` (port via `OLIVIA_PORT`).

Variables d'environnement optionnelles : `OLIVIA_PORT` (8000), `OLIVIA_HOST`,
`OLIVIA_DB` (chemin SQLite, défaut `data/olivia.db`), `OLIVIA_WORLD_INTERVAL` (5 s).

## Architecture

```
server/
  config.py     GAME_CONFIG : toutes les valeurs du bot (tick, bar, VIP, niveaux,
                managers, équipements, artistes, événements, activités, packs,
                braquage, boutique). Surchargeable par l'admin, stockée en base.
  engine.py     Moteur pur (port fidèle de process_ticks & co). Aucune I/O.
  db.py         SQLite : users, sessions, clubs (JSON = format du bot), service_log,
                transactions, notifications, trades, city_feed, settings.
  services.py   Actions validées côté serveur, journal, notifications, SSE, vues.
  auth.py       Mots de passe scrypt + sessions cookie.
  app.py        API FastAPI + flux temps réel (SSE) + boucle monde + statique.
web/
  index.html, css/app.css
  js/app.js     store, API, routeur, SSE, compteur de service, overlays/toasts
  js/scene.js   scène SVG procédurale du club (niveau, équipements, foule, showcase…)
  js/pages.js   toutes les pages (ville, ma boîte, direction, finances, showcases,
                équipements, manager, activités/blackjack, boutique, banque, classement,
                profil, visite, notifications, progression, admin)
reference/      script du bot d'origine (source de vérité) + flex.py
docs/CORRESPONDANCE.md   mécanique Discord → fonction web → interface → données
```

## Principes

- **Temps réel côté serveur** : un service toutes les 3 minutes (`tick_seconds`), calculé
  à partir de `last_tick` (timestamps). Une boucle de fond fait avancer tous les clubs
  toutes les 5 s, exactement comme `ranking_embed` du bot le faisait à chaque appel.
  Le club continue de tourner hors-ligne ; au retour, un récapitulatif est affiché.
- **Argent jamais côté client** : chaque action passe par l'API, sous verrou global,
  dans une transaction SQLite. Le client reçoit l'état complet après chaque action.
- **Configuration centralisée** : rien n'est hardcodé dans le frontend ; le client reçoit
  `public_config` et l'admin peut surcharger n'importe quelle valeur.
- **Indépendant de Discord** : comptes locaux. Import de `nightclub_data.json` depuis
  l'admin (les clubs sont repris tels quels, `discord_id` conservé pour une future
  connexion Discord).

## Améliorations web (séparées du jeu original)

Regroupées dans `config["web"]` :

- `blackjack_mode` : `"interactive"` (vraie table : tirer / rester, mêmes cartes et mêmes
  gains) ou `"auto"` (algorithme original du bot, main jouée automatiquement).
- statuts de club (OUVERT / TRÈS ACTIF / COMPLET / CALME / SHOWCASE / ÉVÉNEMENT),
  flux « Actualités de la nuit », notifications persistantes, historique financier,
  classements secondaires (richesse, revenus 24 h, clients, VIP, showcases, progression).

Aucune valeur économique du bot n'a été modifiée.

## Système audio

Architecture dans `web/js/audio.js` (AudioManager, Web Audio API) + `server/audio.py` (assets).

| | Portée | Déclencheur | Diffusion |
|---|---|---|---|
| 🚨 **Braquage** | **GLOBAL** — tous les joueurs connectés, braqueur compris | braquage validé par le serveur | `robbery_created` (SSE broadcast) → FX + alerte plein écran synchronisés |
| 🎤 **Showcase** | **LOCAL** — uniquement le joueur dont `activeClubView === club_id` | `showcase_started` / `showcase_ended` (SSE broadcast) ou arrivée dans la vue du club | extrait aléatoire (jamais deux fois le même de suite), fondu, enchaînement tant que le showcase est actif |
| 🎧 Ambiance | LOCAL — vue du club consulté | `setView` | boucle, réduite à 35 % pendant un extrait de showcase |
| 🔔 Interface / événements | joueur | actions, services, notifications, événements spéciaux | bus `notifications` / `fx` |

- Bus : `master → { fx, showcase, ambient, notifications }`. Réglages dans **Paramètres → Audio**
  (général, showcase, ambiance, notifications, FX, mute), sauvegardés dans le profil (`users.audio_prefs`)
  et en local.
- Anti-spam FX : au plus 3 sons de braquage par 10 s, volumes 1 / 0,7 / 0,5, file d'attente ; l'événement
  de jeu et la notification ne sont jamais bloqués (`config["audio"]`).
- Autoplay : le moteur s'initialise à la première interaction ; si le navigateur bloque, un bouton
  « 🔊 Activer le son » apparaît dans l'en-tête. Onglet caché → sons locaux coupés, restaurés au retour.
- Chargement paresseux : seuls les FX de braquage et deux sons d'interface sont préchargés ; les extraits
  de showcase / ambiance sont chargés à l'entrée dans un club, puis mis en cache.
- Assets : `web/audio/{robbery,showcases/<artiste>,ambient,ui,events}/`, scannés au démarrage dans la
  table `audio_assets` (activation / poids modifiables dans Admin → Audio, bouton « Rescanner »).
  **Aucun contenu protégé n'est fourni** : les fichiers actuels sont des placeholders synthétisés par
  `tools/make_placeholder_audio.py`. Déposez vos extraits autorisés dans `showcases/<artiste>/`
  (ex. `lagui_01.mp3`) ; tant qu'un dossier d'artiste est vide, `showcases/_placeholder/` est utilisé.
- Tables : `audio_assets` (id, category, key, file_url, duration, enabled, weight), `active_showcases`
  (club_id, artist, source, started_at, ends_at, status), `robberies`. La base reste la source de vérité :
  le client ne fait que réagir aux événements validés par le serveur.

## Notes de fidélité

- `OWNER_BONUS` (1 Md€ pour un ID Discord précis) n'est pas reproduit tel quel : il est
  remplacé par l'outil admin « ajuster la trésorerie ».
- Les événements spéciaux (25 % toutes les 10 min) sont contrôlés en continu par la
  boucle monde, ce qui correspond au comportement du bot sur un serveur actif.
