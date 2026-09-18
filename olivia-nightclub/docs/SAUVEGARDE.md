# Conserver les comptes et les progressions

La base SQLite contient les comptes, les mots de passe hachés, les sessions,
les clubs, les historiques et les réglages. Le dépôt Git ne contient pas cette
base. Une copie du code n'est donc pas une sauvegarde des joueurs.

## Export complet

Dans la nouvelle version : Administration → Télécharger la sauvegarde.
L'accès exige une session administrateur. L'export utilise l'API de sauvegarde
SQLite sous le verrou du jeu et inclut les données validées du journal WAL.
Il est vérifié puis téléchargé sans cache. Le fichier temporaire est supprimé.
Le fichier doit rester privé, hors de GitHub et des fichiers web publics.
Cette fonctionnalité ne peut pas exporter les données d'un ancien serveur
qui ne possède pas encore cet endpoint.

Depuis une console ayant accès au fichier du serveur, dans le dossier du jeu :

```sh
python -m server.backups backup /app/data/olivia.db /chemin/prive/olivia-export.db
python -m server.backups inspect /chemin/prive/olivia-export.db
```

Les chemins sont des exemples, à adapter. Le rapport donne les effectifs et
l'intégrité, jamais les identifiants de session ni les mots de passe hachés.
L'export peut se faire pendant le fonctionnement ; pour une bascule sans perte,
arrêter les écritures de l'ancien jeu avant l'export final, puis ne plus le
rouvrir aux joueurs jusqu'à la bascule. La boucle monde écrit aussi hors ligne.

## Restauration avant de démarrer le nouveau serveur

```sh
python -m server.backups restore /chemin/prive/olivia-export.db /var/data/olivia.db
python -m server.backups inspect /var/data/olivia.db
```

Le serveur de destination doit être arrêté. La destination ne doit pas exister,
même vide ; aucun écrasement, fusion ou remise à zéro implicite n'est autorisé.
Une sauvegarde endommagée ou incomplète est refusée. Toutes les tables sont
copiées, y compris les sessions, mots de passe hachés et identifiants de joueurs.
Le fichier obtenu est autonome : aucun `-wal` ou `-shm` ne doit être transféré.

Sur Render (`RENDER=true`), le nouveau code refuse par défaut de démarrer si
la base attendue est absente ou invalide, au lieu de recréer un jeu vide.
`OLIVIA_REQUIRE_EXISTING_DB=1` active cette protection ailleurs.
`OLIVIA_REQUIRE_EXISTING_DB=0` est uniquement prévu pour un premier lancement
volontairement vide ; ce réglage ne doit pas servir à débloquer une migration.
Cette protection n'ajoute aucun stockage persistant et ne garantit pas à elle
seule que Render gardera l'ancienne instance en activité.

## Limite de l'hébergement actuel

Le serveur Render gratuit a un système de fichiers éphémère, sans console SSH
ni disque persistant. Redéployer, redémarrer ou mettre en veille peut effacer
la base. Ajouter un disque implique une offre payante et un redéploiement :
ce n'est pas une méthode de récupération du fichier actuel.

Pour conserver gratuitement le serveur, il faut adapter le stockage du jeu à
une base externe persistante et configurer ses accès privés. Cela ne récupère
pas les anciennes données. Ne pas déployer sur `main` avant d'avoir obtenu et
vérifié la base actuelle et choisi un stockage durable. Une récupération auprès
du support Render peut être demandée, sans garantie de disponibilité.

Sources : https://render.com/docs/free ; https://render.com/docs/disks ;
https://render.com/docs/ssh
