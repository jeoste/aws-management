#!/usr/bin/env python3
"""
Simple tkinter GUI to enter AWS credentials/profile and list SNS topics and SQS queues.

This file intentionally imports boto3 only when needed so the GUI can start even if boto3
is not installed (it will show an error when you try to query AWS).
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
                self.regions.insert(0, "us-east-1,eu-west-1")
                self.regions.grid(row=2, column=0, sticky="w")

                # Buttons
                btns = ttk.Frame(frm)
                btns.grid(row=3, column=0, sticky="w", pady=(8, 0))
                ttk.Button(btns, text="Lister Topics", command=self.list_topics_action).grid(row=0, column=0, padx=(0, 6))
                ttk.Button(btns, text="Lister Queues", command=self.list_queues_action).grid(row=0, column=1, padx=(0, 6))
                ttk.Button(btns, text="Lister tout", command=self.list_both_action).grid(row=0, column=2, padx=(0, 6))
                ttk.Button(btns, text="Lister Subscriptions", command=self.list_links_action).grid(row=0, column=3, padx=(0, 6))
                ttk.Button(btns, text="Exporter JSON", command=self.export_json).grid(row=0, column=4, padx=(20, 6))

                # Results
                res_frame = ttk.Frame(frm)
                res_frame.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
                root.rowconfigure(4, weight=1)
                root.columnconfigure(0, weight=1)

                # Topics listbox
                topics_frame = ttk.LabelFrame(res_frame, text="Topics")
                topics_frame.grid(row=0, column=0, sticky="nsew")
                self.topics_list = tk.Listbox(topics_frame, width=60, height=15)
                self.topics_list.grid(row=0, column=0, sticky="nsew")

                # Queues listbox
                queues_frame = ttk.LabelFrame(res_frame, text="Queues")
                queues_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
                self.queues_list = tk.Listbox(queues_frame, width=60, height=15)
                self.queues_list.grid(row=0, column=0, sticky="nsew")

                # Links listbox (SNS -> SQS)
                links_frame = ttk.LabelFrame(res_frame, text="Subscriptions (SNS -> SQS)")
                links_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8,0))
                self.links_list = tk.Listbox(links_frame, width=125, height=8)
                self.links_list.grid(row=0, column=0, sticky="nsew")

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

            def _list_topics(self):
                try:
                    session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
                    regions = self.parse_regions()
                    all_topics = []
                    for r in regions:
                        all_topics.extend(list_topics(session, r))

                    self.latest_inventory["topics"] = all_topics
                    self.root.after(0, lambda topics=all_topics: self._update_topics_list(topics))
                except Exception as exc:
                    err = str(exc)
                    self.root.after(0, lambda err=err: messagebox.showerror("Erreur", err))

            def _list_queues(self):
                try:
                    session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
                    regions = self.parse_regions()
                    all_queues = []
                    for r in regions:
                        all_queues.extend(list_queues(session, r))

                    self.latest_inventory["queues"] = all_queues
                    self.root.after(0, lambda queues=all_queues: self._update_queues_list(queues))
                except Exception as exc:
                    err = str(exc)
                    self.root.after(0, lambda err=err: messagebox.showerror("Erreur", err))

            def _list_both(self):
                try:
                    session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
                    regions = self.parse_regions()
                    all_topics = []
                    all_queues = []
                    all_links = []
                    for r in regions:
                        all_topics.extend(list_topics(session, r))
                        all_queues.extend(list_queues(session, r))
                        all_links.extend(list_links_for_region(session, r))

                    self.latest_inventory["topics"] = all_topics
                    self.latest_inventory["queues"] = all_queues
                    self.latest_inventory["links"] = all_links
                    self.root.after(0, lambda topics=all_topics: self._update_topics_list(topics))
                    self.root.after(0, lambda queues=all_queues: self._update_queues_list(queues))
                    self.root.after(0, lambda links=all_links: self._update_links_list(links))
                except Exception as exc:
                    err = str(exc)
                    self.root.after(0, lambda err=err: messagebox.showerror("Erreur", err))

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

            def _list_links(self):
                try:
                    session = get_session(self.access_key.get().strip() or None, self.secret_key.get().strip() or None, self.session_token.get().strip() or None, self.profile.get().strip() or None)
                    regions = self.parse_regions()
                    all_links = []
                    for r in regions:
                        all_links.extend(list_links_for_region(session, r))

                    self.latest_inventory["links"] = all_links
                    self.root.after(0, lambda links=all_links: self._update_links_list(links))
                except Exception as exc:
                    err = str(exc)
                    self.root.after(0, lambda err=err: messagebox.showerror("Erreur", err))

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
                print(f"[aws_sns_sqs_gui] error starting GUI: {exc}")
                raise


        if __name__ == "__main__":
            main()
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
