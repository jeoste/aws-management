# Structure du Projet

```
aws-management/
│
├── app.py                      # Application Flask principale (point d'entrée)
├── aws_sns_sqs_map.py         # Module CLI pour scan et export
├── requirements.txt            # Dépendances Python
├── README.md                   # Documentation utilisateur
├── CHANGELOG.md                # Historique des versions
├── PROJECT_STRUCTURE.md        # Ce fichier
├── .gitignore                  # Fichiers à ignorer par Git
│
├── static/                     # Assets frontend
│   ├── app.js                 # Logique JavaScript (monitoring, UI)
│   └── style.css              # Styles TailwindCSS
│
├── templates/                  # Templates HTML
│   └── index.html             # Interface web principale
│
└── tests/                      # Tests unitaires
    └── test_app.py            # Tests Flask

```

## Description des Fichiers

### Backend

#### `app.py`
Application Flask principale avec les endpoints API :

- `GET /` : Page d'accueil
- `GET/POST /api/credentials` : Gestion des credentials AWS
- `POST /api/test-connection` : Test de connexion AWS
- `POST /api/scan` : Scan des ressources SNS/SQS
- `POST /api/stats` : Récupération des métriques CloudWatch
- `POST /api/monitor` : **Monitoring temps réel SQS** (polling direct)
- `POST /api/export/mermaid` : Export diagramme Mermaid
- `POST /api/export/sql` : Export SQL
- `POST /api/export/drawio` : Export Draw.io

#### `aws_sns_sqs_map.py`
Module CLI réutilisable pour :
- Scanner les topics SNS et queues SQS multi-régions
- Détecter les subscriptions SNS → SQS
- Générer exports JSON et Mermaid
- Utilisé par `app.py` via `build_inventory()`

### Frontend

#### `templates/index.html`
Interface web unique avec :
- Formulaire credentials AWS
- Navigation par onglets (Topics, Queues, Links, Diagram, Real-time)
- Tables de données avec statistiques
- Zone de monitoring temps réel
- Boutons d'export

#### `static/app.js`
Logique frontend :
- `scanResources()` : Lance le scan AWS
- `fetchStatistics()` : Récupère les métriques CloudWatch
- `toggleRealtime()` : Démarre/arrête le monitoring
- `fetchRealtimeMessages()` : Poll les messages SQS toutes les 2 secondes
- `updateTables()` : Met à jour l'affichage des ressources
- `exportData()` : Gère les exports

#### `static/style.css`
Styles TailwindCSS personnalisés

### Tests

#### `tests/test_app.py`
Tests unitaires Flask avec mocks :
- Test routing
- Test API credentials
- Test scan avec mocks boto3
- Test statistiques CloudWatch
- Test exports (Draw.io, SQL)

## Flux de Données

### 1. Scan Initial

```
User → Frontend (scanResources)
       ↓
    POST /api/scan
       ↓
    aws_sns_sqs_map.build_inventory()
       ↓ boto3
    AWS (SNS, SQS)
       ↓
    Frontend (updateTables)
```

### 2. Monitoring Temps Réel

```
User → Start Monitoring
       ↓
    setInterval(2000ms)
       ↓
    POST /api/monitor {items: [queues]}
       ↓
    sqs.receive_message(WaitTimeSeconds=2)
       ↓ boto3
    AWS SQS
       ↓
    Frontend (display messages)
       ↑
    Loop every 2 seconds
```

### 3. Statistiques

```
User → Fetch Statistics
       ↓
    POST /api/stats {items: [topics, queues]}
       ↓
    cloudwatch.get_metric_statistics()
       ↓ boto3
    AWS CloudWatch (28 days data)
       ↓
    Frontend (update tables with stats)
```

## Technologies

- **Backend** : Flask 3.0+, boto3, keyring
- **Frontend** : Vanilla JavaScript, TailwindCSS, Mermaid.js, Lucide Icons
- **AWS** : SNS, SQS, CloudWatch, STS
- **Tests** : unittest, unittest.mock

## Points d'Attention

1. **Monitoring temps réel** :
   - Utilise `change_message_visibility(VisibilityTimeout=0)` pour lecture non-destructive
   - Polling toutes les 2 secondes côté frontend
   - Long-polling 2s côté backend (WaitTimeSeconds=2)

2. **Credentials** :
   - Stockage sécurisé via keyring OS
   - Support rôle IAM (Access Key + Secret + Session Token requis)
   - Jamais stockés en clair dans le code

3. **Performance** :
   - Scan multi-région en séquentiel (non parallèle)
   - Statistiques CloudWatch peuvent prendre du temps (28 jours de données)
   - Monitoring temps réel optimisé pour faible latence

4. **Limitations** :
   - Mono-compte (multi-régions supporté)
   - SQS uniquement pour monitoring temps réel (SNS ne stocke pas)
   - 100 messages max dans l'historique temps réel

