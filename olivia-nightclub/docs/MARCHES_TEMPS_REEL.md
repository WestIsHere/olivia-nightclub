# Marchés Olivia

La boutique propose BTC, ETH, SOL, XRP, ADA, DOGE, DOT, LINK, AVAX, LTC, BCH et UNI.
Les cours de référence sont les derniers échanges en EUR de Kraken, interrogés toutes les
15 secondes par un seul worker serveur. Aucun compte Kraken ni clé API n'est
nécessaire. Il ne s'agit pas d'un flux tick par tick ni d'ordres financiers réels.
Toutes les transactions utilisent exclusivement la trésorerie fictive du jeu.

## Bitcoin accéléré ×5

À la demande du joueur, le BTC utilise un **cours de jeu fictif amplifié ×5**.
À l'activation, un ancrage persistant conserve sa valorisation existante. Ensuite :
`prix_jeu = ancre_jeu × (cours_réel / ancre_réelle)^5`.
Cela multiplie par cinq les variations logarithmiques, indépendamment du nombre
et de la fréquence des requêtes. Une hausse réelle de 1 % donne environ +5,10 %
dans le jeu ; une baisse réelle de 1 % donne environ −4,90 %. Aucun bruit
aléatoire n'est ajouté. La cote est bornée entre 0,000001 et 10^12 euros de jeu.
Le cours réel reste affiché à côté. Les frais, soldes, achats, ventes et richesse
utilisent le cours du jeu. Les autres cryptomonnaies restent au cours réel.

La courbe BTC démarre à l'activation du mode amplifié et conserve uniquement les
prix de jeu réellement calculés. L'ancien historique Kraken n'est pas présenté
comme une performance fictive passée. La variation BTC correspond à l'historique
du jeu disponible (24 h maximum), tandis que les autres cryptos affichent la
variation depuis 00 h UTC. Les ancrages et courbes survivent aux redémarrages si
le stockage SQLite est persistant.

Les courbes des autres cryptos 1 h / 24 h utilisent les bougies de 5 minutes et les derniers cours
reçus. L'historique des onze actifs réels se charge progressivement (environ trois
minutes) puis est renouvelé une fois par heure par actif. La variation affichée
est calculée depuis l'ouverture à 00 h UTC, pas depuis 24 heures glissantes.
Les données manquantes ne sont pas remplacées par des courbes inventées.

Les positions acceptent huit décimales. Les frais fictifs sont de 0,5 % : achat
arrondi à l'euro supérieur, vente à l'euro inférieur ; vente inférieure à 1 €
refusée. Le cours serveur à l'exécution fait foi. Les soldes sont contrôlés sous
le verrou transactionnel du jeu. Au-delà de 90 secondes sans cours frais, les
achats et ventes sont suspendus ; le dernier cours reste visible avec son état.
Les erreurs réseau déclenchent un délai de reprise progressif, plafonné à 120 s.

Les voitures et montres suivent une **simulation Olivia**, indépendante des
marchés réels. Chaque minute, chaque modèle peut monter ou baisser (choc de
±0,25 %, léger rappel vers sa cote de référence), dans des bornes de 45 à 250 %
du prix initial. Une seule cote est partagée par tous les joueurs ; ni recharger
la page ni changer de compte ne la modifie. La revente conserve la décote de
25 % du jeu, appliquée à la cote courante. Une confirmation d'achat/vente devenue
obsolète est refusée avant toute mutation.

Les historiques (24 h, au plus 289 points par actif), les cours et la graine de
simulation sont sauvegardés dans le réglage SQLite `live_markets_v1`. Les BTC
existants restent dans `bitcoin`, les nouvelles positions dans `crypto` ; les
inventaires de voitures et montres restent inchangés. Les profils, le classement
et la richesse utilisent les cotes actuelles. Les échanges BTC entre joueurs
conservent désormais les fractions.

Un événement SSE `markets` diffuse les mises à jour à tous les clients connectés,
y compris quand une source est indisponible. Les formulaires de quantité ne sont
pas remplacés lors d'une mise à jour. L'API historique `/api/bitcoin/{op}` utilise
les mêmes cours et contrôles que `/api/crypto/{op}`.

La sauvegarde survit aux redémarrages seulement si le fichier SQLite est sur un
stockage persistant. Sur l'instance Render gratuite actuelle, un redéploiement
réinitialise toujours les comptes et les données : ce changement ne résout pas
cette limite de l'hébergement.

Sources : [ticker Kraken](https://docs.kraken.com/api-reference/market-data/get-ticker-information),
[bougies Kraken](https://docs.kraken.com/api-reference/market-data/get-ohlc-data).

Validation : `python tests/test_markets.py`, `python tests/test_engine.py`,
`python tests/test_admin_controls.py` et vérification de la boutique dans le navigateur.
