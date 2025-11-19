import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'AWS SNS/SQS Manager', response.data)

    @patch('app.keyring')
    def test_credentials_get(self, mock_keyring):
        mock_keyring.get_password.return_value = "test-value"
        response = self.app.get('/api/credentials')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['access_key'], "test-value")

    @patch('app.get_session')
    def test_scan(self, mock_get_session):
        # Mock session and clients
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Mock SNS client
        mock_sns = MagicMock()
        mock_session.client.return_value = mock_sns
        
        # Mock paginators
        mock_paginator = MagicMock()
        mock_sns.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [] # Empty results for simplicity

        response = self.app.post('/api/scan', json={
            "regions": "us-east-1",
            "access_key": "test",
            "secret_key": "test"
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_export_drawio(self):
        # Test with dummy inventory
        inventory = [{
            "region": "us-east-1",
            "topics": [{"arn": "arn:aws:sns:us-east-1:123:topic1", "name": "topic1"}],
            "queues": [{"arn": "arn:aws:sqs:us-east-1:123:queue1", "name": "queue1", "url": "http://queue1"}],
            "links": [{"from_arn": "arn:aws:sns:us-east-1:123:topic1", "to_arn": "arn:aws:sqs:us-east-1:123:queue1"}]
        }]
        
        response = self.app.post('/api/export/drawio', json=inventory)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('<mxfile', data['content'])
        self.assertIn('topic1', data['content'])
        self.assertIn('queue1', data['content'])

        self.assertIn('topic1', data['content'])
        self.assertIn('queue1', data['content'])

    @patch('app.get_session')
    def test_stats(self, mock_get_session):
        # Mock session and cloudwatch
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_cw = MagicMock()
        mock_session.client.return_value = mock_cw
        
        # Mock metric response
        mock_cw.get_metric_statistics.return_value = {
            'Datapoints': [{'Sum': 42}]
        }

        data = {
            "items": [
                {"arn": "arn:aws:sns:us-east-1:123:topic1", "name": "topic1", "region": "us-east-1", "type": "topic"},
                {"arn": "arn:aws:sqs:us-east-1:123:queue1", "name": "queue1", "region": "us-east-1", "type": "queue"}
            ]
        }
        
        response = self.app.post('/api/stats', json=data)
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        
        self.assertIn("arn:aws:sns:us-east-1:123:topic1", result)
        self.assertEqual(result["arn:aws:sns:us-east-1:123:topic1"]["published_24h"], 42)

if __name__ == '__main__':
    unittest.main()
