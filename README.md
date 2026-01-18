# AWS SNS/SQS Manager

Web application built with Flask for inventorying and real-time monitoring of AWS SNS Topics, SQS Queues, and their subscriptions.

## Features

- **Automatic scanning** of SNS/SQS resources across multiple regions
- **CloudWatch statistics** (messages published, sent, received over 28 days)
- **Real-time monitoring** of SQS messages with direct polling
- **Visual diagrams** of SNS → SQS topologies
- **Multiple export formats**: JSON, SQL, Draw.io, Mermaid, JSON Canvas

## Installation

Prerequisites: Python 3.9+

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

Start the web application:

```bash
python app.py
```

The application will automatically open in your browser at `http://127.0.0.1:5000`

**Steps:**
1. Enter your AWS credentials (Access Key + Secret + Session Token for IAM roles)
2. Specify one or more regions (e.g., `eu-central-1,us-east-1`)
3. Click "Scan Resources" to inventory your resources
4. View the Dashboard, Topics, and Pipeline sections for details
5. Go to the "Real-time" section to monitor messages in real-time

**Real-time monitoring:**
- Select SQS queues to monitor
- Click "Start Monitoring" (orange button that turns red when active)
- Messages appear instantly (delay < 4 seconds)

### CLI (Command Line)

```bash
python aws_sns_sqs_map.py --region eu-west-1 --format json
python aws_sns_sqs_map.py --region eu-west-1 --format mermaid > diagram.mmd
```

Options:
- `--region REGION` (repeatable)
- `--profile PROFILE` (local AWS profile, optional)
- `--aws-access-key-id` (optional): AWS access key
- `--aws-secret-access-key` (optional): AWS secret key
- `--aws-session-token` (optional): session token for temporary credentials
- `--format json|mermaid` (default: json)
- `--output path` (optional; otherwise stdout)

Examples:

```powershell
# Use an AWS profile
python aws_sns_sqs_map.py --profile my-profile --region eu-west-1 --format json

# With temporary credentials (assume role)
python aws_sns_sqs_map.py --region eu-west-1 --aws-access-key-id ABC... --aws-secret-access-key xyz... --aws-session-token token... --format json
```

## Technical Architecture

- **Backend**: Flask (Python)
- **Frontend**: HTML/JS with TailwindCSS, GSAP animations, Lenis smooth scroll
- **AWS SDK**: boto3
- **Credential storage**: keyring (operating system)
- **Monitoring**: Direct SQS polling with long-polling (5s)

## Limitations

- Single account per scan (multi-region supported)
- Real-time monitoring limited to SQS queues (SNS topics do not store messages)
- Messages are read non-destructively (visibility timeout = 0)
- AWS assume role authentication required (Access Key + Secret + Session Token)

## Mermaid Example

```mermaid
graph LR
  subgraph ${ACCOUNT} ${REGION}
    T1[Topic: example]:::topic --> Q1((Queue: example)):::queue
  end

classDef topic fill:#f0f9ff,stroke:#38bdf8,color:#0c4a6e;
classDef queue fill:#fef3c7,stroke:#f59e0b,color:#78350f;
```

## Documentation

- [Quick Start Guide](docs/quickstart.md) - Get started in 5 minutes
- [Project Structure](docs/project-structure.md) - Architecture and code organization
- [Monitoring Behavior](docs/monitoring-behavior.md) - How real-time monitoring works
- [React Setup](docs/react-setup.md) - React components configuration
- [Changelog](docs/changelog.md) - Version history

## License

This project is provided as-is for internal use.