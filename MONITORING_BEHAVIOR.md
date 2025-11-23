# Comportement du Monitoring Temps Réel

## Comment ça fonctionne

### Polling SQS
- **Intervalle frontend** : Toutes les 3 secondes
- **Long-polling backend** : 5 secondes (WaitTimeSeconds=5)
- **Messages par poll** : Maximum 10 messages
- **Mode** : Lecture non-destructive

### Lecture Non-Destructive

Quand un message est lu :
1. `receive_message()` le récupère et le rend invisible (30s par défaut)
2. Le message est affiché dans l'interface
3. `change_message_visibility(VisibilityTimeout=0)` le rend immédiatement visible à nouveau
4. Le message reste dans la queue

**Avantage** : Vous pouvez surveiller sans consommer les messages
**Inconvénient** : Les mêmes messages peuvent apparaître plusieurs fois

## Comportements Attendus

### ✅ Cas Normal : Nouveaux Messages

```
Topic SNS → Publie un message
            ↓
Queue SQS ← Reçoit le message
            ↓
Monitoring ← Détecte en < 8 secondes (3s interval + 5s long-poll)
            ↓
Interface ← Affiche le message
```

Délai typique : **3-8 secondes**

### ✅ Cas Normal : Queue Vide

```
Monitoring → Poll #1 (0 messages) → "en attente..."
           → Poll #2 (0 messages) → "en attente..."
           → Poll #3 (0 messages) → "en attente..."
           ...
           → Poll #5 → Status update affiché
```

Un indicateur de status s'affiche tous les 5 polls pour confirmer que le monitoring est actif.

### ⚠️ Cas Spécial : Purge de Queue

**Scénario** :
1. Monitoring actif avec messages affichés
2. Vous purgez la queue dans la console AWS
3. Les anciens messages restent affichés dans l'interface

**Pourquoi ?** L'interface garde un historique local des 100 derniers messages.

**Solution** : Cliquez sur "Stop Monitoring" puis "Start Monitoring" pour réinitialiser l'affichage.

### ⚠️ Cas Spécial : Messages "Fantômes"

**Scénario** :
1. Message est en cours de lecture (invisible pour 0-30s)
2. Vous supprimez manuellement le message
3. Le monitoring tente de le rendre visible → Échec silencieux

**Pourquoi ?** `change_message_visibility()` échoue si le message n'existe plus.

**Comportement** : L'erreur est ignorée (catch silencieux), aucun impact sur le monitoring.

### ⚠️ Cas Spécial : Messages Dupliqués

**Scénario** :
Vous voyez le même message plusieurs fois dans l'interface.

**Pourquoi ?** 
- Mode non-destructif : le message reste dans la queue
- Le monitoring le re-détecte à chaque poll

**Solution** : C'est normal ! Le monitoring montre tous les messages présents.

## Indicateurs de Status

### Interface Active

```
👀 Surveillance active - en attente de messages...
Polling #12 - 14:23:45
Les messages apparaîtront ici dès leur réception
```

### Messages Affichés

Chaque message montre :
- ✉️ **MESSAGE** : Nouveau message SQS (vert)
- 📤 **SENT** : Métrique CloudWatch (jaune)  
- 📥 **RECEIVED** : Métrique CloudWatch (violet)
- ⚠️ **ERROR** : Erreur de polling (rouge)

### Indicateur de Poll (tous les 5 polls)

```
⏱️ Monitoring actif - Dernier poll: 14:23:45 (25 polls)
```

## Dépannage

### Le monitoring ne démarre pas

**Symptôme** : Rien ne se passe après "Start Monitoring"

**Causes possibles** :
1. Aucun topic/queue sélectionné
2. Credentials expirés
3. Permissions IAM insuffisantes

**Vérification** :
- Ouvrez la console JavaScript (F12)
- Regardez les logs dans le terminal où `python app.py` tourne
- Vérifiez que vous avez bien sélectionné des ressources

### Les nouveaux messages n'apparaissent pas

**Symptôme** : Messages publiés mais pas affichés

**Vérification** :

1. **Confirmez que le message arrive dans la queue** :
   - Ouvrez la console AWS SQS
   - Vérifiez "Messages Available"
   - Si 0, le problème est SNS → SQS

2. **Vérifiez le monitoring** :
   - Status indicator change-t-il ? (confirme que le poll fonctionne)
   - Si oui, attendez 8-10 secondes maximum
   - Si non, arrêtez/redémarrez le monitoring

3. **Vérifiez les permissions IAM** :
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "sqs:ReceiveMessage",
       "sqs:GetQueueUrl",
       "sqs:ChangeMessageVisibility"
     ],
     "Resource": "arn:aws:sqs:*:*:*"
   }
   ```

### Les messages apparaissent en double

**Symptôme** : Même message ID affiché plusieurs fois

**Cause** : Mode non-destructif normal

**Solution** : 
- Si gênant, ajoutez une déduplication côté frontend (future amélioration)
- Ou utilisez le MessageID pour identifier les doublons

### "Realtime error" dans l'interface

**Symptôme** : Message d'erreur rouge dans le log

**Causes possibles** :
1. Session token expiré → Régénérez vos credentials
2. Queue supprimée → Relancez un scan
3. Permissions manquantes → Vérifiez IAM
4. Région incorrecte → Vérifiez la région dans le scan

## Bonnes Pratiques

### 🎯 Pour Tester

1. Démarrez le monitoring sur une queue vide
2. Vérifiez que le status indicator s'actualise
3. Publiez un message test
4. Confirmez l'affichage en < 10 secondes

### 🎯 Pour Surveiller en Production

1. Sélectionnez uniquement les queues importantes
2. Utilisez le filtre de queues si beaucoup de ressources
3. Arrêtez le monitoring quand vous n'en avez plus besoin
4. Rafraîchissez périodiquement (Stop/Start) pour nettoyer l'historique

### 🎯 Pour Debug

1. Ouvrez la console JavaScript (F12)
2. Regardez l'onglet Network pour voir les requêtes `/api/monitor`
3. Vérifiez les réponses JSON
4. Regardez les logs du terminal backend

## Limites Connues

- **Déduplication** : Pas de déduplication des messages dans l'interface
- **Historique** : Limité à 100 messages, les plus anciens sont supprimés
- **Latence** : 3-8 secondes entre publication et affichage
- **Queues FIFO** : Supportées mais peuvent avoir des comportements spécifiques
- **Messages > 500 chars** : Corps tronqué dans l'interface
- **Délai de purge** : AWS peut prendre jusqu'à 60 secondes pour purger complètement une queue

## Optimisations Futures

- [ ] Déduplication par MessageID côté frontend
- [ ] Option "auto-delete" pour lecture destructive
- [ ] Ajustement dynamique de l'intervalle de polling
- [ ] Filtrage des messages par pattern
- [ ] Export de l'historique des messages
- [ ] WebSocket pour push temps réel (au lieu de polling)

