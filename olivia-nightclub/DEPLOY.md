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

Le premier compte créé devient administrateur, comme indiqué dans le README.

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
