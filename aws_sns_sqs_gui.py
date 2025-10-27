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

        # Mémoire des identifiants (Windows Credential Manager via keyring)
        remember_frame = ttk.Frame(creds)
        remember_frame.grid(row=4, column=0, columnspan=2, sticky="w")
        self.remember_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(remember_frame, text="Mémoriser (Windows Credential Manager)", variable=self.remember_var).grid(row=0, column=0, sticky="w")
        ttk.Button(remember_frame, text="Oublier identifiants", command=self.clear_saved_credentials_action).grid(row=0, column=1, padx=(8, 0))

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
        ttk.Button(btns, text="Exporter SQL", command=self.export_sql).grid(row=0, column=6, padx=(20, 6))
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

        # Charger d'éventuels identifiants sauvegardés
        self._load_saved_credentials()

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
            # Sauvegarder si demandé
            self._save_credentials_if_checked()
            session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
            
            # Tester avec STS pour obtenir les infos du compte
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            account_id = identity.get("Account", "Inconnu")
            user_arn = identity.get("Arn", "Inconnu")
            
            success_msg = f"Connexion réussie ! Compte: {account_id}\nUtilisateur: {user_arn}"
            self.root.after(0, lambda: self.status_var.set(f"Connecté - Compte: {account_id}"))
            self.root.after(0, lambda: messagebox.showinfo("Connexion réussie", success_msg))

            # Enregistrer après succès si la case est cochée
            self._save_credentials_if_checked()
            
        except Exception as exc:
            err = str(exc)
            self.root.after(0, lambda: self.status_var.set("Erreur de connexion"))
            self.root.after(0, lambda err=err: messagebox.showerror("Erreur de connexion", f"Impossible de se connecter à AWS:\n\n{err}"))

    def _list_topics(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération des topics SNS..."))
            self._save_credentials_if_checked()
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
            self._save_credentials_if_checked()
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
            self._save_credentials_if_checked()
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


    def export_sql(self):
        if not self.latest_inventory["topics"] and not self.latest_inventory["queues"] and not self.latest_inventory["links"]:
            messagebox.showinfo("Info", "Aucune donnée à exporter. Lancer une lecture d'abord.")
            return
        try:
            ddl_parts = []
            ddl_parts.append(
                """
CREATE TABLE sns_topic (
  arn VARCHAR(2048) PRIMARY KEY,
  name VARCHAR(255),
  region VARCHAR(64)
);
                """.strip()
            )
            ddl_parts.append(
                """
CREATE TABLE sqs_queue (
  arn VARCHAR(2048) PRIMARY KEY,
  name VARCHAR(255),
  url VARCHAR(2048),
  region VARCHAR(64)
);
                """.strip()
            )
            ddl_parts.append(
                """
CREATE TABLE subscription (
  topic_arn VARCHAR(2048) NOT NULL,
  queue_arn VARCHAR(2048) NOT NULL,
  region VARCHAR(64),
  PRIMARY KEY (topic_arn, queue_arn),
  CONSTRAINT fk_subscription_topic FOREIGN KEY (topic_arn) REFERENCES sns_topic(arn),
  CONSTRAINT fk_subscription_queue FOREIGN KEY (queue_arn) REFERENCES sqs_queue(arn)
);
                """.strip()
            )

            # Optionnel: ajouter des commentaires pour aider à l'interprétation
            # Les INSERT ne sont pas nécessaires pour l'import SQL de draw.io pour créer l'ERD.

            ddl = "\n\n".join(ddl_parts)

            path = filedialog.asksaveasfilename(defaultextension=".sql", filetypes=[("SQL","*.sql"), ("Text","*.txt")])
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(ddl)
            messagebox.showinfo("Export", f"DDL SQL exporté: {path}\n\nImportez-le dans draw.io via Arrange > Insert > Advanced > SQL.")
        except Exception as exc:
            messagebox.showerror("Erreur", f"Erreur lors de la génération du SQL: {exc}")

    def _list_links(self):
        try:
            self.root.after(0, lambda: self.status_var.set("Récupération des subscriptions..."))
            self._save_credentials_if_checked()
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

    # --- Gestion des identifiants mémorisés ---
    def _load_saved_credentials(self):
        try:
            import keyring  # type: ignore
        except Exception:
            return
        service = "aws-sns-sqs-gui"
        try:
            ak = keyring.get_password(service, "aws_access_key_id")
            sk = keyring.get_password(service, "aws_secret_access_key")
            st = keyring.get_password(service, "aws_session_token")
            pf = keyring.get_password(service, "profile")
            regs = keyring.get_password(service, "regions")
        except Exception:
            return

        any_loaded = False
        if ak:
            self.access_key.insert(0, ak)
            any_loaded = True
        if sk:
            self.secret_key.insert(0, sk)
            any_loaded = True
        if st:
            self.session_token.insert(0, st)
            any_loaded = True
        if pf:
            self.profile.insert(0, pf)
            any_loaded = True
        if regs:
            self.regions.delete(0, tk.END)
            self.regions.insert(0, regs)
            any_loaded = True
        if any_loaded:
            self.remember_var.set(True)
            self.status_var.set("Identifiants chargés depuis le gestionnaire d'identifiants")

    def _save_credentials_if_checked(self):
        if not getattr(self, "remember_var", None) or not self.remember_var.get():
            return
        try:
            import keyring  # type: ignore
        except Exception:
            return
        service = "aws-sns-sqs-gui"
        try:
            ak = (self.access_key.get() or "").strip()
            sk = (self.secret_key.get() or "").strip()
            st = (self.session_token.get() or "").strip()
            pf = (self.profile.get() or "").strip()
            regs = (self.regions.get() or "").strip()

            # Enregistrer si non vide, sinon supprimer l'entrée
            def set_or_delete(name, value):
                try:
                    if value:
                        keyring.set_password(service, name, value)
                    else:
                        try:
                            keyring.delete_password(service, name)
                        except Exception:
                            pass
                except Exception:
                    pass

            set_or_delete("aws_access_key_id", ak)
            set_or_delete("aws_secret_access_key", sk)
            set_or_delete("aws_session_token", st)
            set_or_delete("profile", pf)
            set_or_delete("regions", regs)
        except Exception:
            pass

    def _clear_saved_credentials(self):
        try:
            import keyring  # type: ignore
        except Exception as exc:
            self.root.after(0, lambda exc=str(exc): messagebox.showerror("Erreur", f"Impossible d'accéder au gestionnaire d'identifiants:\n\n{exc}"))
            return
        service = "aws-sns-sqs-gui"
        for name in [
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_session_token",
            "profile",
            "regions",
        ]:
            try:
                keyring.delete_password(service, name)
            except Exception:
                # Ignorer si l'entrée n'existe pas
                pass
        self.root.after(0, lambda: self.status_var.set("Identifiants supprimés du gestionnaire d'identifiants"))

    def clear_saved_credentials_action(self):
        self.run_in_thread(self._clear_saved_credentials)

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
