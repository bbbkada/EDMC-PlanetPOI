"""
Module for managing EDMC-PlanetPOI releases and auto-updates

Key change vs previous version:
- NEVER extract the GitHub ZIP into the EDMC plugins directory.
- Instead extract to a temporary staging directory (OS temp),
  then copy/overwrite files into the *current* plugin directory (Release.plugin_dir),
  skipping poi.json to preserve user data.

This prevents the updater from creating an extra plugin folder (duplicates).
Python: 3.7+
"""

try:
    import tkinter as tk
    from tkinter import Frame, messagebox
    from io import BytesIO
except Exception:
    import Tkinter as tk
    from Tkinter import Frame
    import tkMessageBox as messagebox
    from io import BytesIO

import datetime
import json
import os
import shutil
import tempfile
import threading
import time
import zipfile

import myNotebook as nb
import plug
import requests
from config import config
from ttkHyperlinkLabel import HyperlinkLabel

# Name based on current folder
plugin_name = os.path.basename(os.path.dirname(__file__))


# Use print-based logging to avoid EDMC logger format incompatibilities
def safe_log(level, message):
    """Safe logging wrapper that avoids EDMC format incompatibilities."""
    import sys
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] PlanetPOI {level.upper()}: {message}", file=sys.stderr)


class ClientVersion:
    """Version information for the plugin."""
    ver = "1.8.1"  # Update this with each release
    client_version = f"EDMC-PlanetPOI.{ver}"

    @classmethod
    def version(cls):
        return cls.ver

    @classmethod
    def client(cls):
        return cls.client_version


RELEASE_CYCLE = 60 * 1000 * 60  # 1 Hour
DEFAULT_URL = "https://github.com/bbbkada/EDMC-PlanetPOI/releases"
WRAP_LENGTH = 200


class ReleaseLink(HyperlinkLabel):
    """Hyperlink label for displaying release information."""

    def __init__(self, parent):
        HyperlinkLabel.__init__(
            self,
            parent,
            text="Checking for updates...",
            url=DEFAULT_URL,
            wraplength=50,
            anchor=tk.NW,
        )
        self.resized = False
        self.lasttime = datetime.datetime.now()
        self.bind("<Configure>", self.__configure_event)

    def __configure_event(self, event):
        """Handle resizing."""
        difference = datetime.datetime.now() - self.lasttime

        if difference.total_seconds() > 0.5:
            self.resized = False

        if not self.resized:
            safe_log("debug", "Release widget resize")
            self.resized = True
            self.configure(wraplength=max(10, event.width - 2))


class ReleaseThread(threading.Thread):
    """Background thread for checking releases."""

    def __init__(self, release):
        threading.Thread.__init__(self, name="planetpoi-ReleaseThread")
        self.release = release

    def run(self):
        safe_log("debug", "Release: UpdateThread")
        self.release.release_pull()


def _acquire_update_lock(plugins_parent_dir, stale_seconds=600):
    """
    Prevent multiple plugin instances from running installer simultaneously.
    Uses an atomic lockfile in the plugins parent directory.
    """
    lock_path = os.path.join(plugins_parent_dir, ".planetpoi_update.lock")

    try:
        if os.path.exists(lock_path):
            try:
                age = time.time() - os.path.getmtime(lock_path)
                if age > stale_seconds:
                    os.remove(lock_path)
            except Exception:
                pass

        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode("ascii", "ignore"))
        finally:
            os.close(fd)
        return lock_path
    except FileExistsError:
        return None
    except Exception as e:
        safe_log("warning", f"Could not create update lock: {e}")
        return None


def _release_update_lock(lock_path):
    if not lock_path:
        return
    try:
        os.remove(lock_path)
    except Exception:
        pass


