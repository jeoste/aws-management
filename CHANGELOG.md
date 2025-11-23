# Changelog

## [2.0.0] - 2025-11-23

### 🎉 Migration vers Interface Web Flask

**Breaking Changes :**
- Suppression complète de l'interface Tkinter (`aws_sns_sqs_gui.py`)
- L'application principale est maintenant `app.py` au lieu de `aws_sns_sqs_gui.py`

### ✨ Nouvelles Fonctionnalités

#### Interface Web Moderne
- Interface web Flask avec TailwindCSS
- Navigation par onglets (Topics, Queues, Links, Diagram, Real-time)
- Thème clair/sombre
- Design responsive et moderne

#### Monitoring Temps Réel
- **Polling SQS direct** remplaçant CloudWatch Metrics (délai réduit de plusieurs minutes à < 4 secondes)
- Surveillance automatique des queues abonnées aux topics sélectionnés
- Affichage des messages avec leur contenu complet
- Lecture non-destructive (visibility timeout = 0)
- Icônes et couleurs pour identifier rapidement les types d'événements
- Historique de 100 messages maximum

#### Statistiques CloudWatch
- Métriques sur 28 jours (messages publiés, envoyés, reçus)
- Affichage dans les tableaux de ressources

#### Exports Multiples
- JSON
- SQL (CREATE TABLE + INSERT)
- Draw.io (.drawio)
- Mermaid (diagramme)

#### Gestion des Credentials
- Stockage sécurisé avec keyring (système d'exploitation)
- Checkbox "Remember credentials"
- Support complet des rôles IAM (Access Key + Secret + Session Token)

### 🔧 Améliorations Techniques

- Meilleure gestion des erreurs avec messages explicites
- Polling SQS avec `WaitTimeSeconds=2` pour réduction de latence
- Extraction automatique du timestamp des messages SQS
- Regroupement des liens par topic dans l'interface
- Code refactorisé et mieux organisé

### 🗑️ Fichiers Supprimés

- `aws_sns_sqs_gui.py` (interface Tkinter obsolète)
- `test_output.txt` (sortie de tests obsolète)
- `__pycache__/aws_sns_sqs_gui.cpython-312.pyc`

### 📝 Documentation

- README mis à jour avec instructions complètes pour l'interface web
- Suppression des références à Tkinter
- Ajout de .gitignore pour éviter les fichiers cache

### 🚀 Migration

Pour migrer depuis l'ancienne version :

**Avant :**
```bash
python aws_sns_sqs_gui.py
```

**Maintenant :**
```bash
python app.py
```

L'application s'ouvre automatiquement dans votre navigateur.

### 🐛 Corrections

- Fix : Les messages SQS apparaissent maintenant instantanément (< 4s)
- Fix : Synchronisation correcte entre scan et onglet Real-time
- Fix : Gestion des erreurs de polling avec affichage dans l'interface
- Fix : Meilleure résolution des URLs de queues à partir des ARN

