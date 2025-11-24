#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

# boto3 and botocore are imported lazily inside functions so that the CLI --help
# can be displayed even if the packages are not installed.


@dataclass
class Topic:
    arn: str
    name: str


@dataclass
class Queue:
    arn: str
    url: str
    name: str


@dataclass
class Link:
    from_arn: str
    to_arn: str
    protocol: str
    attributes: Dict[str, str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventorier SNS/SQS et générer JSON ou Mermaid")
    parser.add_argument("--region", action="append", required=True, help="Région AWS (répétable)")
    parser.add_argument("--profile", default=None, help="Profil AWS à utiliser")
    parser.add_argument("--aws-access-key-id", default=None, help="AWS Access Key ID (optionnel)")
    parser.add_argument("--aws-secret-access-key", default=None, help="AWS Secret Access Key (optionnel; si omis et --aws-access-key-id fourni, vous serez invité)")
    parser.add_argument("--aws-session-token", default=None, help="AWS Session Token (optionnel)")
    parser.add_argument("--format", choices=["json", "mermaid"], default="json", help="Format de sortie")
    parser.add_argument("--output", default=None, help="Chemin de fichier de sortie (sinon stdout)")
    return parser.parse_args()


def get_session(profile: Optional[str], access_key: Optional[str], secret_key: Optional[str], session_token: Optional[str]):
    """
    Retourne une session boto3.

    Priorité (de la plus haute à la plus basse):
    - Si --aws-access-key-id est fourni, utilise les clés passées en argument (prompt pour le secret si omis).
    - Si --profile est fourni, utilise le profil.
    - Sinon, laisse boto3 utiliser sa résolution par défaut (env, shared config, SSO, etc.).
    """
    # Import boto3 only when actually creating a session
    try:
        import boto3
    except Exception:
        raise

    if access_key:
        if not secret_key:
            # Ne pas obliger à passer le secret sur la ligne de commande : prompt sécurisé
            secret_key = getpass.getpass("AWS Secret Access Key: ")
        return boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, aws_session_token=session_token)
    if profile:
        return boto3.Session(profile_name=profile)
    return boto3.Session()


def list_topics(sns_client) -> List[Topic]:
    topics: List[Topic] = []
    paginator = sns_client.get_paginator("list_topics")
    for page in paginator.paginate():
        for t in page.get("Topics", []):
            arn = t["TopicArn"]
            name = arn.split(":")[-1]
            topics.append(Topic(arn=arn, name=name))
    return topics


def list_queues(sqs_client) -> List[Queue]:
    queues: List[Queue] = []
    queue_urls: List[str] = []
    
    # First, collect all queue URLs
    paginator = sqs_client.get_paginator("list_queues")
    for page in paginator.paginate():
        queue_urls.extend(page.get("QueueUrls", []) or [])
    
    # Parallelize get_queue_attributes calls
    def get_queue_info(url: str) -> Queue:
        attrs = sqs_client.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])
        arn = attrs.get("Attributes", {}).get("QueueArn", "")
        name = url.rsplit("/", 1)[-1]
        return Queue(arn=arn, url=url, name=name)
    
    # Use ThreadPoolExecutor to fetch queue attributes in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_queue_info, url): url for url in queue_urls}
        for future in as_completed(futures):
            try:
                queue = future.result()
                queues.append(queue)
            except Exception as e:
                # Skip queues that fail to fetch attributes
                pass
    
    return queues


def list_links_sns_to_sqs(sns_client, topics: List[Topic]) -> List[Link]:
    links: List[Link] = []
    for topic in topics:
        paginator = sns_client.get_paginator("list_subscriptions_by_topic")
        for page in paginator.paginate(TopicArn=topic.arn):
            for sub in page.get("Subscriptions", []) or []:
                protocol = sub.get("Protocol")
                endpoint = sub.get("Endpoint")
                sub_arn = sub.get("SubscriptionArn")
                if protocol == "sqs" and endpoint:
                    # endpoint est normalement l'ARN de la file SQS
                    attributes = {"subscriptionArn": sub_arn or ""}
                    links.append(Link(from_arn=topic.arn, to_arn=endpoint, protocol=protocol, attributes=attributes))
    return links


