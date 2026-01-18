# Quick Start Guide

## Installation (5 minutes)

### 1. Clone or download the project

```bash
cd aws-management
```

### 2. Create virtual environment

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
# or
source .venv/bin/activate  # Linux/Mac
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Launch Application

```bash
python app.py
```

The application will automatically open in your browser at `http://127.0.0.1:5000`

## First Scan (2 minutes)

### 1. Configure AWS Credentials

In the web interface, enter:

- **Access Key ID**: Your AWS access key
- **Secret Access Key**: Your AWS secret key
- **Session Token**: Session token (required for assume role)
- **Regions**: Regions to scan (e.g., `eu-central-1,us-east-1`)

**Tip**: Check "Remember credentials" to save securely.

### 2. Test Connection

Click **"Test Connection"** to verify your credentials.

You should see: `Connected: arn:aws:sts::123456789:assumed-role/...`

### 3. Scan Resources

Click **"Scan Resources"** to list all your SNS topics and SQS queues.

Results are displayed in sections:
- **Dashboard**: Overview with statistics
- **Topics**: List of SNS topics
- **Queues**: List of SQS queues
- **Pipeline**: Mermaid diagram visualization

Scan time: ~5-10 seconds per region

## Real-time Monitoring (30 seconds)

### 1. Go to "Real-time" section

### 2. Select Resources

**Option A**: Select **SQS queues** to monitor
- Click "All" to select everything

**Option B**: Manually select specific **SQS queues**

### 3. Start Monitoring

Click **"Start Monitoring"** (orange button that turns red when active)

### 4. Observe Messages

Messages appear in real-time (delay < 4 seconds):

- **MESSAGE**: New message received in a queue
- **ERROR**: Polling error
- **SENT** / **RECEIVED**: CloudWatch metrics

Each message displays:
- Exact timestamp
- Resource name (queue)
- AWS region
- Message ID
- **Complete message content**

### 5. Test with a Message

Open AWS console and publish a test message on one of your SNS topics.

The message should appear in the interface within **2-4 seconds**!

### 6. Stop Monitoring

Click **"Stop Monitoring"** (red button that turns orange)

## CloudWatch Statistics (optional)

Click **"Fetch Statistics"** to get metrics for the last 28 days:

- **Topics**: Number of messages published
- **Queues**: Number of messages sent/received

Retrieval time: ~10-30 seconds depending on number of resources

## Exports

Click **"Export"** and choose the format:

- **JSON**: Complete inventory
- **SQL**: CREATE TABLE + INSERT script
- **Draw.io**: Diagram importable in draw.io
- **Mermaid**: Mermaid code for documentation
- **JSON Canvas**: Canvas format for Obsidian

## Troubleshooting

### Application won't start

```bash
# Verify Flask is installed
python -c "import flask; print(flask.__version__)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### No real-time messages

1. Verify you have selected topics/queues
2. Publish a test message on an SNS topic
3. Verify queues have active subscriptions
4. Verify your IAM permissions (sqs:ReceiveMessage, sqs:ChangeMessageVisibility)

### Credentials error

```
Error: The security token included in the request is invalid
```

Your credentials have expired (session token). Generate new credentials and restart.

### Region error

```
Error: Could not connect to the endpoint URL
```

Verify the region is correctly spelled (e.g., `eu-central-1`, not `eu-central1`)

## Next Steps

- Read [README.md](../README.md) for more details
- Check [project-structure.md](project-structure.md) to understand the architecture
- Review [changelog.md](changelog.md) for version history

## Keyboard Shortcuts (in interface)

- `Ctrl + R`: Refresh page
- `F5`: Reload application
- `F12`: Open developer tools (for debugging)

## Support

If you encounter issues, check:
1. Logs in the terminal where `python app.py` is running
2. JavaScript console (F12) in the browser
3. Your AWS IAM permissions