def _copy_merge_tree(src_dir, dst_dir, skip_files=None, skip_dirs=None):
    """
    Copy/overwrite files from src_dir into dst_dir (recursive).
    Python 3.7 compatible. Overwrites existing files.
    """
    if skip_files is None:
        skip_files = set()
    else:
        skip_files = set(skip_files)

    if skip_dirs is None:
        skip_dirs = {"__pycache__", ".git"}
    else:
        skip_dirs = set(skip_dirs)

    for root, dirs, files in os.walk(src_dir):
        # prune directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        rel = os.path.relpath(root, src_dir)
        dst_root = dst_dir if rel == "." else os.path.join(dst_dir, rel)

        if not os.path.isdir(dst_root):
            os.makedirs(dst_root)

        for fn in files:
            if fn in skip_files:
                continue
            src_path = os.path.join(root, fn)
            dst_path = os.path.join(dst_root, fn)

            # Ensure parent exists
            dst_parent = os.path.dirname(dst_path)
            if not os.path.isdir(dst_parent):
                os.makedirs(dst_parent)

            # copy2 preserves mtime which can be useful for debugging
            shutil.copy2(src_path, dst_path)


class Release(Frame):
    """Main release management class."""

    plugin_dir = None
    installed = False  # Class variable to prevent duplicate installs
    latest_release = {}  # Store latest release data across instances

    def __init__(self, parent, release, gridrow):
        padx, pady = 10, 5
        sticky = tk.EW + tk.N
        anchor = tk.NW

        Frame.__init__(self, parent)

        self.columnconfigure(1, weight=1)
        self.grid(row=gridrow, column=0, sticky="NSEW", columnspan=2)
        self.grid_remove()  # Hide by default

        self.label = tk.Label(self, text="Release:")
        self.label.grid(row=0, column=0, sticky=sticky)

        self.hyperlink = ReleaseLink(self)
        self.hyperlink.grid(row=0, column=1, sticky="NSEW")

        self.button = tk.Button(
            self, text="Click here to upgrade", command=self.click_installer
        )
        self.button.grid(row=1, column=0, columnspan=2, sticky="NSEW")
        self.button.grid_remove()

        self.release = release
        self.latest = {}

        self.bind("<<ReleaseUpdate>>", self.release_update)

        # Delay version check by 2 seconds to avoid blocking EDMC startup
        self.after(2000, lambda: self.update(None))

    def update(self, event):
        self.release_thread()

    def start_update_check(self):
        self.after(2000, lambda: self.update(None))

    def version2number(self, version):
        try:
            major, minor, patch = version.lstrip("v").split(".")
            return (int(major) * 1000000) + (int(minor) * 1000) + int(patch)
        except Exception:
            safe_log("error", f"Failed to parse version: {version}")
            return 0

    def release_thread(self):
        ReleaseThread(self).start()

    def release_pull(self):
        try:
            headers = {"X-GitHub-Api-Version": "2022-11-28"}
            self.latest = {}
            Release.latest_release = {}

            r = requests.get(
                "https://api.github.com/repos/bbbkada/EDMC-PlanetPOI/releases/latest",
                headers=headers,
                timeout=10,
            )

            if r.status_code != requests.codes.ok:
                safe_log("error", "Error fetching release from GitHub")
                safe_log("error", f"Status code: {r.status_code}")
                safe_log("error", r.text)
                return

            self.latest = r.json()
            Release.latest_release = self.latest
            safe_log("debug", "Latest release downloaded")

            if not config.shutting_down:
                def safe_event_generate():
                    try:
                        self.event_generate("<<ReleaseUpdate>>", when="tail")
                    except tk.TclError:
                        safe_log("debug", "Widget destroyed, skipping event generation")

                self.after_idle(safe_event_generate)

        except Exception as e:
            safe_log("error", f"Failed to check for updates: {str(e)}")

    def release_update(self, event):
        if Release.installed:
            safe_log("debug", "Already installed, skipping")
            return

        if not self.latest:
            safe_log("debug", "Latest release is empty")
            return

        safe_log("debug", "Processing latest release")
        safe_log("debug", f"Current version string: {self.release}")
        safe_log("debug", f"Latest tag_name: {self.latest.get('tag_name')}")

        current = self.version2number(self.release)
        release = self.version2number(self.latest.get("tag_name", "0.0.0"))

        safe_log("debug", f"Current version number: {current}")
        safe_log("debug", f"Latest version number: {release}")

        self.hyperlink["url"] = self.latest.get("html_url", DEFAULT_URL)
        self.hyperlink["text"] = f"EDMC-PlanetPOI: {self.latest.get('tag_name')}"

        if current >= release:
            safe_log("debug", "No update needed, hiding widget")
            self.grid_remove()
            return

        safe_log("info", f"New version available: {self.latest.get('tag_name')}")
        auto_update_str = config.get_str("planetpoi_auto_update")
        if auto_update_str == "1":
            safe_log("info", "Auto-update enabled, starting installation")
            self.installer()

        self.grid_remove()

    def plugin_prefs(
        self, parent, cmdr, is_beta, gridrow, auto_update_var, auto_remove_backups_var
    ):
        parent.columnconfigure(0, weight=1)

        frame = nb.Frame(parent)
        frame.columnconfigure(2, weight=1)
        frame.grid(row=gridrow, column=0, sticky="NSEW")

        nb.Checkbutton(
            frame, text="Auto Update This Plugin", variable=auto_update_var
        ).grid(row=0, column=0, sticky="NW")

        nb.Checkbutton(
            frame, text="Auto Remove Old Backups", variable=auto_remove_backups_var
        ).grid(row=0, column=1, sticky="NW", padx=(10, 0))

        version_link = HyperlinkLabel(
            frame,
            text=f"v{ClientVersion.version()}",
            url="https://github.com/bbbkada/EDMC-PlanetPOI",
            anchor=tk.E,
        )
        version_link.grid(row=0, column=2, sticky="NE", padx=(10, 5))

        latest_data = self.latest if self.latest else Release.latest_release
        auto_update_enabled = auto_update_var.get() == 1

        if latest_data and not auto_update_enabled:
            current = self.version2number(self.release)
            release = self.version2number(latest_data.get("tag_name", "0.0.0"))

            if current < release:
                update_btn = nb.Button(
                    frame,
                    text=f"Update to {latest_data.get('tag_name')}",
                    command=self.click_installer,
                    width=18,
                )
                update_btn.grid(row=0, column=3, sticky="NE", padx=(0, 5))

        return frame

    def click_installer(self):
        success = self.installer(manual_update=True)
        if success:
            messagebox.showinfo(
                "Update Complete",
                "The plugin has been updated successfully.\n\n"
                "Please restart EDMC for the changes to take effect.",
            )
        else:
            messagebox.showerror(
                "Update Failed",
                "Failed to install the update.\n\n"
                "This may be caused by:\n"
                "- EDMC is running with insufficient permissions\n"
                "- Antivirus software blocking the update\n"
                "- Files are locked by another process\n\n"
                "Try running EDMC as administrator or check the EDMC log for details.",
            )

    def installer(self, manual_update=False):
        """
        Download and install new version.

        New behavior:
        - Extract ZIP to OS temp (staging)
        - Copy/overwrite files into current plugin directory (Release.plugin_dir)
        - Never create extra plugin folders in the plugins directory
        - Preserve poi.json
        """
        tag_name = self.latest.get("tag_name")
        if not tag_name:
            safe_log("error", "No tag_name in latest release")
            return False

        if not Release.plugin_dir or not os.path.isdir(Release.plugin_dir):
            safe_log("error", f"Invalid plugin_dir: {Release.plugin_dir}")
            return False

        plugins_parent_dir = os.path.dirname(os.path.normpath(Release.plugin_dir))

        # Avoid concurrent install attempts from duplicate plugin instances
        lock_path = _acquire_update_lock(plugins_parent_dir)
        if lock_path is None:
            safe_log("info", "Another PlanetPOI instance is updating; skipping.")
            return False

        staging_root = None
        try:
            safe_log("info", f"Installing {tag_name}")
            safe_log("debug", f"Current plugin_dir: {Release.plugin_dir}")

            # 1) Download ZIP
            download_url = (
                f"https://github.com/bbbkada/EDMC-PlanetPOI/archive/refs/tags/{tag_name}.zip"
            )
            safe_log("debug", f"Download URL: {download_url}")

            download = requests.get(download_url, stream=True, timeout=30)
            if download.status_code != requests.codes.ok:
                safe_log("error", f"Download failed with status {download.status_code}")
                safe_log("error", f"Response: {download.text[:500]}")
                return False

            safe_log("debug", f"Downloaded {len(download.content)} bytes")

            # 2) Extract to staging dir (TEMP), not plugins folder
            staging_root = tempfile.mkdtemp(prefix="planetpoi-update-")
            safe_log("debug", f"Staging dir: {staging_root}")

            z = zipfile.ZipFile(BytesIO(download.content))

            # Determine top-level folder inside zip (GitHub zips always have one)
            namelist = z.namelist()
            if not namelist:
                safe_log("error", "ZIP is empty")
                return False
            top_level = namelist[0].split("/")[0]
            safe_log("debug", f"ZIP top-level folder: {top_level}")

            # Extract everything to staging (we'll skip poi.json at copy stage, not here)
            z.extractall(staging_root)

            extracted_dir = os.path.join(staging_root, top_level)
            if not os.path.isdir(extracted_dir):
                safe_log("error", f"Extracted directory not found: {extracted_dir}")
                return False

            # 3) Backup current plugin folder (optional but useful for rollback)
            old_version = ClientVersion.version()
            backup_dir = os.path.join(
                plugins_parent_dir, f"EDMC-PlanetPOI.{old_version}.{datetime.datetime.now():%Y%m%d-%H%M%S}.disabled"
            )
            safe_log("debug", f"Creating backup: {backup_dir}")
            try:
                shutil.copytree(Release.plugin_dir, backup_dir)
                safe_log("debug", "Backup created successfully")
            except Exception as e:
                safe_log("warning", f"Backup failed (continuing anyway): {e}")
                backup_dir = None

            # 4) Copy/overwrite files into *current* plugin dir, preserving poi.json
            safe_log("debug", "Copying new files into current plugin directory (poi.json preserved)")
            _copy_merge_tree(
                extracted_dir,
                Release.plugin_dir,
                skip_files={"poi.json"},
                skip_dirs={"__pycache__", ".git"},
            )

            safe_log("info", f"Upgrade to {tag_name} complete - please restart EDMC")
            Release.installed = True

            # 5) Auto-remove old backups if enabled
            auto_remove_str = config.get_str("planetpoi_auto_remove_backups")
            if auto_remove_str == "1":
                self.remove_old_backups()

            return True

        except Exception as e:
            safe_log("error", f"Failed to install update: {e}")
            return False

        finally:
            # Cleanup staging
            if staging_root and os.path.isdir(staging_root):
                try:
                    shutil.rmtree(staging_root)
                except Exception:
                    pass
            _release_update_lock(lock_path)

    def remove_old_backups(self):
        """Remove old .disabled backup directories created by this updater."""
        try:
            plugins_dir = os.path.dirname(Release.plugin_dir)
            safe_log("debug", f"Looking for old backups in {plugins_dir}")

            for item in os.listdir(plugins_dir):
                # Match: EDMC-PlanetPOI.X.Y.Z.YYYYMMDD-HHMMSS.disabled (or older format)
                if item.startswith("EDMC-PlanetPOI.") and item.endswith(".disabled"):
                    backup_path = os.path.join(plugins_dir, item)
                    safe_log("info", f"Removing old backup: {backup_path}")
                    try:
                        shutil.rmtree(backup_path)
                        safe_log("info", f"Successfully removed {item}")
                    except Exception as e:
                        safe_log("error", f"Failed to remove backup {item}: {e}")
        except Exception as e:
            safe_log("error", f"Failed to scan for old backups: {e}")

    @classmethod
    def get_auto(cls):
        auto_update_str = config.get_str("planetpoi_auto_update")
        return 1 if auto_update_str == "1" else 0

    @classmethod
    def plugin_start(cls, plugin_dir):
        """Initialize plugin directory."""
        cls.plugin_dir = plugin_dir