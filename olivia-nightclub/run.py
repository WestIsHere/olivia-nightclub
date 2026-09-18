"""
Lance le serveur OLIVIA Nightclubs.

    pip install -r requirements.txt
    python run.py

Variables d'environnement optionnelles :
    OLIVIA_HOST            (défaut 0.0.0.0)
    OLIVIA_PORT            (défaut 8000)
    OLIVIA_DB              chemin du fichier SQLite (défaut data/olivia.db)
    OLIVIA_WORLD_INTERVAL  secondes entre deux passes de la boucle monde (défaut 5)
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.app:app",
        host=os.environ.get("OLIVIA_HOST", "0.0.0.0"),
        port=int(os.environ.get("OLIVIA_PORT") or os.environ.get("PORT", "8000")),
        reload=False,
        log_level="info",
    )
