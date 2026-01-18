# Project Structure

```
aws-management/
│
├── app.py                      # Main Flask application (entry point)
├── aws_sns_sqs_map.py         # CLI module for scan and export
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
├── docs/                       # Documentation directory
│   ├── quickstart.md          # Quick start guide
│   ├── project-structure.md   # This file
│   ├── monitoring-behavior.md  # Real-time monitoring details
│   ├── react-setup.md         # React components setup
│   └── changelog.md           # Version history
│
├── static/                     # Frontend assets
│   ├── app.js                 # JavaScript logic (monitoring, UI)
│   └── style.css              # TailwindCSS styles
│
├── templates/                  # HTML templates
│   └── index.html             # Main web interface
│
├── src/                        # React/TypeScript source
│   ├── components/            # React components
│   └── main.tsx               # React entry point
│
└── tests/                      # Unit tests
    └── test_app.py            # Flask tests

```

## File Descriptions

### Backend

#### `app.py`
Main Flask application with API endpoints:

- `GET /` : Home page
- `GET/POST /api/credentials` : AWS credentials management
- `POST /api/test-connection` : AWS connection test
- `POST /api/scan` : SNS/SQS resources scan
- `POST /api/stats` : CloudWatch metrics retrieval
- `POST /api/monitor` : **Real-time SQS monitoring** (direct polling)
- `POST /api/export/mermaid` : Mermaid diagram export
- `POST /api/export/sql` : SQL export
- `POST /api/export/drawio` : Draw.io export
- `POST /api/export/canvas` : JSON Canvas export

#### `aws_sns_sqs_map.py`
Reusable CLI module for:
- Scanning SNS topics and SQS queues across multiple regions
- Detecting SNS → SQS subscriptions
- Generating JSON and Mermaid exports
- Used by `app.py` via `build_inventory()`

### Frontend

#### `templates/index.html`
Single-page web interface with:
- AWS credentials modal
- Navigation with section anchors (Dashboard, Topics, Pipeline, Real-time)
- Glass panel cards with statistics
- Real-time monitoring zone
- Export menu

#### `static/app.js`
Frontend logic:
- `scanResources()` : Launches AWS scan
- `fetchStatistics()` : Retrieves CloudWatch metrics
- `toggleRealtime()` : Starts/stops monitoring
- `fetchRealtimeMessages()` : Polls SQS messages every 3 seconds
- `updateTables()` : Updates resource display
- `exportData()` : Handles exports

#### `static/style.css`
Custom TailwindCSS styles

### React Components

#### `src/main.tsx`
React entry point for diagram checkbox components

#### `src/components/DiagramCheckboxList.tsx`
React component for selecting resources in diagram view

### Tests

#### `tests/test_app.py`
Flask unit tests with mocks:
- Routing tests
- Credentials API tests
- Scan tests with boto3 mocks
- CloudWatch statistics tests
- Export tests (Draw.io, SQL)

## Data Flow

### 1. Initial Scan

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

### 2. Real-time Monitoring

```
User → Start Monitoring
       ↓
    setInterval(3000ms)
       ↓
    POST /api/monitor {items: [queues]}
       ↓
    sqs.receive_message(WaitTimeSeconds=5)
       ↓ boto3
    AWS SQS
       ↓
    Frontend (display messages)
       ↑
    Loop every 3 seconds
```

### 3. Statistics

```
User → Fetch Statistics
       ↓
    POST /api/stats {items: [topics, queues]}
       ↓
    cloudwatch.get_metric_statistics()
       ↓ boto3
    AWS CloudWatch (28 days data)
       ↓
    Frontend (update cards with stats)
```

## Technologies

- **Backend**: Flask 3.0+, boto3, keyring
- **Frontend**: Vanilla JavaScript, TailwindCSS, GSAP, Lenis, Mermaid.js, Lucide Icons
- **React**: TypeScript, shadcn/ui components
- **AWS**: SNS, SQS, CloudWatch, STS
- **Tests**: unittest, unittest.mock

## Important Notes

1. **Real-time monitoring**:
   - Uses `change_message_visibility(VisibilityTimeout=0)` for non-destructive reading
   - Polling every 3 seconds on frontend
   - Long-polling 5s on backend (WaitTimeSeconds=5)

2. **Credentials**:
   - Secure storage via OS keyring
   - IAM role support (Access Key + Secret + Session Token required)
   - Never stored in plain text in code

3. **Performance**:
   - Multi-region scan is sequential (not parallel)
   - CloudWatch statistics can take time (28 days of data)
   - Real-time monitoring optimized for low latency

4. **Limitations**:
   - Single account (multi-region supported)
   - SQS only for real-time monitoring (SNS doesn't store messages)
   - 100 messages max in real-time history
