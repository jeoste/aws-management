# Local Testing Guide

This guide explains how to test the AWS SNS/SQS Manager project locally.

## Prerequisites

- Python 3.9 or higher
- Node.js 16+ (for React components)
- Virtual environment activated
- All dependencies installed

## Setup

### 1. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
# or if pip is not found, use:
python3 -m pip install -r requirements.txt
```

### 2. Install Node.js Dependencies (for React components)

```bash
npm install
```

### 3. Build React Components

```bash
npm run build
```

This generates the compiled React components in `static/react/`.

## Running Unit Tests

### Run All Tests

```bash
python -m pytest tests/
# or
python -m unittest discover tests
# or
python tests/test_app.py
```

### Run Specific Test

```bash
python -m unittest tests.test_app.TestApp.test_index
```

### Test Coverage

```bash
pip install pytest-cov
pytest --cov=app --cov=aws_sns_sqs_map tests/
```

## Running the Application Locally

### Start Flask Server

```bash
python app.py
# or if python is not found, use:
python3 app.py
```

The application will:
- Start on `http://127.0.0.1:5000`
- Automatically open in your browser
- Run in debug mode (auto-reload on code changes)

### Manual Testing Checklist

#### 1. Credentials Management

- [ ] Open credentials modal (click "Console Access")
- [ ] Enter test credentials
- [ ] Check "Remember credentials"
- [ ] Click "Test Connection"
- [ ] Verify connection success message
- [ ] Close and reopen modal
- [ ] Verify credentials are saved (if keyring available)

#### 2. Resource Scanning

- [ ] Enter valid AWS credentials
- [ ] Enter region(s) (e.g., `us-east-1`)
- [ ] Click "Scan Resources"
- [ ] Verify loading indicator
- [ ] Check Dashboard section shows statistics
- [ ] Verify Topics section displays topics
- [ ] Verify Queues section displays queues
- [ ] Check region indicator in navigation updates

#### 3. Statistics

- [ ] After scanning, click "Fetch Stats"
- [ ] Verify loading state
- [ ] Check statistics appear in cards
- [ ] Verify CloudWatch metrics (28 days) are displayed

#### 4. Real-time Monitoring

- [ ] Go to "Real-time" section
- [ ] Select one or more queues
- [ ] Click "Start Monitoring"
- [ ] Verify button turns red
- [ ] Check status messages appear
- [ ] Publish a test message to SNS topic
- [ ] Verify message appears in log (< 8 seconds)
- [ ] Click "Clear" to clear log
- [ ] Click "Stop Monitoring"
- [ ] Verify button turns orange

#### 5. Pipeline/Diagram

- [ ] Go to "Pipeline" section
- [ ] Select topics and queues
- [ ] Verify Mermaid diagram updates
- [ ] Check diagram renders correctly
- [ ] Try "All" and "None" buttons

#### 6. Exports

- [ ] Click "Export" in navigation
- [ ] Test each export format:
  - [ ] JSON
  - [ ] SQL
  - [ ] Draw.io
  - [ ] Mermaid
  - [ ] JSON Canvas
- [ ] Verify files download correctly
- [ ] Check file contents are valid

#### 7. Navigation

- [ ] Test all navigation links:
  - [ ] [01] QUEUES → Dashboard
  - [ ] [02] TOPICS → Topics section
  - [ ] [03] PIPELINE → Pipeline section
  - [ ] [04] MONITOR → Real-time section
- [ ] Verify smooth scroll behavior
- [ ] Check active section highlighting

#### 8. UI/UX

- [ ] Test responsive design (resize browser)
- [ ] Verify glass panel spotlight effects (hover)
- [ ] Check animations (scroll, text scramble)
- [ ] Test modal open/close
- [ ] Verify status bar updates
- [ ] Check error messages display correctly

## Testing with Mock AWS Services

### Using LocalStack (Optional)

LocalStack provides local AWS services for testing:

```bash
# Install LocalStack
pip install localstack-client

# Start LocalStack (requires Docker)
localstack start

# Configure AWS CLI to use LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

Then use LocalStack endpoints in your tests.

### Manual Mock Testing

The unit tests use `unittest.mock` to mock boto3 clients. You can extend this pattern:

```python
from unittest.mock import patch, MagicMock

@patch('app.get_session')
def test_your_feature(mock_get_session):
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session
    # Configure mocks...
    # Run test...
```

## Frontend Testing

### Test React Components

```bash
# If using React testing library
npm install --save-dev @testing-library/react @testing-library/jest-dom
npm test
```

### Manual Browser Testing

1. Open browser developer tools (F12)
2. Check Console for JavaScript errors
3. Monitor Network tab for API calls
4. Verify API responses are correct
5. Test with different screen sizes

### Browser Compatibility

Test in:
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Common Issues and Solutions

### Issue: Tests fail with "keyring not available"

**Solution**: Tests mock keyring, but if running manually:
```python
# In app.py, keyring is optional
# Tests use mocks, so this shouldn't be an issue
```

### Issue: React components not loading

**Solution**: 
```bash
npm run build
# Ensure static/react/ contains built files
```

### Issue: Port 5000 already in use

**Solution**:
```bash
# Change port in app.py
app.run(debug=True, port=5001)
```

### Issue: AWS credentials errors

**Solution**: Use test credentials or mocks. For real testing, use valid AWS credentials with appropriate permissions.

## Performance Testing

### Load Testing

```bash
# Install locust
pip install locust

# Create locustfile.py
# Run load tests
locust -f locustfile.py
```

### Response Time Checks

- Scan should complete in < 30 seconds per region
- Statistics fetch should complete in < 60 seconds
- Real-time monitoring should show messages in < 8 seconds

## Integration Testing

### End-to-End Test Flow

1. Start application: `python app.py`
2. Open browser: `http://127.0.0.1:5000`
3. Enter credentials → Test connection → Scan resources
4. Fetch statistics → Verify data
5. Start monitoring → Publish test message → Verify display
6. Export data → Verify file download
7. Navigate sections → Verify smooth scroll

## Debugging

### Enable Debug Mode

Flask debug mode is enabled by default in `app.py`:
```python
app.run(debug=True, use_reloader=False)
```

### View Logs

- Backend: Check terminal where `python app.py` runs
- Frontend: Check browser console (F12)
- Network: Check Network tab in browser dev tools

### Common Debug Commands

```python
# In Python code
import logging
logging.basicConfig(level=logging.DEBUG)

# In JavaScript
console.log('Debug info:', data);
console.error('Error:', error);
```

## Continuous Integration

For CI/CD, you can run:

```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Build frontend
npm run build

# Run tests
python -m unittest discover tests

# Check code quality (optional)
pip install flake8 black
flake8 app.py aws_sns_sqs_map.py
black --check app.py aws_sns_sqs_map.py
```

## Next Steps

- Review [project-structure.md](project-structure.md) for architecture details
- Check [monitoring-behavior.md](monitoring-behavior.md) for monitoring specifics
- See [quickstart.md](quickstart.md) for user guide
