# Olivia — refonte visuelle et administration locale

Version du 18 septembre 2026. Direction artistique inspirée de la référence fournie : noir, violet, verre fumé, photographie de club et titres élégants.

## Écrans couverts

Connexion, inscription, création/recréation de boîte, ville, mon club, direction, finances, showcases, équipements, managers, activités/blackjack, boutique (voitures, montres, bitcoin), banque/échanges/bouteilles/braquage, classement, profil, visites, notifications, progression, paramètres et administration. Les confirmations, alertes, notifications et le lecteur de showcases reprennent les mêmes styles.

Navigation regroupée en trois sections, avec tous les onglets accessibles ; menu dépliable sur téléphone. Icônes SVG locales. Polices Cormorant Garamond, Manrope et Parisienne avec des polices système de repli. La façade du club, qui évolue avec ses équipements, reste accessible sous la vue de l'établissement.

Les emplacements décoratifs « À louer » ont été retirés du carnet d'adresses : seuls les vrais établissements enregistrés sont présentés. Aucune sauvegarde ni boîte existante n'est supprimée par l'installation.

## Accès administrateur depuis le PC du serveur

1. Relancer le serveur, puis ouvrir `http://localhost:8000` sur l'ordinateur qui héberge le jeu (adapter le port si nécessaire).
2. Lors de l'inscription, cocher **Activer mon accès administrateur sur cet ordinateur**. Pour un compte existant, ouvrir **Paramètres → Activer mon accès administrateur**.
3. Le menu **Administration** est alors disponible. Les droits sont conservés sur ce compte, même lors d'une connexion ultérieure depuis une autre adresse.
4. Dans **Les boîtes de la ville**, choisir **Supprimer cette boîte**, recopier son nom exact, puis confirmer.

La suppression concerne le club sélectionné, sa progression et ses historiques financiers. Elle arrête son showcase et annule ses échanges en attente. Le compte du propriétaire reste utilisable pour créer une nouvelle boîte. La suppression de sa propre boîte depuis ce panneau est interdite.

Le raccourci administrateur vérifie côté serveur la connexion locale (`127.0.0.1` / `::1`), le nom d'hôte localhost et l'origine. Une IP publique ou partagée ne donne aucun droit ; les accès via proxy et les en-têtes de transfert sont refusés. Le premier joueur distant ne devient plus automatiquement administrateur. Les administrateurs existants gardent leurs droits. Ce raccourci demande une ouverture directe via localhost, pas via un domaine public ou l'IP du réseau local.

## Vérifications effectuées

- Parcours des 16 entrées de navigation et de la visite d'un autre club, sur ordinateur et écran de 390 px, sans erreur JavaScript.
- Contrôle des débordements des pages principales sur téléphone ; les tableaux larges défilent dans leur propre conteneur.
- Contrôle visuel de la connexion, inscription, création après suppression, ville, catalogue, visites, paramètres et administration.
- Recherche PNL, sous-onglets montres/bitcoin, fenêtres de réservation et de suppression ; confirmation impossible avec un nom incorrect.
- Tests du moteur, du catalogue et des médias de showcases : réussis.
- 8 tests JavaScript du lecteur partagé et du cycle de vie YouTube : réussis. Cela ne constitue pas une nouvelle validation de la lecture réseau YouTube ; voir VIDEO_SHOWCASES.md.
- 4 tests dédiés aux droits locaux, au refus des origines/proxys distants et à la suppression ciblée : réussis.
- Vérification HTTP sur une base temporaire : inscription locale administrateur, refus public/proxy, compte non-admin refusé, activation locale, confirmation du nom, suppression ciblée et recréation.

Tous les comptes et clubs de vérification sont dans une base temporaire séparée. Ils ne sont pas copiés dans le jeu réel.

## Décor original

Outil : Imagegen intégré, sans API CLI. Fichier installé : `C:/Users/ippo1/Desktop/olivia-nightclub/web/images/olivia-interior.png`.

Prompt utilisé :

> Use case: photorealistic-natural. Asset type: full bleed background photograph for a premium nightclub management game called Olivia. Create an original cinematic luxury Paris nightclub interior at night, wide landscape 16:9 composition. The atmosphere is very dark black and rich violet, saturated purple and subtle pink neon, polished black marble, low velvet lounge chairs, graceful tropical foliage silhouettes, small amber table lamps, an elegant backlit bar on the right, sweeping circular pink pendant lights deeper in the left background. Rich authentic architectural photography, sophisticated, immersive, highly detailed, slightly atmospheric haze catching violet spotlights. Empty club ready to open, no visible people. Center and upper left have calm deep dark negative space for elegant website text added separately. Full bleed photographic asset only, no UI, no lettering, no logo, no text, no border, no watermark. High quality 1920x1080 or similar landscape.

Le thème est dans `web/css/olivia.css`, au-dessus de la feuille historique afin de garder les composants de jeu compatibles. Les icônes et descriptions de pages sont dans `web/js/design.js`.
