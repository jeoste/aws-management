# Changelog

## [2.5.0] - 2025-01-XX

### Design Migration

**Major Changes:**
- Complete UI redesign based on modern dark theme
- Migration from tab-based interface to scrollable sections
- Glass panel cards with spotlight effects
- GSAP animations and Lenis smooth scroll integration

### New Features

#### Modern Interface
- Dark theme with glass panels and spotlight effects
- Smooth scroll navigation with section anchors
- Hero section with call-to-action
- Dashboard with real-time statistics cards
- Responsive design for mobile and desktop

#### Enhanced User Experience
- Credentials modal instead of sidebar
- Export menu in navigation
- Status bar at bottom of page
- Region indicator in navigation
- Improved visual feedback for all actions

### Technical Improvements

- Updated JavaScript to work with new DOM structure
- Converted tables to glass panel cards
- Adapted all UI functions for new design system
- Maintained all existing functionality
- Improved code organization

## [2.0.0] - 2025-11-23

### Migration to Flask Web Interface

**Breaking Changes:**
- Complete removal of Tkinter interface (`aws_sns_sqs_gui.py`)
- Main application is now `app.py` instead of `aws_sns_sqs_gui.py`

### New Features

#### Modern Web Interface
- Flask web interface with TailwindCSS
- Tab-based navigation (Topics, Queues, Links, Diagram, Real-time)
- Light/dark theme
- Responsive and modern design

#### Real-time Monitoring
- **Direct SQS polling** replacing CloudWatch Metrics (delay reduced from several minutes to < 4 seconds)
- Automatic monitoring of queues subscribed to selected topics
- Message display with complete content
- Non-destructive reading (visibility timeout = 0)
- Icons and colors to quickly identify event types
- History of maximum 100 messages

#### CloudWatch Statistics
- Metrics over 28 days (messages published, sent, received)
- Display in resource tables

#### Multiple Exports
- JSON
- SQL (CREATE TABLE + INSERT)
- Draw.io (.drawio)
- Mermaid (diagram)

#### Credentials Management
- Secure storage with keyring (operating system)
- "Remember credentials" checkbox
- Full IAM role support (Access Key + Secret + Session Token)

### Technical Improvements

- Better error handling with explicit messages
- SQS polling with `WaitTimeSeconds=2` for latency reduction
- Automatic extraction of SQS message timestamps
- Link grouping by topic in interface
- Refactored and better organized code

### Removed Files

- `aws_sns_sqs_gui.py` (obsolete Tkinter interface)
- `test_output.txt` (obsolete test output)
- `__pycache__/aws_sns_sqs_gui.cpython-312.pyc`

### Documentation

- README updated with complete instructions for web interface
- Removed Tkinter references
- Added .gitignore to avoid cache files

### Migration

To migrate from previous version:

**Before:**
```bash
python aws_sns_sqs_gui.py
```

**Now:**
```bash
python app.py
```

The application opens automatically in your browser.

### Bug Fixes

- Fix: SQS messages now appear instantly (< 4s)
- Fix: Correct synchronization between scan and Real-time tab
- Fix: Better polling error handling with interface display
- Fix: Better queue URL resolution from ARNs
