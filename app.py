#!/usr/bin/env python3
import os
import sys
import json
import webbrowser
import threading
import time
from typing import Dict, List, Optional

from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, send_file
import boto3
import keyring

# Import logic from existing map script to reuse AWS logic
# We need to make sure aws_sns_sqs_map is importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from aws_sns_sqs_map import get_session, build_inventory, to_mermaid

app = Flask(__name__)
SERVICE_NAME = "aws-sns-sqs-gui"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/credentials", methods=["GET", "POST"])
def credentials():
    if request.method == "GET":
        # Load saved credentials
        try:
            ak = keyring.get_password(SERVICE_NAME, "aws_access_key_id") or ""
            sk = keyring.get_password(SERVICE_NAME, "aws_secret_access_key") or ""
            st = keyring.get_password(SERVICE_NAME, "aws_session_token") or ""
            pf = keyring.get_password(SERVICE_NAME, "profile") or ""
            regs = keyring.get_password(SERVICE_NAME, "regions") or "eu-central-1"
            return jsonify({
                "access_key": ak,
                "secret_key": sk, # Security: In a real app, we might mask this
                "session_token": st,
                "profile": pf,
                "regions": regs,
                "remember": bool(ak or pf)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "POST":
        data = request.json
        remember = data.get("remember", False)
        
        ak = data.get("access_key", "").strip()
        sk = data.get("secret_key", "").strip()
        st = data.get("session_token", "").strip()
        pf = data.get("profile", "").strip()
        regs = data.get("regions", "").strip()

        if remember:
            try:
                keyring.set_password(SERVICE_NAME, "aws_access_key_id", ak) if ak else keyring.delete_password(SERVICE_NAME, "aws_access_key_id")
                keyring.set_password(SERVICE_NAME, "aws_secret_access_key", sk) if sk else keyring.delete_password(SERVICE_NAME, "aws_secret_access_key")
                keyring.set_password(SERVICE_NAME, "aws_session_token", st) if st else keyring.delete_password(SERVICE_NAME, "aws_session_token")
                keyring.set_password(SERVICE_NAME, "profile", pf) if pf else keyring.delete_password(SERVICE_NAME, "profile")
                keyring.set_password(SERVICE_NAME, "regions", regs) if regs else keyring.delete_password(SERVICE_NAME, "regions")
            except Exception as e:
                # Ignore keyring errors (e.g. if delete fails because not exists)
                pass
        else:
            # Clear credentials if remember is unchecked
             try:
                keyring.delete_password(SERVICE_NAME, "aws_access_key_id")
                keyring.delete_password(SERVICE_NAME, "aws_secret_access_key")
                keyring.delete_password(SERVICE_NAME, "aws_session_token")
                keyring.delete_password(SERVICE_NAME, "profile")
                keyring.delete_password(SERVICE_NAME, "regions")
             except:
                 pass

        return jsonify({"status": "saved" if remember else "cleared"})

@app.route("/api/test-connection", methods=["POST"])
def test_connection():
    data = request.json
    try:
        session = get_session(
            profile=data.get("profile"),
            access_key=data.get("access_key"),
            secret_key=data.get("secret_key"),
            session_token=data.get("session_token")
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return jsonify({
            "success": True,
            "account": identity.get("Account"),
            "arn": identity.get("Arn")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/scan", methods=["POST"])
def scan():
    data = request.json
    regions = [r.strip() for r in data.get("regions", "").split(",") if r.strip()]
    if not regions:
        regions = ["us-east-1"]

    try:
        session = get_session(
            profile=data.get("profile"),
            access_key=data.get("access_key"),
            secret_key=data.get("secret_key"),
            session_token=data.get("session_token")
        )
        inventory = build_inventory(session, regions)
        return jsonify(inventory)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats", methods=["POST"])
def get_stats():
    data = request.json
    # Expects a list of items with {arn, region, type}
    items = data.get("items", [])
    
    # Group by region to minimize session creation
    by_region = {}
    for item in items:
        r = item.get("region")
        if r not in by_region:
            by_region[r] = []
        by_region[r].append(item)

    results = {}
    
    try:
        # Credentials from request or keyring (simplified: assume same session as scan)
        # In a real app we might need to re-pass creds or store session
        # For now, let's re-use the credentials passed in the body
        session = get_session(
            profile=data.get("profile"),
            access_key=data.get("access_key"),
            secret_key=data.get("secret_key"),
            session_token=data.get("session_token")
        )

        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=28)  # 4 weeks

        for region, region_items in by_region.items():
            cw = session.client("cloudwatch", region_name=region)
            
            for item in region_items:
                arn = item.get("arn")
                rtype = item.get("type") # 'topic' or 'queue'
                name = item.get("name")
                
                metrics = {}
                
                try:
                    if rtype == 'topic':
                        # SNS: NumberOfMessagesPublished
                        resp = cw.get_metric_statistics(
                            Namespace='AWS/SNS',
                            MetricName='NumberOfMessagesPublished',
                            Dimensions=[{'Name': 'TopicName', 'Value': name}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,  # Daily granularity
                            Statistics=['Sum']
                        )
                        val = 0
                        if resp['Datapoints']:
                            # Sum all datapoints over the 28 days
                            val = int(sum(dp['Sum'] for dp in resp['Datapoints']))
                        metrics['published_28d'] = val
                        
                    elif rtype == 'queue':
                        # SQS: NumberOfMessagesSent, NumberOfMessagesReceived
                        for metric in ['NumberOfMessagesSent', 'NumberOfMessagesReceived']:
                            resp = cw.get_metric_statistics(
                                Namespace='AWS/SQS',
                                MetricName=metric,
                                Dimensions=[{'Name': 'QueueName', 'Value': name}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=86400,  # Daily granularity
                                Statistics=['Sum']
                            )
                            val = 0
                            if resp['Datapoints']:
                                # Sum all datapoints over the 28 days
                                val = int(sum(dp['Sum'] for dp in resp['Datapoints']))
                            metrics[metric.lower() + '_28d'] = val
                            
                except Exception as e:
                    metrics['error'] = str(e)
                
                results[arn] = metrics

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/monitor", methods=["POST"])
def monitor():
    """Real-time monitoring endpoint - returns recent message activity"""
    data = request.json
    items = data.get("items", [])
    
    # Group by region
    by_region = {}
    for item in items:
        r = item.get("region")
        if r not in by_region:
            by_region[r] = []
        by_region[r].append(item)
    
    results = []
    
    try:
        session = get_session(
            profile=data.get("profile"),
            access_key=data.get("access_key"),
            secret_key=data.get("secret_key"),
            session_token=data.get("session_token")
        )
        
        # Get metrics for the last 5 minutes
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        for region, region_items in by_region.items():
            cw = session.client("cloudwatch", region_name=region)
            
            for item in region_items:
                arn = item.get("arn")
                rtype = item.get("type")
                name = item.get("name")
                
                try:
                    if rtype == 'topic':
                        # SNS: NumberOfMessagesPublished
                        resp = cw.get_metric_statistics(
                            Namespace='AWS/SNS',
                            MetricName='NumberOfMessagesPublished',
                            Dimensions=[{'Name': 'TopicName', 'Value': name}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=60,  # 1-minute granularity
                            Statistics=['Sum']
                        )
                        
                        for dp in resp.get('Datapoints', []):
                            if dp['Sum'] > 0:
                                results.append({
                                    'timestamp': dp['Timestamp'].isoformat(),
                                    'type': 'published',
                                    'resource': name,
                                    'resource_type': 'topic',
                                    'arn': arn,
                                    'count': int(dp['Sum']),
                                    'region': region
                                })
                    
                    elif rtype == 'queue':
                        # SQS: NumberOfMessagesSent and NumberOfMessagesReceived
                        for metric_name, event_type in [
                            ('NumberOfMessagesSent', 'sent'),
                            ('NumberOfMessagesReceived', 'received')
                        ]:
                            resp = cw.get_metric_statistics(
                                Namespace='AWS/SQS',
                                MetricName=metric_name,
                                Dimensions=[{'Name': 'QueueName', 'Value': name}],
                                StartTime=start_time,
                                EndTime=end_time,
                                Period=60,  # 1-minute granularity
                                Statistics=['Sum']
                            )
                            
                            for dp in resp.get('Datapoints', []):
                                if dp['Sum'] > 0:
                                    results.append({
                                        'timestamp': dp['Timestamp'].isoformat(),
                                        'type': event_type,
                                        'resource': name,
                                        'resource_type': 'queue',
                                        'arn': arn,
                                        'count': int(dp['Sum']),
                                        'region': region
                                    })
                
                except Exception as e:
                    # Skip errors for individual resources
                    pass
        
        # Sort by timestamp descending (most recent first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/mermaid", methods=["POST"])
def export_mermaid():
    inventory = request.json
    try:
        content = to_mermaid(inventory)
        return jsonify({"content": content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/sql", methods=["POST"])
def export_sql():
    # Simple SQL generation based on inventory
    inventory = request.json
    try:
        ddl_parts = [
            "CREATE TABLE sns_topic (arn VARCHAR(2048) PRIMARY KEY, name VARCHAR(255), region VARCHAR(64));",
            "CREATE TABLE sqs_queue (arn VARCHAR(2048) PRIMARY KEY, name VARCHAR(255), url VARCHAR(2048), region VARCHAR(64));",
            "CREATE TABLE subscription (topic_arn VARCHAR(2048), queue_arn VARCHAR(2048), region VARCHAR(64), PRIMARY KEY (topic_arn, queue_arn));"
        ]
        
        # Generate INSERTs
        inserts = []
        for item in inventory:
            region = item.get("region", "")
            for t in item.get("topics", []):
                inserts.append(f"INSERT INTO sns_topic VALUES ('{t['arn']}', '{t['name']}', '{region}');")
            for q in item.get("queues", []):
                inserts.append(f"INSERT INTO sqs_queue VALUES ('{q['arn']}', '{q['name']}', '{q['url']}', '{region}');")
            for l in item.get("links", []):
                inserts.append(f"INSERT INTO subscription VALUES ('{l['from_arn']}', '{l['to_arn']}', '{region}');")

        return jsonify({"content": "\n".join(ddl_parts + [""] + inserts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export/drawio", methods=["POST"])
def export_drawio():
    inventory = request.json
    try:
        # Basic Draw.io XML structure
        xml_parts = [
            '<mxfile host="app.diagrams.net" modified="2023-01-01T00:00:00.000Z" agent="AWS-Manager" version="21.0.0" type="device">',
            '  <diagram id="aws-diagram" name="AWS Resources">',
            '    <mxGraphModel dx="1422" dy="798" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="827" pageHeight="1169" math="0" shadow="0">',
            '      <root>',
            '        <mxCell id="0" />',
            '        <mxCell id="1" parent="0" />'
        ]

        # Styles
        style_topic = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;"
        style_queue = "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;fillColor=#ffe6cc;strokeColor=#d79b00;fontStyle=1;"
        style_edge = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;"

        # Build subscription map: topic_arn -> [queue_arns]
        topic_to_queues = {}
        all_topics = set()
        all_queues = set()
        
        for item in inventory:
            for t in item.get("topics", []):
                all_topics.add(t["arn"])
                if t["arn"] not in topic_to_queues:
                    topic_to_queues[t["arn"]] = []
            
            for q in item.get("queues", []):
                all_queues.add(q["arn"])
            
            for link in item.get("links", []):
                topic_arn = link.get("from_arn")
                queue_arn = link.get("to_arn")
                if topic_arn and queue_arn:
                    if topic_arn not in topic_to_queues:
                        topic_to_queues[topic_arn] = []
                    topic_to_queues[topic_arn].append(queue_arn)
        
        # Find unsubscribed queues
        subscribed_queues = set()
        for queues in topic_to_queues.values():
            subscribed_queues.update(queues)
        unsubscribed_queues = all_queues - subscribed_queues
        
        # Find topics with no subscriptions
        topics_with_subs = [t for t in all_topics if topic_to_queues.get(t)]
        topics_without_subs = [t for t in all_topics if not topic_to_queues.get(t)]
        
        # Get topic and queue objects
        topic_map = {}
        queue_map = {}
        for item in inventory:
            for t in item.get("topics", []):
                topic_map[t["arn"]] = t
            for q in item.get("queues", []):
                queue_map[q["arn"]] = q
        
        # Layout parameters
        arn_to_id = {}
        current_id = 2
        
        start_x = 40
        column_width = 200
        topic_y = 40
        queue_start_y = 150
        queue_spacing_y = 80
        topic_w = 160
        topic_h = 60
        queue_w = 120
        queue_h = 60
        
        current_x = start_x
        
        # Layout topics with subscriptions and their queues
        for topic_arn in topics_with_subs:
            topic = topic_map.get(topic_arn)
            if not topic:
                continue
            
            # Add topic
            xml_parts.append(f'        <mxCell id="{current_id}" value="{topic["name"]}" style="{style_topic}" vertex="1" parent="1">')
            xml_parts.append(f'          <mxGeometry x="{current_x}" y="{topic_y}" width="{topic_w}" height="{topic_h}" as="geometry" />')
            xml_parts.append('        </mxCell>')
            arn_to_id[topic_arn] = current_id
            current_id += 1
            
            # Add subscribed queues below this topic
            queue_y = queue_start_y
            for queue_arn in topic_to_queues[topic_arn]:
                queue = queue_map.get(queue_arn)
                if not queue or queue_arn in arn_to_id:
                    continue
                
                xml_parts.append(f'        <mxCell id="{current_id}" value="{queue["name"]}" style="{style_queue}" vertex="1" parent="1">')
                xml_parts.append(f'          <mxGeometry x="{current_x}" y="{queue_y}" width="{queue_w}" height="{queue_h}" as="geometry" />')
                xml_parts.append('        </mxCell>')
                arn_to_id[queue_arn] = current_id
                current_id += 1
                queue_y += queue_spacing_y
            
            # Move to next column
            current_x += column_width
        
        # Add topics without subscriptions
        for topic_arn in topics_without_subs:
            topic = topic_map.get(topic_arn)
            if not topic:
                continue
            
            xml_parts.append(f'        <mxCell id="{current_id}" value="{topic["name"]}" style="{style_topic}" vertex="1" parent="1">')
            xml_parts.append(f'          <mxGeometry x="{current_x}" y="{topic_y}" width="{topic_w}" height="{topic_h}" as="geometry" />')
            xml_parts.append('        </mxCell>')
            arn_to_id[topic_arn] = current_id
            current_id += 1
            current_x += column_width
        
        # Add unsubscribed queues at the end
        queue_y = queue_start_y
        for queue_arn in unsubscribed_queues:
            queue = queue_map.get(queue_arn)
            if not queue:
                continue
            
            xml_parts.append(f'        <mxCell id="{current_id}" value="{queue["name"]}" style="{style_queue}" vertex="1" parent="1">')
            xml_parts.append(f'          <mxGeometry x="{current_x}" y="{queue_y}" width="{queue_w}" height="{queue_h}" as="geometry" />')
            xml_parts.append('        </mxCell>')
            arn_to_id[queue_arn] = current_id
            current_id += 1
            queue_y += queue_spacing_y
            
            # If too many unsubscribed queues, move to next column
            if queue_y > 600:
                current_x += column_width
                queue_y = queue_start_y

        # Add Links
        for item in inventory:
            for l in item.get("links", []):
                source_id = arn_to_id.get(l["from_arn"])
                target_id = arn_to_id.get(l["to_arn"])
                
                if source_id and target_id:
                    xml_parts.append(f'        <mxCell id="{current_id}" value="" style="{style_edge}" edge="1" parent="1" source="{source_id}" target="{target_id}">')
                    xml_parts.append('          <mxGeometry relative="1" as="geometry" />')
                    xml_parts.append('        </mxCell>')
                    current_id += 1

        xml_parts.append('      </root>')
        xml_parts.append('    </mxGraphModel>')
        xml_parts.append('  </diagram>')
        xml_parts.append('</mxfile>')

        return jsonify({"content": "\n".join(xml_parts)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    app.run(debug=True, use_reloader=False)
