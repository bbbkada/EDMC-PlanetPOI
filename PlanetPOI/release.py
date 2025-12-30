"""
Module for managing EDMC-PlanetPOI releases and auto-updates
"""

try:
    import tkinter as tk
    from tkinter import Frame
    from io import BytesIO
except:
    import Tkinter as tk
    from Tkinter import Frame

import json
import myNotebook as nb
import os
import plug
import requests
import shutil
import threading
import zipfile
import datetime
from config import config
from ttkHyperlinkLabel import HyperlinkLabel

import logging
from config import appname

plugin_name = os.path.basename(os.path.dirname(__file__))
logger = logging.getLogger(f"{appname}.{plugin_name}")


class ClientVersion:
    """Version information for the plugin"""
    ver = "1.7.2"  # Update this with each release
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
    """Hyperlink label for displaying release information"""
    
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
        """Handle resizing"""
        difference = datetime.datetime.now() - self.lasttime

        if difference.total_seconds() > 0.5:
            self.resized = False

        if not self.resized:
            logger.debug("Release widget resize")
            self.resized = True
            self.configure(wraplength=event.width - 2)


class ReleaseThread(threading.Thread):
    """Background thread for checking releases"""
    
    def __init__(self, release):
        threading.Thread.__init__(self, name="planetpoi-ReleaseThread")
        self.release = release

    def run(self):
        logger.debug("Release: UpdateThread")
        self.release.release_pull()


