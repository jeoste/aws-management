"""Simple Tkinter GUI for listing SNS topics, SQS queues and realtime SQS polling.

Features:
- Enter AWS credentials or profile and regions
- List Topics, Queues and SNS->SQS subscriptions
- Export inventory to JSON
- Real-time tab: select queues and start background polling to display messages

This file keeps boto3 imports lazy so the UI can show a helpful error if boto3
is not installed instead of failing at import time.
"""
from __future__ import annotations

import threading
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List, Optional


def get_session(profile: Optional[str], access_key: Optional[str], secret_key: Optional[str], session_token: Optional[str]):
    """Return a boto3.Session created from provided credentials or profile.

    Raises RuntimeError if boto3 is not available.
    """
    try:
        import boto3
    except Exception as exc:
        raise RuntimeError("boto3 is required for AWS operations: " + str(exc))

    if access_key and secret_key:
        return boto3.Session(aws_access_key_id=access_key,
                             aws_secret_access_key=secret_key,
                             aws_session_token=session_token)
    if profile:
        return boto3.Session(profile_name=profile)
    return boto3.Session()


def list_topics(session, region: Optional[str]) -> List[str]:
    import botocore
    sns = session.client('sns', region_name=region)
    out = []
    paginator = sns.get_paginator('list_topics')
    for page in paginator.paginate():
        for t in page.get('Topics', []):
            out.append(t.get('TopicArn'))
    return out


def list_queues(session, region: Optional[str]) -> List[str]:
    sqs = session.client('sqs', region_name=region)
    out = []
    paginator = sqs.get_paginator('list_queues')
    try:
        for page in paginator.paginate():
            urls = page.get('QueueUrls') or []
            out.extend(urls)
    except Exception:
        # Some accounts/regions return no queues and boto3 may raise
        pass
    return out


def list_links_for_region(session, region: Optional[str]) -> List[Dict[str, str]]:
    """Return list of subscriptions where protocol is 'sqs'.

    Each item is a dict with keys: TopicArn, Protocol, Endpoint
    """
    sns = session.client('sns', region_name=region)
    out = []
    paginator = sns.get_paginator('list_subscriptions')
    for page in paginator.paginate():
        for s in page.get('Subscriptions', []):
            if s.get('Protocol') == 'sqs':
                out.append({
                    'TopicArn': s.get('TopicArn'),
                    'Protocol': s.get('Protocol'),
                    'Endpoint': s.get('Endpoint')
                })
    return out


