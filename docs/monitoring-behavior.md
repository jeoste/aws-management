# Real-time Monitoring Behavior

## How It Works

### SQS Polling
- **Frontend interval**: Every 3 seconds
- **Backend long-polling**: 5 seconds (WaitTimeSeconds=5)
- **Messages per poll**: Maximum 10 messages
- **Mode**: Non-destructive reading

### Non-Destructive Reading

When a message is read:
1. `receive_message()` retrieves it and makes it invisible (30s by default)
2. Message is displayed in the interface
3. `change_message_visibility(VisibilityTimeout=0)` makes it immediately visible again
4. Message remains in the queue

**Advantage**: You can monitor without consuming messages
**Disadvantage**: Same messages may appear multiple times

## Expected Behaviors

### Normal Case: New Messages

```
SNS Topic → Publishes a message
            ↓
SQS Queue ← Receives the message
            ↓
Monitoring ← Detects in < 8 seconds (3s interval + 5s long-poll)
            ↓
Interface ← Displays the message
```

Typical delay: **3-8 seconds**

### Normal Case: Empty Queue

```
Monitoring → Poll #1 (0 messages) → "waiting..."
           → Poll #2 (0 messages) → "waiting..."
           → Poll #3 (0 messages) → "waiting..."
           ...
           → Poll #5 → Status update displayed
```

A status indicator displays every 5 polls to confirm monitoring is active.

### Special Case: Queue Purge

**Scenario**:
1. Monitoring active with messages displayed
2. You purge the queue in AWS console
3. Old messages remain displayed in the interface

**Why?** The interface keeps a local history of the last 100 messages.

**Solution**: Click "Stop Monitoring" then "Start Monitoring" to reset the display.

### Special Case: Ghost Messages

**Scenario**:
1. Message is being read (invisible for 0-30s)
2. You manually delete the message
3. Monitoring tries to make it visible → Silent failure

**Why?** `change_message_visibility()` fails if the message no longer exists.

**Behavior**: Error is ignored (silent catch), no impact on monitoring.

### Special Case: Duplicate Messages

**Scenario**:
You see the same message multiple times in the interface.

**Why?**
- Non-destructive mode: message stays in queue
- Monitoring re-detects it on each poll

**Solution**: This is normal! Monitoring shows all present messages.

## Status Indicators

### Active Interface

```
Monitoring active - waiting for messages...
Polling #12 - 14:23:45
Messages will appear here as soon as they are received
```

### Messages Displayed

Each message shows:
- **MESSAGE**: New SQS message (green)
- **SENT**: CloudWatch metric (yellow)
- **RECEIVED**: CloudWatch metric (purple)
- **ERROR**: Polling error (red)

### Poll Indicator (every 5 polls)

```
Monitoring active - Last poll: 14:23:45 (25 polls)
```

## Troubleshooting

### Monitoring won't start

**Symptom**: Nothing happens after "Start Monitoring"

**Possible causes**:
1. No topic/queue selected
2. Expired credentials
3. Insufficient IAM permissions

**Verification**:
- Open JavaScript console (F12)
- Check logs in terminal where `python app.py` is running
- Verify you have selected resources

### New messages don't appear

**Symptom**: Messages published but not displayed

**Verification**:

1. **Confirm message arrives in queue**:
   - Open AWS SQS console
   - Check "Messages Available"
   - If 0, problem is SNS → SQS

2. **Check monitoring**:
   - Does status indicator change? (confirms poll is working)
   - If yes, wait 8-10 seconds maximum
   - If no, stop/restart monitoring

3. **Verify IAM permissions**:
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

### Messages appear duplicated

**Symptom**: Same message ID displayed multiple times

**Cause**: Normal non-destructive mode

**Solution**:
- If annoying, add deduplication on frontend (future improvement)
- Or use MessageID to identify duplicates

### "Realtime error" in interface

**Symptom**: Red error message in log

**Possible causes**:
1. Expired session token → Regenerate credentials
2. Deleted queue → Run a new scan
3. Missing permissions → Check IAM
4. Incorrect region → Verify region in scan

## Best Practices

### For Testing

1. Start monitoring on an empty queue
2. Verify status indicator updates
3. Publish a test message
4. Confirm display in < 10 seconds

### For Production Monitoring

1. Select only important queues
2. Use queue filter if many resources
3. Stop monitoring when no longer needed
4. Periodically refresh (Stop/Start) to clean history

### For Debugging

1. Open JavaScript console (F12)
2. Check Network tab to see `/api/monitor` requests
3. Verify JSON responses
4. Check backend terminal logs

## Known Limitations

- **Deduplication**: No message deduplication in interface
- **History**: Limited to 100 messages, oldest are removed
- **Latency**: 3-8 seconds between publication and display
- **FIFO Queues**: Supported but may have specific behaviors
- **Messages > 500 chars**: Body truncated in interface
- **Purge delay**: AWS can take up to 60 seconds to fully purge a queue

## Future Optimizations

- [ ] Deduplication by MessageID on frontend
- [ ] "Auto-delete" option for destructive reading
- [ ] Dynamic polling interval adjustment
- [ ] Message filtering by pattern
- [ ] Message history export
- [ ] WebSocket for real-time push (instead of polling)
