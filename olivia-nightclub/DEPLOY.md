# Déployer OLIVIA Nightclubs sur Internet

Le projet est déjà conçu comme un jeu web multijoueur : les joueurs partagent le même serveur et la même base de données. Cette configuration ajoute les fichiers nécessaires à un déploiement public.

## Option recommandée : Render

Le fichier `render.yaml` est déjà fourni.

1. Mets le projet dans un dépôt GitHub.
2. Sur Render, crée un nouveau Blueprint.
3. Sélectionne le dépôt.
4. Render détectera `render.yaml`.
5. Le service démarre avec `python run.py`.
6. La base SQLite est placée sur le disque persistant `/var/data/olivia.db`.
7. L'adresse HTTPS fournie par Render devient l'adresse publique du jeu.

Les comptes administrateurs existants conservent leurs droits. L'activation par
localhost concerne uniquement un serveur lancé sur son propre PC : le navigateur
du propriétaire ne devient pas localhost lorsqu'il visite Render. Sur un serveur
Render neuf, un administrateur doit attribuer le rôle au compte voulu via la
console du serveur, sans accorder de droits à partir d'une IP publique partagée.

## Structure du dépôt GitHub

Le code du jeu se trouve dans `olivia-nightclub/`. Le Dockerfile à la racine du
dépôt copie ce sous-dossier et lance `python run.py`. Le Dockerfile à l'intérieur
du sous-dossier convient aussi si le Root Directory Render est `olivia-nightclub`.
`run.py` respecte `OLIVIA_PORT`, puis le `PORT` fourni par Render.

Ne jamais versionner `data/`, les fichiers SQLite, leurs journaux ou les caches
Python. Les `.gitignore` et `.dockerignore` fournis les excluent du code publié
et de l'image Docker. Le disque persistant du service reste la source de vérité.

## Important : persistance

Ne pas utiliser un hébergement éphémère sans disque persistant pour la version publique : SQLite contient les comptes, clubs, transactions, showcases, braquages et autres données du jeu.

Pour une petite communauté, une seule instance avec SQLite + disque persistant suffit. Pour une grosse communauté ou plusieurs instances serveur, il faudra migrer le stockage vers PostgreSQL et le temps réel vers un broker partagé (Redis/pubsub, par exemple).

## Tester localement

Windows :
- double-cliquer sur `start.bat`
- ouvrir `http://localhost:8000`

Ou :

```bash
pip install -r requirements.txt
python run.py
```

Le serveur écoute déjà sur `0.0.0.0`, ce qui permet à la plateforme d'hébergement de recevoir les connexions externes.

## Vérification

Une fois déployé :

`https://TON-DOMAINE/healthz`

doit répondre :

```json
{"ok":true,"service":"olivia-nightclubs"}
```

## Audio

Les FX de braquage sont globaux et les showcases sont locaux au club consulté. Les assets audio restent dans `web/audio/`.

Pour les vrais extraits d'artistes, n'ajoute que des fichiers que tu as le droit d'utiliser.
