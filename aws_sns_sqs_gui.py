#!/usr/bin/env python3
"""
Tkinter GUI to enter AWS credentials/profile and list SNS topics, SQS queues and SNS->SQS subscriptions.

This file keeps boto3 imports lazy so the UI can start even if boto3 is not installed; attempting
to query AWS without boto3 will raise a clear error.
"""
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Optional


def get_session(access_key: Optional[str], secret_key: Optional[str], session_token: Optional[str], profile: Optional[str]):
    try:
        import boto3
    except Exception as e:
        raise RuntimeError("boto3 is required to access AWS: " + str(e))

    if access_key:
        return boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key, aws_session_token=session_token)
    if profile:
        return boto3.Session(profile_name=profile)
    return boto3.Session()


def list_topics(session, region: str) -> List[Dict[str, str]]:
    sns = session.client("sns", region_name=region)
    topics = []
    paginator = sns.get_paginator("list_topics")
    for page in paginator.paginate():
        for t in page.get("Topics", []):
            arn = t.get("TopicArn")
            name = arn.split(":")[-1] if arn else ""
            topics.append({"arn": arn, "name": name, "region": region})
    return topics


def list_queues(session, region: str) -> List[Dict[str, str]]:
    sqs = session.client("sqs", region_name=region)
    queues = []
    paginator = sqs.get_paginator("list_queues")
    for page in paginator.paginate():
        for url in page.get("QueueUrls", []) or []:
            attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"]) or {}
            arn = attrs.get("Attributes", {}).get("QueueArn", "")
            name = url.rsplit("/", 1)[-1]
            queues.append({"arn": arn, "url": url, "name": name, "region": region})
    return queues


