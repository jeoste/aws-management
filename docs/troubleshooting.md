# Troubleshooting Guide

## Common Issues and Solutions

### pip command not found

**Problem**: `pip` command is not found even though Python is installed.

**Solution 1**: Use `python3 -m pip` instead:
```bash
python3 -m pip install -r requirements.txt
```

**Solution 2**: Add pip to your PATH permanently:

```bash
# Add to ~/.zshrc
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Or run the setup script:
```bash
./setup-path.sh
source ~/.zshrc
```

**Solution 3**: Use pip3 directly:
```bash
pip3 install -r requirements.txt
```

### pip version warning

**Problem**: Warning about pip version mismatch.

**Solution**: Upgrade pip using the method that works:
```bash
python3 -m pip install --upgrade pip
# or
pip3 install --upgrade pip
```

### Virtual environment issues

**Problem**: Cannot activate virtual environment.

**Solution**:
```bash
# Make sure you're using python3
python3 -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### Port already in use

**Problem**: Port 5000 is already in use.

**Solution**: Change the port in `app.py`:
```python
app.run(debug=True, port=5001)
```

Or kill the process using port 5000:
```bash
lsof -ti:5000 | xargs kill -9
```

### React components not loading

**Problem**: Diagram checkboxes not appearing.

**Solution**:
```bash
# Install Node.js dependencies
npm install

# Build React components
npm run build

# Verify files exist
ls -la static/react/
```

### AWS credentials errors

**Problem**: "The security token included in the request is invalid"

**Solution**:
- Your session token has expired
- Generate new credentials from AWS console
- Make sure you're using Access Key + Secret + Session Token (for IAM roles)

### Module not found errors

**Problem**: `ModuleNotFoundError` when running the app.

**Solution**:
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import flask; import boto3; print('OK')"
```

### Permission denied errors

**Problem**: Cannot write to files or directories.

**Solution**:
```bash
# Check file permissions
ls -la

# Fix permissions if needed
chmod +x app.py
chmod -R u+w .
```

### Browser doesn't open automatically

**Problem**: Application starts but browser doesn't open.

**Solution**: Manually open `http://127.0.0.1:5000` in your browser.

### Real-time monitoring not working

**Problem**: No messages appearing in real-time monitoring.

**Solutions**:
1. Verify you have selected queues
2. Check IAM permissions (sqs:ReceiveMessage, sqs:ChangeMessageVisibility)
3. Verify queues have messages
4. Check browser console (F12) for errors
5. Check backend terminal for error messages

See [monitoring-behavior.md](monitoring-behavior.md) for detailed troubleshooting.

### Mermaid diagrams not rendering

**Problem**: Diagram section shows code instead of diagram.

**Solution**:
1. Check browser console for JavaScript errors
2. Verify Mermaid library is loaded (check Network tab)
3. Try refreshing the page
4. Check that resources are selected

### Export files are empty or corrupted

**Problem**: Exported files are empty or invalid.

**Solution**:
1. Make sure you've scanned resources first
2. Check browser console for errors
3. Verify you have data to export
4. Try a different export format

## Getting Help

1. Check the [testing guide](testing.md) for debugging techniques
2. Review [project structure](project-structure.md) for architecture details
3. Check browser console (F12) for frontend errors
4. Check terminal where `python app.py` runs for backend errors
5. Verify AWS credentials and permissions

## System Requirements

- Python 3.9 or higher
- Node.js 16+ (for React components)
- Modern browser (Chrome, Firefox, Safari, Edge)
- AWS account with appropriate IAM permissions