def fetch_region_inventory(session: boto3.Session, region: str) -> Dict[str, object]:
    """Fetch inventory for a single region with parallel API calls."""
    from botocore.config import Config  # type: ignore
    
    config = Config(retries={"max_attempts": 5, "mode": "standard"})
    sns = session.client("sns", region_name=region, config=config)
    sqs = session.client("sqs", region_name=region, config=config)
    
    # Parallelize topics and queues fetching
    topics: List[Topic] = []
    queues: List[Queue] = []
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_topics = executor.submit(list_topics, sns)
        future_queues = executor.submit(list_queues, sqs)
        
        topics = future_topics.result()
        queues = future_queues.result()
    
    # Fetch links after we have topics
    links = list_links_sns_to_sqs(sns, topics)
    
    # Déterminer accountId depuis un ARN existant si possible
    account_id: Optional[str] = None
    candidate_arn = (topics[0].arn if topics else (queues[0].arn if queues else None))
    if candidate_arn:
        parts = candidate_arn.split(":")
        if len(parts) >= 5:
            account_id = parts[4]
    
    return {
        "region": region,
        "accountId": account_id,
        "topics": [asdict(t) for t in topics],
        "queues": [asdict(q) for q in queues],
        "links": [asdict(l) for l in links],
    }


def build_inventory(session: boto3.Session, regions: List[str]) -> List[Dict[str, object]]:
    """Build inventory for multiple regions in parallel."""
    inventory: List[Dict[str, object]] = []
    
    # Parallelize across regions
    max_workers = min(len(regions), 10)  # Limit to avoid throttling
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_region_inventory, session, region): region for region in regions}
        
        for future in as_completed(futures):
            region = futures[future]
            try:
                region_inventory = future.result()
                inventory.append(region_inventory)
            except Exception as e:
                # Log error but continue with other regions
                print(f"Error fetching inventory for region {region}: {e}", file=sys.stderr)
    
    return inventory


def to_mermaid(inventory: List[Dict[str, object]]) -> str:
    lines: List[str] = ["graph LR"]
    for item in inventory:
        account = item.get("accountId")
        region = item.get("region") or "?"
        topics: List[Dict[str, str]] = item.get("topics", [])  # type: ignore
        queues: List[Dict[str, str]] = item.get("queues", [])  # type: ignore
        links: List[Dict[str, object]] = item.get("links", [])  # type: ignore

        # Only include accountId in subgraph title if it's available
        if account:
            lines.append(f"  subgraph {account} {region}")
        else:
            lines.append(f"  subgraph {region}")
        # Map ids stables pour Mermaid
        topic_ids: Dict[str, str] = {}
        queue_ids: Dict[str, str] = {}

        for idx, t in enumerate(topics, start=1):
            tid = f"T{idx}"
            topic_ids[t["arn"]] = tid
            label = t["name"].replace("\"", "'")
            lines.append(f"    {tid}[Topic: {label}]:::topic")

        for idx, q in enumerate(queues, start=1):
            qid = f"Q{idx}"
            queue_ids[q["arn"]] = qid
            label = q["name"].replace("\"", "'")
            lines.append(f"    {qid}(Queue: {label}):::queue")

        for l in links:
            from_arn = l.get("from_arn")  # type: ignore
            to_arn = l.get("to_arn")  # type: ignore
            tid = topic_ids.get(from_arn, None)
            qid = queue_ids.get(to_arn, None)
            if tid and qid:
                lines.append(f"    {tid} --> {qid}")
        lines.append("  end")

    # Styles Linear-inspired: bleu subtil pour topics, gris neutre pour queues
    # Primary blue: #5E6AD2 (Linear's signature blue)
    # Muted gray: #9B9B9B (neutral gray)
    # Background: white
    lines.append("\nclassDef topic fill:#5E6AD2,stroke:#5E6AD2,stroke-width:1.5px,color:#ffffff;")
    lines.append("classDef queue fill:#9B9B9B,stroke:#9B9B9B,stroke-width:1.5px,color:#ffffff;")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    session = get_session(args.profile, args.aws_access_key_id, args.aws_secret_access_key, args.aws_session_token)
    inventory = build_inventory(session, args.region)

    if args.format == "json":
        output = json.dumps(inventory, indent=2)
    else:
        output = to_mermaid(inventory)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output + ("\n" if not output.endswith("\n") else ""))
    else:
        sys.stdout.write(output + ("\n" if not output.endswith("\n") else ""))


if __name__ == "__main__":
    main()