def list_links_for_region(session, region: str) -> List[Dict[str, str]]:
    sns = session.client("sns", region_name=region)
    links = []
    # list topics first
    topics = []
    tp_p = sns.get_paginator("list_topics")
    for page in tp_p.paginate():
        for t in page.get("Topics", []):
            arn = t.get("TopicArn")
            name = arn.split(":")[-1] if arn else ""
            topics.append({"arn": arn, "name": name})

    for topic in topics:
        t_arn = topic.get("arn")
        if not t_arn:
            continue
        sub_p = sns.get_paginator("list_subscriptions_by_topic")
        for p in sub_p.paginate(TopicArn=t_arn):
            for sub in p.get("Subscriptions", []) or []:
                if sub.get("Protocol") == "sqs":
                    endpoint = sub.get("Endpoint")
                    if not endpoint:
                        continue
                    qname = endpoint.split(":")[-1]
                    links.append({
                        "topic_arn": t_arn,
                        "topic_name": topic.get("name"),
                        "queue_arn": endpoint,
                        "queue_name": qname,
                        "region": region,
                    })
    return links


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AWS SNS/SQS Browser")

        frm = ttk.Frame(root, padding=12)
        frm.grid(sticky="nsew")

        # Credentials
        creds = ttk.LabelFrame(frm, text="Credentials / Profil")
        creds.grid(row=0, column=0, sticky="ew")

        ttk.Label(creds, text="Access Key ID:").grid(row=0, column=0, sticky="w")
        self.access_key = ttk.Entry(creds, width=50)
        self.access_key.grid(row=0, column=1, sticky="w")

        ttk.Label(creds, text="Secret Access Key:").grid(row=1, column=0, sticky="w")
        self.secret_key = ttk.Entry(creds, width=50, show="*")
        self.secret_key.grid(row=1, column=1, sticky="w")

        ttk.Label(creds, text="Session Token:").grid(row=2, column=0, sticky="w")
        self.session_token = ttk.Entry(creds, width=50)
        self.session_token.grid(row=2, column=1, sticky="w")

        ttk.Label(creds, text="Profile:").grid(row=3, column=0, sticky="w")
        self.profile = ttk.Entry(creds, width=30)
        self.profile.grid(row=3, column=1, sticky="w")

        # Regions
        ttk.Label(frm, text="Régions (séparées par des virgules):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.regions = ttk.Entry(frm, width=60)
        self.regions.insert(0, "eu-central-1")
        self.regions.grid(row=2, column=0, sticky="w")

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Prêt")
        status_bar = ttk.Label(frm, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # Buttons
        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Button(btns, text="Lister Topics", command=self.list_topics_action).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btns, text="Lister Queues", command=self.list_queues_action).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(btns, text="Lister tout", command=self.list_both_action).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(btns, text="Lister Subscriptions", command=self.list_links_action).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(btns, text="Exporter JSON", command=self.export_json).grid(row=0, column=4, padx=(20, 6))
        ttk.Button(btns, text="Générer Mermaid", command=self.generate_mermaid).grid(row=0, column=5, padx=(20, 6))
        ttk.Button(btns, text="Générer Draw.io", command=self.generate_drawio).grid(row=0, column=6, padx=(20, 6))
        ttk.Button(btns, text="Tester Connexion", command=self.test_connection).grid(row=0, column=7, padx=(20, 6))

        # Results
        res_frame = ttk.Frame(frm)
        res_frame.grid(row=5, column=0, sticky="nsew", pady=(12, 0))
        root.rowconfigure(5, weight=1)
        root.columnconfigure(0, weight=1)

        # Topics listbox
        topics_frame = ttk.LabelFrame(res_frame, text="Topics")
        topics_frame.grid(row=0, column=0, sticky="nsew")
        topics_frame.columnconfigure(0, weight=1)
        topics_frame.rowconfigure(0, weight=1)
        self.topics_list = tk.Listbox(topics_frame, width=90, height=15, exportselection=False)
        self.topics_list.grid(row=0, column=0, sticky="nsew")
        topics_hsb = ttk.Scrollbar(topics_frame, orient="horizontal", command=self.topics_list.xview)
        topics_hsb.grid(row=1, column=0, sticky="ew")
        self.topics_list.configure(xscrollcommand=topics_hsb.set)

        # Queues listbox
        queues_frame = ttk.LabelFrame(res_frame, text="Queues")
        queues_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        queues_frame.columnconfigure(0, weight=1)
        queues_frame.rowconfigure(0, weight=1)
        self.queues_list = tk.Listbox(queues_frame, width=90, height=15, exportselection=False)
        self.queues_list.grid(row=0, column=0, sticky="nsew")
        queues_hsb = ttk.Scrollbar(queues_frame, orient="horizontal", command=self.queues_list.xview)
        queues_hsb.grid(row=1, column=0, sticky="ew")
        self.queues_list.configure(xscrollcommand=queues_hsb.set)

        # Links listbox (SNS -> SQS)
        links_frame = ttk.LabelFrame(res_frame, text="Subscriptions (SNS -> SQS)")
        links_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8,0))
        links_frame.columnconfigure(0, weight=1)
        links_frame.rowconfigure(0, weight=1)
        self.links_list = tk.Listbox(links_frame, width=140, height=8, exportselection=False)
        self.links_list.grid(row=0, column=0, sticky="nsew")
        links_hsb = ttk.Scrollbar(links_frame, orient="horizontal", command=self.links_list.xview)
        links_hsb.grid(row=1, column=0, sticky="ew")
        self.links_list.configure(xscrollcommand=links_hsb.set)

        for child in frm.winfo_children():
            child.grid_configure(padx=4, pady=2)

        # Data storage
        self.latest_inventory = {"topics": [], "queues": [], "links": []}

    def parse_regions(self) -> List[str]:
        txt = self.regions.get().strip()
        if not txt:
            return ["us-east-1"]
        return [r.strip() for r in txt.split(",") if r.strip()]

    def run_in_thread(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def list_topics_action(self):
        self.run_in_thread(self._list_topics)

    def list_queues_action(self):
        self.run_in_thread(self._list_queues)

    def list_both_action(self):
        self.run_in_thread(self._list_both)

    def list_links_action(self):
        self.run_in_thread(self._list_links)

    def test_connection(self):
        self.run_in_thread(self._test_connection)

    def _test_connection(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Test de connexion en cours..."))
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            
            # Tester avec STS pour obtenir les infos du compte
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            account_id = identity.get("Account", "Inconnu")
            user_arn = identity.get("Arn", "Inconnu")
            
            success_msg = f"Connexion réussie ! Compte: {account_id}\nUtilisateur: {user_arn}"
            self.root.after(0, lambda: self.status_var.set(f"Connecté - Compte: {account_id}"))
            self.root.after(0, lambda: messagebox.showinfo("Connexion réussie", success_msg))
            
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur de connexion"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à AWS:\n\n{err}"))

    def _list_topics(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération des topics SNS..."))
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            regions = self.parse_regions()
            all_topics = []
            for r in regions:
                self.root.after(0, lambda r=r: self.status_var.set(f"Récupération des topics dans {r}..."))
                all_topics.extend(list_topics(session, r))

            self.latest_inventory["topics"] = all_topics
            self.root.after(0, lambda topics=all_topics: self._update_topics_list(topics))
            self.root.after(0, lambda: self.status_var.set(f"Récupéré {len(all_topics)} topics"))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur lors de la récupération"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur", f"Erreur lors de la récupération des topics:\n\n{err}"))

    def _list_queues(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération des queues SQS..."))
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            regions = self.parse_regions()
            all_queues = []
            for r in regions:
                self.root.after(0, lambda r=r: self.status_var.set(f"Récupération des queues dans {r}..."))
                all_queues.extend(list_queues(session, r))

            self.latest_inventory["queues"] = all_queues
            self.root.after(0, lambda queues=all_queues: self._update_queues_list(queues))
            self.root.after(0, lambda: self.status_var.set(f"Récupéré {len(all_queues)} queues"))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur lors de la récupération"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur", f"Erreur lors de la récupération des queues:\n\n{err}"))

    def _list_both(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération complète en cours..."))
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            regions = self.parse_regions()
            all_topics = []
            all_queues = []
            all_links = []
            for r in regions:
                self.root.after(0, lambda r=r: self.status_var.set(f"Récupération dans {r}..."))
                all_topics.extend(list_topics(session, r))
                all_queues.extend(list_queues(session, r))
                all_links.extend(list_links_for_region(session, r))

            self.latest_inventory["topics"] = all_topics
            self.latest_inventory["queues"] = all_queues
            self.latest_inventory["links"] = all_links
            self.root.after(0, lambda topics=all_topics: self._update_topics_list(topics))
            self.root.after(0, lambda queues=all_queues: self._update_queues_list(queues))
            self.root.after(0, lambda links=all_links: self._update_links_list(links))
            self.root.after(0, lambda: self.status_var.set(f"Récupéré {len(all_topics)} topics, {len(all_queues)} queues, {len(all_links)} liens"))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur lors de la récupération"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur", f"Erreur lors de la récupération complète:\n\n{err}"))

    def _update_topics_list(self, topics):
        self.topics_list.delete(0, tk.END)
        for t in topics:
            display = f"{t.get('region','?')} | {t.get('name','?')} | {t.get('arn','') }"
            self.topics_list.insert(tk.END, display)

    def _update_queues_list(self, queues):
        self.queues_list.delete(0, tk.END)
        for q in queues:
            display = f"{q.get('region','?')} | {q.get('name','?')} | {q.get('arn','')} | {q.get('url','')}"
            self.queues_list.insert(tk.END, display)

    def export_json(self):
        if not self.latest_inventory["topics"] and not self.latest_inventory["queues"] and not self.latest_inventory["links"]:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Lancer une lecture d'abord.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json" )])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.latest_inventory, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Export", f"Export JSON enregistré: {path}")

    def generate_mermaid(self):
        if not self.latest_inventory["topics"] and not self.latest_inventory["queues"] and not self.latest_inventory["links"]:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Lancer une lecture d'abord.")
            return
        
        # Convertir les données au format attendu par aws_sns_sqs_map.py
        inventory = []
        regions_data = {}
        
        # Grouper par région
        for topic in self.latest_inventory["topics"]:
            region = topic.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["topics"].append({
                "arn": topic.get("arn", ""),
                "name": topic.get("name", "")
            })
        
        for queue in self.latest_inventory["queues"]:
            region = queue.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["queues"].append({
                "arn": queue.get("arn", ""),
                "name": queue.get("name", ""),
                "url": queue.get("url", "")
            })
        
        for link in self.latest_inventory["links"]:
            region = link.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["links"].append({
                "from_arn": link.get("topic_arn", ""),
                "to_arn": link.get("queue_arn", ""),
                "protocol": "sqs",
                "attributes": {}
            })
        
        # Créer l'inventaire final
        for region, data in regions_data.items():
            account_id = None
            # Essayer de déterminer l'account ID depuis un ARN
            for topic in data["topics"]:
                if topic["arn"]:
                    parts = topic["arn"].split(":")
                    if len(parts) >= 5:
                        account_id = parts[4]
                        break
            
            inventory.append({
                "region": region,
                "accountId": account_id,
                "topics": data["topics"],
                "queues": data["queues"],
                "links": data["links"]
            })
        
        # Générer le diagramme Mermaid
        try:
            from aws_sns_sqs_map import to_mermaid
            mermaid_content = to_mermaid(inventory)
            
            # Sauvegarder le fichier
            path = filedialog.asksaveasfilename(defaultextension=".mmd", filetypes=[("Mermaid","*.mmd"), ("Text","*.txt")])
            if not path:
                return
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(mermaid_content)
            
            messagebox.showinfo("Export", f"Diagramme Mermaid enregistré: {path}")
        except Exception as exc:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du diagramme Mermaid: {exc}")

    def generate_drawio(self):
        if not self.latest_inventory["topics"] and not self.latest_inventory["queues"] and not self.latest_inventory["links"]:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Lancer une lecture d'abord.")
            return
        
        try:
            # Générer le diagramme Draw.io
            drawio_content = self._create_drawio_diagram()
            
            # Sauvegarder le fichier
            path = filedialog.asksaveasfilename(defaultextension=".drawio", filetypes=[("Draw.io","*.drawio"), ("XML","*.xml")])
            if not path:
                return
            
            with open(path, "w", encoding="utf-8") as f:
                f.write(drawio_content)
            
            messagebox.showinfo("Export", f"Diagramme Draw.io enregistré: {path}")
        except Exception as exc:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du diagramme Draw.io: {exc}")

    def _create_drawio_diagram(self):
        """Crée un diagramme Draw.io au format XML"""
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        # Créer la racine du diagramme
        root = ET.Element("mxfile")
        root.set("host", "app.diagrams.net")
        root.set("modified", "2024-01-01T00:00:00.000Z")
        root.set("agent", "AWS SNS/SQS Browser")
        root.set("version", "22.1.16")
        root.set("etag", "abc123")
        
        diagram = ET.SubElement(root, "diagram")
        diagram.set("id", "aws-sns-sqs")
        diagram.set("name", "AWS SNS/SQS Architecture")
        
        mxGraphModel = ET.SubElement(diagram, "mxGraphModel")
        mxGraphModel.set("dx", "1422")
        mxGraphModel.set("dy", "754")
        mxGraphModel.set("grid", "1")
        mxGraphModel.set("gridSize", "10")
        mxGraphModel.set("guides", "1")
        mxGraphModel.set("tooltips", "1")
        mxGraphModel.set("connect", "1")
        mxGraphModel.set("arrows", "1")
        mxGraphModel.set("fold", "1")
        mxGraphModel.set("page", "1")
        mxGraphModel.set("pageScale", "1")
        mxGraphModel.set("pageWidth", "1169")
        mxGraphModel.set("pageHeight", "827")
        mxGraphModel.set("background", "#ffffff")
        mxGraphModel.set("math", "0")
        mxGraphModel.set("shadow", "0")
        
        root_elem = ET.SubElement(mxGraphModel, "root")
        
        # Cellules par défaut
        default_cell = ET.SubElement(root_elem, "mxCell")
        default_cell.set("id", "0")
        
        default_cell2 = ET.SubElement(root_elem, "mxCell")
        default_cell2.set("id", "1")
        default_cell2.set("parent", "0")
        
        # Position de départ
        y_pos = 50
        x_pos = 50
        cell_id = 2
        
        # Grouper par région
        regions_data = {}
        for topic in self.latest_inventory["topics"]:
            region = topic.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["topics"].append(topic)
        
        for queue in self.latest_inventory["queues"]:
            region = queue.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["queues"].append(queue)
        
        for link in self.latest_inventory["links"]:
            region = link.get("region", "unknown")
            if region not in regions_data:
                regions_data[region] = {"topics": [], "queues": [], "links": []}
            regions_data[region]["links"].append(link)
        
        # Créer les éléments du diagramme
        topic_cells = {}
        queue_cells = {}
        
        for region, data in regions_data.items():
            # Titre de région
            region_title = ET.SubElement(root_elem, "mxCell")
            region_title.set("id", str(cell_id))
            region_title.set("value", f"Région: {region}")
            region_title.set("style", "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=16;fontStyle=1")
            region_title.set("vertex", "1")
            region_title.set("parent", "1")
            region_geom = ET.SubElement(region_title, "mxGeometry")
            region_geom.set("x", str(x_pos))
            region_geom.set("y", str(y_pos))
            region_geom.set("width", "200")
            region_geom.set("height", "30")
            region_geom.set("as", "geometry")
            cell_id += 1
            y_pos += 50
            
            # Topics SNS
            for topic in data["topics"]:
                topic_name = topic.get("name", "Unknown")
                topic_cell = ET.SubElement(root_elem, "mxCell")
                topic_cell.set("id", str(cell_id))
                topic_cell.set("value", f"SNS Topic\n{topic_name}")
                topic_cell.set("style", "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12")
                topic_cell.set("vertex", "1")
                topic_cell.set("parent", "1")
                topic_geom = ET.SubElement(topic_cell, "mxGeometry")
                topic_geom.set("x", str(x_pos))
                topic_geom.set("y", str(y_pos))
                topic_geom.set("width", "120")
                topic_geom.set("height", "60")
                topic_geom.set("as", "geometry")
                topic_cells[topic.get("arn", "")] = cell_id
                cell_id += 1
                y_pos += 80
            
            # Queues SQS
            y_pos += 20
            for queue in data["queues"]:
                queue_name = queue.get("name", "Unknown")
                queue_cell = ET.SubElement(root_elem, "mxCell")
                queue_cell.set("id", str(cell_id))
                queue_cell.set("value", f"SQS Queue\n{queue_name}")
                queue_cell.set("style", "ellipse;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12")
                queue_cell.set("vertex", "1")
                queue_cell.set("parent", "1")
                queue_geom = ET.SubElement(queue_cell, "mxGeometry")
                queue_geom.set("x", str(x_pos + 200))
                queue_geom.set("y", str(y_pos))
                queue_geom.set("width", "120")
                queue_geom.set("height", "60")
                queue_geom.set("as", "geometry")
                queue_cells[queue.get("arn", "")] = cell_id
                cell_id += 1
                y_pos += 80
            
            y_pos += 50
            x_pos += 400
        
        # Créer les connexions
        for link in self.latest_inventory["links"]:
            topic_arn = link.get("topic_arn", "")
            queue_arn = link.get("queue_arn", "")
            
            if topic_arn in topic_cells and queue_arn in queue_cells:
                connection = ET.SubElement(root_elem, "mxCell")
                connection.set("id", str(cell_id))
                connection.set("style", "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#666666;strokeWidth=2")
                connection.set("edge", "1")
                connection.set("parent", "1")
                connection.set("source", str(topic_cells[topic_arn]))
                connection.set("target", str(queue_cells[queue_arn]))
                edge_geom = ET.SubElement(connection, "mxGeometry")
                edge_geom.set("relative", "1")
                edge_geom.set("as", "geometry")
                cell_id += 1
        
        # Convertir en XML formaté
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    def _list_links(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération des subscriptions..."))
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            regions = self.parse_regions()
            all_links = []
            for r in regions:
                self.root.after(0, lambda r=r: self.status_var.set(f"Récupération des subscriptions dans {r}..."))
                all_links.extend(list_links_for_region(session, r))

            self.latest_inventory["links"] = all_links
            self.root.after(0, lambda links=all_links: self._update_links_list(links))
            self.root.after(0, lambda: self.status_var.set(f"Récupéré {len(all_links)} subscriptions"))
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur lors de la récupération"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur", f"Erreur lors de la récupération des subscriptions:\n\n{err}"))

    def _update_links_list(self, links):
        self.links_list.delete(0, tk.END)
        for l in links:
            display = f"{l.get('region','?')} | Topic: {l.get('topic_name','?')} ({l.get('topic_arn','')}) -> Queue: {l.get('queue_name','?')} ({l.get('queue_arn','')})"
            self.links_list.insert(tk.END, display)


def main():
    try:
        print("[aws_sns_sqs_gui] starting GUI...")
        root = tk.Tk()
        app = App(root)
        print("[aws_sns_sqs_gui] entering mainloop")
        root.mainloop()
        print("[aws_sns_sqs_gui] mainloop exited")
    except Exception as exc:
        # Print to console so the user can see errors when launching from terminal
        print(f"[aws_sns_sqs_gui] error starting GUI: {exc}")
        raise


if __name__ == "__main__":
    main()