class Release(Frame):
    """Main release management class"""
    
    plugin_dir = None
    
    def __init__(self, parent, release, gridrow):
        """Initialize the Release frame"""
        padx, pady = 10, 5
        sticky = tk.EW + tk.N
        anchor = tk.NW

        Frame.__init__(self, parent)

        self.installed = False

        self.auto = tk.IntVar(value=config.get_int("PlanetPOI_AutoUpdate", default=1))
        self.rmbackup = tk.IntVar(value=config.get_int("PlanetPOI_RemoveBackup", default=0))

        self.columnconfigure(1, weight=1)
        self.grid(row=gridrow, column=0, sticky="NSEW", columnspan=2)

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

        # Remove backup directory if configured
        if (
            self.rmbackup.get() == 1
            and config.get_str("PlanetPOI_RemoveBackup")
            and config.get_str("PlanetPOI_RemoveBackup") != "None"
        ):
            delete_dir = config.get_str("PlanetPOI_RemoveBackup")
            logger.debug(f"PlanetPOI_RemoveBackup {delete_dir}")
            
            config.set("PlanetPOI_RemoveBackup", "None")
            
            if os.path.exists(delete_dir):
                try:
                    shutil.rmtree(delete_dir)
                    logger.debug(f"Successfully deleted {delete_dir}")
                except Exception as e:
                    logger.error(f"Failed to delete {delete_dir}: {str(e)}")
            else:
                logger.debug(f"Directory {delete_dir} does not exist, skipping deletion")

        # Trigger update after Tk main loop is running
        self.after_idle(self.update, None)

    def update(self, event):
        """Start update check"""
        self.release_thread()

    def version2number(self, version):
        """Convert version string to comparable number"""
        try:
            major, minor, patch = version.lstrip('v').split(".")
            return (int(major) * 1000000) + (int(minor) * 1000) + int(patch)
        except:
            logger.error(f"Failed to parse version: {version}")
            return 0

    def release_thread(self):
        """Start background thread for release check"""
        ReleaseThread(self).start()

    def release_pull(self):
        """Fetch latest release information from GitHub"""
        try:
            headers = {"X-GitHub-Api-Version": "2022-11-28"}
            self.latest = {}
            
            r = requests.get(
                "https://api.github.com/repos/bbbkada/EDMC-PlanetPOI/releases/latest",
                headers=headers,
                timeout=10
            )
            
            if not r.status_code == requests.codes.ok:
                logger.error("Error fetching release from GitHub")
                logger.error(f"Status code: {r.status_code}")
                logger.error(r.text)
            else:
                self.latest = r.json()
                logger.debug("Latest release downloaded")
                if not config.shutting_down:
                    self.after_idle(lambda: self.event_generate("<<ReleaseUpdate>>", when="tail"))
        except Exception as e:
            logger.error(f"Failed to check for updates: {str(e)}")

    def release_update(self, event):
        """Handle release update event"""
        if self.installed:
            return
            
        if not self.latest:
            logger.debug("Latest release is empty")
            return

        logger.debug("Processing latest release")

        current = self.version2number(self.release)
        release = self.version2number(self.latest.get("tag_name", "0.0.0"))

        self.hyperlink["url"] = self.latest.get("html_url", DEFAULT_URL)
        self.hyperlink["text"] = f"EDMC-PlanetPOI: {self.latest.get('tag_name')}"

        if current == release:
            # Current version, hide the release info
            self.grid_remove()
        elif current > release:
            # Experimental/dev version - hide the widget instead of showing experimental message
            self.grid_remove()
        else:
            # New version available
            if self.auto.get() == 1:
                # Auto-update enabled
                self.hyperlink["text"] = f"Updating to {self.latest.get('tag_name')}..."
                
                if self.installer():
                    self.hyperlink["text"] = f"Release {self.latest.get('tag_name')} Installed - Please Restart EDMC"
                else:
                    self.hyperlink["text"] = f"Release {self.latest.get('tag_name')} Upgrade Failed"
            else:
                # Manual update
                self.hyperlink["text"] = f"Please Upgrade to {self.latest.get('tag_name')}"
                self.button.grid()
            
            self.grid()

    def plugin_prefs(self, parent, cmdr, is_beta, gridrow):
        """Create preferences UI"""
        self.auto = tk.IntVar(value=config.get_int("PlanetPOI_AutoUpdate", default=1))
        self.rmbackup = tk.IntVar(value=config.get_int("PlanetPOI_RemoveBackup", default=0))

        frame = nb.Frame(parent)
        frame.columnconfigure(2, weight=1)
        frame.grid(row=gridrow, column=0, sticky="NSEW")
        
        nb.Checkbutton(
            frame, 
            text="Auto Update This Plugin", 
            variable=self.auto
        ).grid(row=0, column=0, sticky="NW")
        
        nb.Checkbutton(
            frame, 
            text="Remove backup after update", 
            variable=self.rmbackup
        ).grid(row=0, column=1, sticky="NW")

        return frame

    def prefs_changed(self, cmdr, is_beta):
        """Save preferences"""
        config.set("PlanetPOI_AutoUpdate", self.auto.get())
        config.set("PlanetPOI_RemoveBackup", self.rmbackup.get())

    def click_installer(self):
        """Handle manual install button click"""
        self.button.grid_remove()

        if self.installer():
            self.hyperlink["text"] = f"Release {self.latest.get('tag_name')} Installed - Please Restart EDMC"
        else:
            self.hyperlink["text"] = f"Release {self.latest.get('tag_name')} Upgrade Failed"

    def installer(self):
        """Download and install new version"""
        tag_name = self.latest.get("tag_name")
        
        if not tag_name:
            logger.error("No tag_name in latest release")
            return False

        logger.info(f"Installing {tag_name}")

        new_plugin_dir = os.path.join(
            os.path.dirname(Release.plugin_dir), 
            f"EDMC-PlanetPOI-{tag_name}"
        )

        # Check if already downloaded
        if os.path.isdir(new_plugin_dir):
            logger.error(f"Download already exists: {new_plugin_dir}")
            plug.show_error("PlanetPOI upgrade failed - directory exists")
            return False

        try:
            logger.debug("Downloading new version")
            download = requests.get(
                f"https://github.com/bbbkada/EDMC-PlanetPOI/archive/{tag_name}.zip",
                stream=True,
                timeout=30
            )
            
            if not download.status_code == requests.codes.ok:
                logger.error(f"Download failed with status {download.status_code}")
                plug.show_error("PlanetPOI upgrade failed - download error")
                return False

            # Extract zip file
            z = zipfile.ZipFile(BytesIO(download.content))
            z.extractall(os.path.dirname(Release.plugin_dir))
            
        except Exception as e:
            logger.error(f"Download/extract failed: {str(e)}")
            plug.show_error("PlanetPOI upgrade failed")
            return False

        # Disable current plugin
        try:
            disabled_dir = f"{Release.plugin_dir}.disabled"
            os.rename(Release.plugin_dir, disabled_dir)
            logger.debug(f"Renamed {Release.plugin_dir} to {disabled_dir}")
        except Exception as e:
            logger.error(f"Failed to disable current plugin: {str(e)}")
            plug.show_error("PlanetPOI upgrade failed")
            try:
                shutil.rmtree(new_plugin_dir)
            except:
                pass
            return False

        # Mark backup for removal if configured
        if self.rmbackup.get() == 1:
            config.set("PlanetPOI_RemoveBackup", disabled_dir)

        logger.info("Upgrade complete")
        Release.plugin_dir = new_plugin_dir
        self.installed = True

        return True

    @classmethod
    def get_auto(cls):
        """Get auto-update setting"""
        return config.get_int("PlanetPOI_AutoUpdate", default=1)

    @classmethod
    def plugin_start(cls, plugin_dir):
        """Initialize plugin directory"""
        cls.plugin_dir = plugin_dir
