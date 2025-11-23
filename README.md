# AWS Manager (MVP)

Petit utilitaire CLI pour inventorier les Topics SNS, les Queues SQS et leurs souscriptions, puis générer un export JSON et/ou un diagramme Mermaid.

## Installation

Prérequis: Python 3.9+

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Utilisation

```bash
python aws_sns_sqs_map.py --region eu-west-1 --format json
python aws_sns_sqs_map.py --region eu-west-1 --format mermaid > diagram.mmd
```

Options:
- `--region REGION` (répétable)
- `--profile PROFILE` (profil AWS local, optionnel)
- `--aws-access-key-id` (optionnel) : clé d'accès AWS. Si fournie sans `--aws-secret-access-key`, vous serez invité(e) à saisir le secret de façon sécurisée.
- `--aws-secret-access-key` (optionnel) : secret AWS (évitez de le passer en clair sur la ligne de commande si possible).
- `--aws-session-token` (optionnel) : token de session pour les credentials temporaires.
- `--format json|mermaid` (défaut: json)
- `--output chemin` (optionnel; sinon stdout)

Authentification: utilise les mécanismes standard AWS (profils, variables d'environnement, SSO, etc.).

Exemples d'utilisation avec clés en ligne de commande (moins recommandé que les profils):

```powershell
# Prompt pour le secret si omis
python aws_sns_sqs_map.py --region eu-west-1 --aws-access-key-id ABC... --format json

# Fournir le secret et token (par ex. CI sécurisé)
python aws_sns_sqs_map.py --region eu-west-1 --aws-access-key-id ABC... --aws-secret-access-key xyz... --aws-session-token token... --format json
```

Interface graphique (Tkinter)

Un petit GUI est également fourni dans `aws_sns_sqs_gui.py` pour saisir les credentials ou profil, sélectionner des régions et lister/exporter les Topics et Queues.

Lancer le GUI:

```powershell
python aws_sns_sqs_gui.py
```

Remarque: le GUI utilise `boto3` pour interroger AWS. Installez les dépendances si nécessaire:

```powershell
pip install -r requirements.txt
```

## Limitations (MVP)
- Mono-compte par exécution (multi-régions supportées via `--region` répété).
- Souscriptions SNS → SQS uniquement pour le diagramme (les autres protocoles sont listés dans le JSON).
- Pas de retry/backoff avancé.

## Exemple Mermaid

```mermaid
graph LR
  subgraph ${ACCOUNT} ${REGION}
    T1[Topic: example]:::topic --> Q1((Queue: example)):::queue
  end

classDef topic fill:#f0f9ff,stroke:#38bdf8,color:#0c4a6e;
classDef queue fill:#fef3c7,stroke:#f59e0b,color:#78350f;
```

