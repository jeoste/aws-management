# AWS SNS/SQS Manager

Application web Flask pour inventorier et surveiller en temps réel les Topics SNS, les Queues SQS et leurs souscriptions AWS.

## Fonctionnalités

- 🔍 **Scan automatique** des ressources SNS/SQS multi-régions
- 📊 **Statistiques CloudWatch** (messages publiés, envoyés, reçus sur 28 jours)
- ⚡ **Monitoring temps réel** des messages SQS avec polling direct
- 📈 **Diagrammes visuels** des topologies SNS → SQS
- 💾 **Exports multiples** : JSON, SQL, Draw.io, Mermaid

## Installation

Prérequis: Python 3.9+

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Utilisation

### Interface Web (Recommandé)

Lancez l'application web :

```bash
python app.py
```

L'application s'ouvrira automatiquement dans votre navigateur sur `http://127.0.0.1:5000`

**Étapes :**
1. Entrez vos credentials AWS (Access Key + Secret + Session Token pour rôle IAM)
2. Spécifiez la ou les régions (ex: `eu-central-1,us-east-1`)
3. Cliquez sur "Scan Resources" pour inventorier vos ressources
4. Consultez les onglets Topics, Queues, Links pour voir les détails
5. Allez dans l'onglet "Real-time" pour surveiller les messages en direct

**Monitoring temps réel :**
- Sélectionnez les topics SNS à surveiller
- Les queues abonnées sont automatiquement incluses
- Cliquez sur "Start Monitoring" (bouton bleu)
- Les messages apparaissent instantanément (délai < 4 secondes)

### CLI (Ligne de commande)

```bash
python aws_sns_sqs_map.py --region eu-west-1 --format json
python aws_sns_sqs_map.py --region eu-west-1 --format mermaid > diagram.mmd
```

Options:
- `--region REGION` (répétable)
- `--profile PROFILE` (profil AWS local, optionnel)
- `--aws-access-key-id` (optionnel) : clé d'accès AWS
- `--aws-secret-access-key` (optionnel) : secret AWS
- `--aws-session-token` (optionnel) : token de session pour credentials temporaires
- `--format json|mermaid` (défaut: json)
- `--output chemin` (optionnel; sinon stdout)

Exemples :

```powershell
# Utiliser un profil AWS
python aws_sns_sqs_map.py --profile mon-profil --region eu-west-1 --format json

# Avec credentials temporaires (assume role)
python aws_sns_sqs_map.py --region eu-west-1 --aws-access-key-id ABC... --aws-secret-access-key xyz... --aws-session-token token... --format json
```

## Architecture technique

- **Backend** : Flask (Python)
- **Frontend** : HTML/JS/TailwindCSS
- **AWS SDK** : boto3
- **Stockage credentials** : keyring (système d'exploitation)
- **Monitoring** : Polling SQS direct avec long-polling (2s)

## Limitations

- Mono-compte par scan (multi-régions supporté)
- Monitoring temps réel limité aux queues SQS (les topics SNS ne stockent pas de messages)
- Les messages sont lus de façon non-destructive (visibility timeout = 0)
- Authentification assume role AWS requise (Access Key + Secret + Session Token)

## Exemple Mermaid

```mermaid
graph LR
  subgraph ${ACCOUNT} ${REGION}
    T1[Topic: example]:::topic --> Q1((Queue: example)):::queue
  end

classDef topic fill:#f0f9ff,stroke:#38bdf8,color:#0c4a6e;
classDef queue fill:#fef3c7,stroke:#f59e0b,color:#78350f;
```

