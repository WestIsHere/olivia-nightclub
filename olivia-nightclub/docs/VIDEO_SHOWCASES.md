# Vidéo et musique des showcases, par boîte

Chaque réservation prépare côté serveur un ordre aléatoire des clips de l'artiste.
Le programme est enregistré en base. Tous les joueurs à l'intérieur de cette boîte
reçoivent le même clip et la même heure de début ; un nouveau visiteur rejoint la
position déjà en cours. Les programmes de deux boîtes sont indépendants.

Un visiteur doit cliquer **Entrer**. Consulter la façade ne lance rien. Le patron
voit sa scène depuis **Ma boîte**. Sortir, changer de boîte, changer de page ou
masquer l'onglet arrête le lecteur. Les clips sont diffusés dès la réservation et
s'arrêtent à la fin du showcase (au prochain service, comme auparavant).

Le lecteur officiel YouTube fournit l'image et le son. Aucun fichier musical ou
vidéo n'est téléchargé sur le serveur du jeu. Le catalogue contient 333 liens,
trois par artiste, y compris des collaborations et des visualizers. Les liens,
titres, chaînes et durées proviennent de pages publiques YouTube consultées le
18 septembre 2026. Le fichier `server/showcase_videos.json` permet de les modifier.
Exemples PNL : [Au DD](https://www.youtube.com/watch?v=BtyHYIpykN0),
[Blanka](https://www.youtube.com/watch?v=u8bHjdljyLw),
[À l'Ammoniaque](https://www.youtube.com/watch?v=Vl-GJaitlNs).

## Lecture

Les réglages Audio (volume général, showcase et mute) s'appliquent au lecteur.
Si le navigateur refuse l'autoplay sonore, **Activer le clip et le son** permet
de rejoindre la lecture par un clic. Si un clip est retiré ou si son intégration
est refusée, un message et un bouton de nouvel essai sont affichés. Le programme
reprend au morceau suivant à son heure prévue, sans faire diverger les visiteurs.
La synchronisation vise le même clip et une position commune ; la mise en tampon,
les publicités et les interventions manuelles dans le lecteur peuvent introduire
un décalage. Il ne s'agit pas d'une synchronisation audio à la milliseconde.

Dans **Administration → Clips YouTube des showcases**, sélectionner un artiste et
coller les liens (un par ligne) pour enrichir les showcases suivants. Les playlists
intégrées peuvent être remplacées par artiste dans les surcharges
`audio.showcase_videos`. Les clips ajoutés en base et désactivés dans les assets
sont exclus du prochain tirage, y compris s'ils figurent au catalogue intégré.

Référence : [API IFrame YouTube](https://developers.google.com/youtube/iframe_api_reference)
(autoplay, commandes de lecture, erreurs d'intégration). La page du jeu envoie le
référent d'origine requis par YouTube ; aucune clé API n'est nécessaire.

## Mise à jour et vérification

Redémarrer le serveur puis actualiser les navigateurs avec Ctrl+F5. La migration
ajoute uniquement `active_showcases.screen_playlist`. Les sauvegardes existantes
restent compatibles. Un showcase déjà en cours reçoit son programme à sa première
consultation après mise à jour. Le programme survit au redémarrage du serveur.

Tests : `python tests/test_engine.py`, `python tests/test_showcase_catalog.py`,
`python tests/test_showcase_media.py`,
`node --test tests/test_club_screen.mjs tests/test_youtube_stage.mjs`.
Ils couvrent les réservations, la persistance, deux boîtes et plusieurs visiteurs,
les arrivées tardives, les réponses réseau périmées, l'arrêt en sortant, le mute
et les commandes envoyées au lecteur. Tests réussis.

Vérification dans l'interface : aucun lecteur devant la boîte, écran PNL à
l'intérieur de Palmeray, écran Gims à l'intérieur de Babinski, écran masqué à la
sortie. Limite de la vérification : le lecteur externe YouTube n'a pas achevé son
chargement dans le navigateur de prévisualisation intégré. La lecture réelle de
l'image et du son reste donc à confirmer dans le navigateur habituel du jeu.