def _region_from_queue_url(url: str) -> Optional[str]:
    try:
        host = url.split('//', 1)[1].split('/', 1)[0]
        parts = host.split('.')
        # host like: sqs.us-east-1.amazonaws.com
        if len(parts) >= 2 and parts[0].startswith('sqs'):
            return parts[1]
    except Exception:
        return None
    return None


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title('AWS SNS / SQS Viewer')

        frm = ttk.Frame(root, padding=8)
        frm.grid(row=0, column=0, sticky='nsew')

        # Credential fields
        ttk.Label(frm, text='AWS Profile:').grid(row=0, column=0, sticky='w')
        self.profile = tk.StringVar()
        ttk.Entry(frm, textvariable=self.profile, width=30).grid(row=0, column=1, sticky='w')

        ttk.Label(frm, text='Access Key ID:').grid(row=1, column=0, sticky='w')
        self.access_key = tk.StringVar()
        ttk.Entry(frm, textvariable=self.access_key, width=60).grid(row=1, column=1, sticky='w')

        ttk.Label(frm, text='Secret Access Key:').grid(row=2, column=0, sticky='w')
        self.secret_key = tk.StringVar()
        ttk.Entry(frm, textvariable=self.secret_key, show='*', width=60).grid(row=2, column=1, sticky='w')

        ttk.Label(frm, text='Session Token:').grid(row=3, column=0, sticky='w')
        self.session_token = tk.StringVar()
        ttk.Entry(frm, textvariable=self.session_token, width=60).grid(row=3, column=1, sticky='w')

        ttk.Label(frm, text='Region (optional):').grid(row=4, column=0, sticky='w')
        self.regions = tk.StringVar()
        ttk.Entry(frm, textvariable=self.regions, width=60).grid(row=4, column=1, sticky='w')

        # Action buttons
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, sticky='w', pady=(8,0))
        ttk.Button(btn_frame, text='List Topics', command=self.list_topics_action).grid(row=0, column=0, padx=(0,6))
        ttk.Button(btn_frame, text='List Queues', command=self.list_queues_action).grid(row=0, column=1, padx=(0,6))
        ttk.Button(btn_frame, text='List Links', command=self.list_links_action).grid(row=0, column=2, padx=(0,6))
        ttk.Button(btn_frame, text='Export JSON', command=self.export_json).grid(row=0, column=3, padx=(0,6))

        # Notebook with Results and Real-time
        self.notebook = ttk.Notebook(frm)
        self.notebook.grid(row=6, column=0, columnspan=2, sticky='nsew', pady=(12,0))
        root.rowconfigure(6, weight=1)
        root.columnconfigure(0, weight=1)

        # Results tab
        results_tab = ttk.Frame(self.notebook)
        self.notebook.add(results_tab, text='Results')

        topics_frame = ttk.LabelFrame(results_tab, text='Topics')
        topics_frame.grid(row=0, column=0, sticky='nsew')
        self.topics_list = tk.Listbox(topics_frame, width=60, height=15)
        self.topics_list.grid(row=0, column=0, sticky='nsew')

        queues_frame = ttk.LabelFrame(results_tab, text='Queues')
        queues_frame.grid(row=0, column=1, sticky='nsew', padx=(8,0))
        self.queues_list = tk.Listbox(queues_frame, width=60, height=15)
        self.queues_list.grid(row=0, column=0, sticky='nsew')

        links_frame = ttk.LabelFrame(results_tab, text='Subscriptions (SNS -> SQS)')
        links_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(8,0))
        self.links_list = tk.Listbox(links_frame, width=125, height=8)
        self.links_list.grid(row=0, column=0, sticky='nsew')

        for child in results_tab.winfo_children():
            child.grid_configure(padx=4, pady=2)

        # Real-time tab
        realtime_tab = ttk.Frame(self.notebook)
        self.notebook.add(realtime_tab, text='Real-time')

        selector_frame = ttk.LabelFrame(realtime_tab, text='Select queues to monitor')
        selector_frame.grid(row=0, column=0, sticky='nsw', padx=(0,8), pady=(0,8))
        self.rt_queues_listbox = tk.Listbox(selector_frame, selectmode=tk.MULTIPLE, width=60, height=15)
        self.rt_queues_listbox.grid(row=0, column=0, sticky='nsew')

        ctrl_frame = ttk.Frame(realtime_tab)
        ctrl_frame.grid(row=1, column=0, sticky='w', pady=(4,0))
        self.rt_start_btn = ttk.Button(ctrl_frame, text='Start Monitoring', command=self.start_realtime)
        self.rt_start_btn.grid(row=0, column=0, padx=(0,6))
        self.rt_stop_btn = ttk.Button(ctrl_frame, text='Stop Monitoring', command=self.stop_realtime, state='disabled')
        self.rt_stop_btn.grid(row=0, column=1, padx=(0,6))
        self.rt_auto_delete = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl_frame, text='Auto-delete messages', variable=self.rt_auto_delete).grid(row=0, column=2, padx=(6,0))

        messages_frame = ttk.LabelFrame(realtime_tab, text='Messages (live)')
        messages_frame.grid(row=0, column=1, rowspan=2, sticky='nsew')
        realtime_tab.columnconfigure(1, weight=1)
        realtime_tab.rowconfigure(0, weight=1)
        self.rt_messages = ScrolledText(messages_frame, width=100, height=25)
        self.rt_messages.grid(row=0, column=0, sticky='nsew')

        # Storage
        self.latest_inventory = {'topics': [], 'queues': [], 'links': []}
        self.rt_threads: Dict[str, tuple[threading.Thread, threading.Event]] = {}

    def _make_session(self):
        try:
            return get_session(self.profile.get() or None,
                               self.access_key.get() or None,
                               self.secret_key.get() or None,
                               self.session_token.get() or None)
        except RuntimeError as exc:
            messagebox.showerror('Missing dependency', str(exc))
            return None

    def list_topics_action(self):
        session = self._make_session()
        if not session:
            return
        region = (self.regions.get() or None)

        def worker():
            try:
                topics = list_topics(session, region)
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda err=err: messagebox.showerror('Error listing topics', err))
                return
            self.latest_inventory['topics'] = topics
            self.root.after(0, lambda: self._update_topics(topics))

        threading.Thread(target=worker, daemon=True).start()

    def _update_topics(self, topics: List[str]):
        self.topics_list.delete(0, tk.END)
        for t in topics:
            self.topics_list.insert(tk.END, t)

    def list_queues_action(self):
        session = self._make_session()
        if not session:
            return
        region = (self.regions.get() or None)

        def worker():
            try:
                queues = list_queues(session, region)
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda err=err: messagebox.showerror('Error listing queues', err))
                return
            self.latest_inventory['queues'] = queues
            self.root.after(0, lambda: self._update_queues(queues))

        threading.Thread(target=worker, daemon=True).start()

    def _update_queues(self, queues: List[str]):
        self.queues_list.delete(0, tk.END)
        self.rt_queues_listbox.delete(0, tk.END)
        for q in queues:
            self.queues_list.insert(tk.END, q)
            self.rt_queues_listbox.insert(tk.END, q)

    def list_links_action(self):
        session = self._make_session()
        if not session:
            return
        region = (self.regions.get() or None)

        def worker():
            try:
                links = list_links_for_region(session, region)
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda err=err: messagebox.showerror('Error listing links', err))
                return
            self.latest_inventory['links'] = links
            self.root.after(0, lambda: self._update_links(links))

        threading.Thread(target=worker, daemon=True).start()

    def _update_links(self, links: List[Dict[str, str]]):
        self.links_list.delete(0, tk.END)
        for l in links:
            self.links_list.insert(tk.END, f"{l.get('TopicArn')} -> {l.get('Endpoint')}")

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.latest_inventory, f, indent=2)
        messagebox.showinfo('Exported', f'Inventory exported to {path}')

    def start_realtime(self):
        # start threads for selected queues
        selected = self.rt_queues_listbox.curselection()
        if not selected:
            messagebox.showinfo('No queues selected', 'Please select one or more queues to monitor')
            return
        session = self._make_session()
        if not session:
            return

        to_start = []
        for i in selected:
            q = self.rt_queues_listbox.get(i)
            if q in self.rt_threads:
                continue
            to_start.append(q)

        if not to_start:
            messagebox.showinfo('Already monitoring', 'Selected queues are already being monitored')
            return

        for q in to_start:
            stop_event = threading.Event()
            thr = threading.Thread(target=self._poll_queue, args=(session, q, stop_event), daemon=True)
            self.rt_threads[q] = (thr, stop_event)
            thr.start()

        self.rt_start_btn.config(state='disabled')
        self.rt_stop_btn.config(state='normal')

    def stop_realtime(self):
        for q, (thr, stop_event) in list(self.rt_threads.items()):
            stop_event.set()
            thr.join(timeout=1.0)
            self.rt_threads.pop(q, None)
        self.rt_start_btn.config(state='normal')
        self.rt_stop_btn.config(state='disabled')

    def _poll_queue(self, session, queue_url: str, stop_event: threading.Event):
        try:
            import boto3
        except Exception:
            self.root.after(0, lambda: messagebox.showerror('Missing dependency', 'boto3 is required for realtime monitoring'))
            return

        region = _region_from_queue_url(queue_url)
        sqs = session.client('sqs', region_name=region)
        while not stop_event.is_set():
            try:
                resp = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=10)
                messages = resp.get('Messages') or []
                for m in messages:
                    body = m.get('Body')
                    ts = time.strftime('%Y-%m-%d %H:%M:%S')
                    display = f'[{ts}] Queue={queue_url} MessageId={m.get("MessageId")} Body={body}\n'
                    self.root.after(0, lambda display=display: self.rt_messages.insert(tk.END, display))
                    self.root.after(0, lambda: self.rt_messages.yview_moveto(1.0))
                    if self.rt_auto_delete.get():
                        try:
                            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=m.get('ReceiptHandle'))
                        except Exception:
                            pass
            except Exception as exc:
                err = str(exc)
                self.root.after(0, lambda err=err: self.rt_messages.insert(tk.END, f'Error polling {queue_url}: {err}\n'))
                time.sleep(2)


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
