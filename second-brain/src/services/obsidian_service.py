import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from typing import Callable
import logging

class ObsidianHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str, str], None]):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self.callback("modified", event.src_path)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self.callback("created", event.src_path)

class ObsidianService:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.observer = Observer()

    def start_watching(self, callback: Callable[[str, str], None]):
        """开始监听 Obsidian 库目录"""
        if not os.path.exists(self.vault_path):
            logging.error(f"Obsidian vault path does not exist: {self.vault_path}")
            return

        handler = ObsidianHandler(callback)
        self.observer.schedule(handler, self.vault_path, recursive=True)
        self.observer.start()
        logging.info(f"Started watching Obsidian vault: {self.vault_path}")

    def stop_watching(self):
        """停止监听"""
        self.observer.stop()
        self.observer.join()

    def get_all_notes(self) -> list[str]:
        """获取库中所有的 Markdown 文件路径"""
        notes = []
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith(".md"):
                    notes.append(os.path.join(root, file))
        return notes
