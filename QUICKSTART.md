# Guide de Démarrage Rapide

## Installation (5 minutes)

### 1. Cloner ou télécharger le projet

```bash
cd c:\github-prod\aws-management
```

### 2. Créer l'environnement virtuel

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Installer les dépendances

```powershell
pip install -r requirements.txt
```

## Utilisation

### Lancer l'Application

```powershell
python app.py
```

L'application s'ouvre automatiquement dans votre navigateur sur `http://127.0.0.1:5000`

## Premier Scan (2 minutes)

### 1. Configurer les Credentials AWS

Dans l'interface web, saisissez :

- **Access Key ID** : Votre clé d'accès AWS
- **Secret Access Key** : Votre clé secrète AWS
- **Session Token** : Token de session (requis pour assume role)
- **Regions** : Régions à scanner (ex: `eu-central-1,us-east-1`)

💡 **Cochez "Remember credentials"** pour sauvegarder de façon sécurisée.

### 2. Tester la Connexion

Cliquez sur **"Test Connection"** pour vérifier vos credentials.

Vous devriez voir : `Connected: arn:aws:sts::123456789:assumed-role/...`

### 3. Scanner les Ressources

Cliquez sur **"Scan Resources"** pour lister tous vos topics SNS et queues SQS.

Les résultats s'affichent dans les onglets :
- **Topics** : Liste des topics SNS
- **Queues** : Liste des queues SQS
- **Links** : Subscriptions SNS → SQS
- **Diagram** : Visualisation graphique Mermaid

⏱️ Temps de scan : ~5-10 secondes par région

## Monitoring Temps Réel (30 secondes)

### 1. Aller dans l'onglet "Real-time"

### 2. Sélectionner les Resources

**Option A** : Sélectionnez les **topics SNS** à surveiller
- Les queues abonnées seront automatiquement incluses
- Cliquez sur "All" pour tout sélectionner

**Option B** : Sélectionnez manuellement des **queues SQS** spécifiques

### 3. Démarrer la Surveillance

Cliquez sur **"Start Monitoring"** (bouton bleu qui devient rouge)

### 4. Observer les Messages

Les messages apparaissent en temps réel (délai < 4 secondes) :

- ✉️ **MESSAGE** : Nouveau message reçu dans une queue
- ⚠️ **ERROR** : Erreur de polling
- 📤 **SENT** / 📥 **RECEIVED** : Métriques CloudWatch

Chaque message affiche :
- Timestamp exact
- Nom de la resource (queue)
- Région AWS
- Message ID
- **Contenu complet du message**

### 5. Tester avec un Message

Ouvrez la console AWS et publiez un message test sur un de vos topics SNS.

Le message devrait apparaître dans l'interface en **2-4 secondes** ! 🚀

### 6. Arrêter la Surveillance

Cliquez sur **"Stop Monitoring"** (bouton rouge qui redevient bleu)

## Statistiques CloudWatch (optionnel)

Cliquez sur **"Fetch Statistics"** pour obtenir les métriques des 28 derniers jours :

- **Topics** : Nombre de messages publiés
- **Queues** : Nombre de messages envoyés/reçus

⏱️ Temps de récupération : ~10-30 secondes selon le nombre de ressources

## Exports

Cliquez sur **"Export"** et choisissez le format :

- **JSON** : Inventaire complet
- **SQL** : Script CREATE TABLE + INSERT
- **Draw.io** : Diagramme importable dans draw.io
- **Mermaid** : Code Mermaid pour documentation

## Dépannage

### L'application ne démarre pas

```powershell
# Vérifier que Flask est installé
python -c "import flask; print(flask.__version__)"

# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Pas de messages en temps réel

1. ✅ Vérifiez que vous avez bien sélectionné des topics/queues
2. ✅ Publiez un message test sur un topic SNS
3. ✅ Vérifiez que les queues ont des subscriptions actives
4. ✅ Vérifiez vos permissions IAM (sqs:ReceiveMessage, sqs:ChangeMessageVisibility)

### Erreur de credentials

```
Error: The security token included in the request is invalid
```

→ Vos credentials ont expiré (session token). Générez de nouveaux credentials et relancez.

### Erreur de région

```
Error: Could not connect to the endpoint URL
```

→ Vérifiez que la région est correctement orthographiée (ex: `eu-central-1`, pas `eu-central1`)

## Prochaines Étapes

- 📖 Consultez [README.md](README.md) pour plus de détails
- 🏗️ Consultez [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) pour comprendre l'architecture
- 📝 Consultez [CHANGELOG.md](CHANGELOG.md) pour l'historique des versions

## Raccourcis Clavier (dans l'interface)

- `Ctrl + R` : Rafraîchir la page
- `F5` : Recharger l'application
- `F12` : Ouvrir les outils développeur (pour debug)

## Support

En cas de problème, vérifiez :
1. Les logs dans le terminal où `python app.py` tourne
2. La console JavaScript (F12) dans le navigateur
3. Vos permissions IAM AWS

Bon monitoring ! 🎉

