"""
Module for managing EDMC-PlanetPOI releases and auto-updates
"""

try:
    import tkinter as tk
    from tkinter import Frame, messagebox
    from io import BytesIO
except:
    import Tkinter as tk
    from Tkinter import Frame
    import tkMessageBox as messagebox

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

# Use print-based logging to avoid EDMC logger format incompatibilities
def safe_log(level, message):
    """Safe logging wrapper that avoids EDMC format incompatibilities"""
    # Use print to stderr instead of logger to avoid osthreadid formatting issues
    import sys
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] PlanetPOI {level.upper()}: {message}", file=sys.stderr)


class ClientVersion:
    """Version information for the plugin"""
    ver = "1.7.4"  # Update this with each release
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
            safe_log('debug', "Release widget resize")
            self.resized = True
            self.configure(wraplength=event.width - 2)


class ReleaseThread(threading.Thread):
    """Background thread for checking releases"""
    
    def __init__(self, release):
        threading.Thread.__init__(self, name="planetpoi-ReleaseThread")
        self.release = release

    def run(self):
        safe_log('debug', "Release: UpdateThread")
        self.release.release_pull()


class Release(Frame):
    """Main release management class"""
    
    plugin_dir = None
    installed = False  # Class variable to prevent duplicate installs
    latest_release = {}  # Class variable to store latest release data across instances
    
    def __init__(self, parent, release, gridrow):
        """Initialize the Release frame"""
        padx, pady = 10, 5
        sticky = tk.EW + tk.N
        anchor = tk.NW

        Frame.__init__(self, parent)

        self.columnconfigure(1, weight=1)
        # Start hidden - only show if update is needed
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
        # Use lambda to properly call update method
        self.after(2000, lambda: self.update(None))

    def update(self, event):
        """Start update check"""
        self.release_thread()
    
    def start_update_check(self):
        """Public method to start update check - can be called from load.py"""
        # Delay by 2 seconds to avoid blocking startup
        self.after(2000, lambda: self.update(None))

    def version2number(self, version):
        """Convert version string to comparable number"""
        try:
            major, minor, patch = version.lstrip('v').split(".")
            return (int(major) * 1000000) + (int(minor) * 1000) + int(patch)
        except:
            safe_log('error', f"Failed to parse version: {version}")
            return 0

    def release_thread(self):
        """Start background thread for release check"""
        ReleaseThread(self).start()

    def release_pull(self):
        """Fetch latest release information from GitHub"""
        try:
            headers = {"X-GitHub-Api-Version": "2022-11-28"}
            self.latest = {}
            Release.latest_release = {}  # Reset class variable
            
            r = requests.get(
                "https://api.github.com/repos/bbbkada/EDMC-PlanetPOI/releases/latest",
                headers=headers,
                timeout=10
            )
            
            if not r.status_code == requests.codes.ok:
                safe_log('error', "Error fetching release from GitHub")
                safe_log('error', f"Status code: {r.status_code}")
                safe_log('error', r.text)
            else:
                self.latest = r.json()
                Release.latest_release = self.latest  # Store in class variable
                safe_log('debug', "Latest release downloaded")
                if not config.shutting_down:
                    # Schedule event generation, but wrap in try/except to handle widget destruction
                    def safe_event_generate():
                        try:
                            self.event_generate("<<ReleaseUpdate>>", when="tail")
                        except tk.TclError:
                            # Widget was destroyed - this is normal if settings dialog was closed
                            safe_log('debug', "Widget destroyed, skipping event generation")
                    self.after_idle(safe_event_generate)
        except Exception as e:
            safe_log('error', f"Failed to check for updates: {str(e)}")

    def release_update(self, event):
        """Handle release update event"""
        if Release.installed:
            safe_log('debug', "Already installed, skipping")
            return
            
        if not self.latest:
            safe_log('debug', "Latest release is empty")
            return

        safe_log('debug', "Processing latest release")
        safe_log('debug', f"Current version string: {self.release}")
        safe_log('debug', f"Latest tag_name: {self.latest.get('tag_name')}")

        current = self.version2number(self.release)
        release = self.version2number(self.latest.get("tag_name", "0.0.0"))

        safe_log('debug', f"Current version number: {current}")
        safe_log('debug', f"Latest version number: {release}")

        self.hyperlink["url"] = self.latest.get("html_url", DEFAULT_URL)
        self.hyperlink["text"] = f"EDMC-PlanetPOI: {self.latest.get('tag_name')}"

        if current == release:
            # Current version, hide the release info
            safe_log('debug', "Same version, hiding widget")
            self.grid_remove()
        elif current > release:
            # Experimental/dev version - hide the widget instead of showing experimental message
            safe_log('debug', "Running newer version than release, hiding widget")
            self.grid_remove()
        else:
            # New version available
            safe_log('info', f"New version available: {self.latest.get('tag_name')}")
            auto_update_str = config.get_str("planetpoi_auto_update")
            if auto_update_str == "1":
                # Auto-update enabled - install silently
                safe_log('info', "Auto-update enabled, starting installation")
                self.installer()
            # Always hide in main GUI - update button will show in settings instead
            self.grid_remove()

    def plugin_prefs(self, parent, cmdr, is_beta, gridrow, auto_update_var, auto_remove_backups_var):
        """Create preferences UI using passed IntVars from load.py"""
        # Ensure parent expands horizontally
        parent.columnconfigure(0, weight=1)
        
        frame = nb.Frame(parent)
        frame.columnconfigure(2, weight=1)  # Column 2 expands to push version right
        frame.grid(row=gridrow, column=0, sticky="NSEW")
        
        nb.Checkbutton(
            frame, 
            text="Auto Update This Plugin", 
            variable=auto_update_var
        ).grid(row=0, column=0, sticky="NW")
        
        nb.Checkbutton(
            frame, 
            text="Auto Remove Old Backups", 
            variable=auto_remove_backups_var
        ).grid(row=0, column=1, sticky="NW", padx=(10, 0))
        
        # Version number as hyperlink to repository
        version_link = HyperlinkLabel(
            frame,
            text=f"v{ClientVersion.version()}",
            url="https://github.com/bbbkada/EDMC-PlanetPOI",
            anchor=tk.E
        )
        version_link.grid(row=0, column=2, sticky="NE", padx=(10, 5))
        
        # Update button - only shown when new version is available AND auto-update is disabled
        # Check if update is available - use class variable if instance variable is empty
        latest_data = self.latest if self.latest else Release.latest_release
        safe_log('debug', f"plugin_prefs called - latest_data: {latest_data}")
        
        # Only show update button if auto-update is disabled
        auto_update_enabled = auto_update_var.get() == 1
        
        if latest_data and not auto_update_enabled:
            current = self.version2number(self.release)
            release = self.version2number(latest_data.get("tag_name", "0.0.0"))
            safe_log('debug', f"Version check - current: {current}, release: {release}")
            
            if current < release:
                # New version available - show update button
                safe_log('info', f"Showing update button for {latest_data.get('tag_name')}")
                update_btn = nb.Button(
                    frame,
                    text=f"Update to {latest_data.get('tag_name')}",
                    command=self.click_installer,
                    width=18
                )
                update_btn.grid(row=0, column=3, sticky="NE", padx=(0, 5))
        elif auto_update_enabled:
            safe_log('debug', "Auto-update enabled, hiding update button")
        else:
            safe_log('debug', "No latest release data available")

        return frame

    def click_installer(self):
        """Handle manual install button click"""
        # Run installer and show dialog if successful
        success = self.installer(manual_update=True)
        if success:
            messagebox.showinfo(
                "Update Complete",
                "The plugin has been updated successfully.\n\n"
                "Please restart EDMC for the changes to take effect."
            )

    def installer(self, manual_update=False):
        """Download and install new version
        
        Args:
            manual_update: If True, this is a manual update (not auto-update)
        """
        tag_name = self.latest.get("tag_name")
        
        if not tag_name:
            safe_log('error', "No tag_name in latest release")
            return False

        safe_log('info', f"Installing {tag_name}")
        safe_log('debug', f"Current plugin_dir: {Release.plugin_dir}")
        safe_log('debug', f"Parent dir: {os.path.dirname(Release.plugin_dir)}")

        # Always use the same directory name to avoid duplicates
        new_plugin_dir = os.path.join(
            os.path.dirname(Release.plugin_dir), 
            "EDMC-PlanetPOI-temp"
        )
        
        safe_log('debug', f"Temporary download dir: {new_plugin_dir}")

        # Check if already downloaded (clean up if exists)
        if os.path.isdir(new_plugin_dir):
            safe_log('warning', f"Directory already exists, removing: {new_plugin_dir}")
            try:
                shutil.rmtree(new_plugin_dir)
            except Exception as e:
                safe_log('error', f"Failed to remove existing directory: {e}")
                return False

        try:
            safe_log('debug', "Downloading new version...")
            download_url = f"https://github.com/bbbkada/EDMC-PlanetPOI/archive/refs/tags/{tag_name}.zip"
            safe_log('debug', f"Download URL: {download_url}")
            
            download = requests.get(
                download_url,
                stream=True,
                timeout=30
            )
            
            if not download.status_code == requests.codes.ok:
                safe_log('error', f"Download failed with status {download.status_code}")
                safe_log('error', f"Response: {download.text[:500]}")
                return False

            safe_log('debug', f"Downloaded {len(download.content)} bytes")
            
            # Extract zip file
            safe_log('debug', "Extracting ZIP file...")
            z = zipfile.ZipFile(BytesIO(download.content))
            extract_to = os.path.dirname(Release.plugin_dir)
            safe_log('debug', f"Extracting to: {extract_to}")
            safe_log('debug', f"ZIP contains: {z.namelist()[:5]}")  # Show first 5 files
            z.extractall(extract_to)
            safe_log('debug', "ZIP extraction complete")
            
            # GitHub creates a folder named "EDMC-PlanetPOI-{tag_name}" - rename it to temp name
            extracted_dir = os.path.join(extract_to, f"EDMC-PlanetPOI-{tag_name}")
            if os.path.isdir(extracted_dir):
                safe_log('debug', f"Renaming {extracted_dir} to {new_plugin_dir}")
                os.rename(extracted_dir, new_plugin_dir)
                safe_log('debug', "Rename complete")
            else:
                safe_log('error', f"Expected directory not found: {extracted_dir}")
                # List what actually got extracted
                safe_log('error', f"Contents of {extract_to}:")
                try:
                    for item in os.listdir(extract_to):
                        if item.startswith("EDMC-PlanetPOI"):
                            safe_log('error', f"  - {item}")
                except Exception as list_err:
                    safe_log('error', f"Failed to list directory: {list_err}")
            
        except Exception as e:
            safe_log('error', f"Download/extract failed: {str(e)}")
            return False

        # Verify extracted directory exists after rename
        if not os.path.isdir(new_plugin_dir):
            safe_log('error', f"Temporary directory not found after extraction: {new_plugin_dir}")
            return False
        
        safe_log('debug', f"Verified temporary directory exists: {new_plugin_dir}")

        # Create backup of current plugin directory with old version number and .disabled suffix
        # This prevents EDMC from loading it as a duplicate plugin
        old_version = ClientVersion.version()
        backup_dir = f"{Release.plugin_dir}.{old_version}.disabled"
        safe_log('debug', f"Creating backup with .disabled suffix: {backup_dir}")
        
        try:
            # Remove old backup if it exists
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            # Backup current directory
            shutil.copytree(Release.plugin_dir, backup_dir)
            safe_log('debug', "Backup created successfully")
            
            # Copy new files to current plugin directory (overwrite, except poi.json)
            safe_log('debug', f"Copying new files to {Release.plugin_dir}")
            for item in os.listdir(new_plugin_dir):
                src = os.path.join(new_plugin_dir, item)
                dst = os.path.join(Release.plugin_dir, item)
                
                # NEVER overwrite poi.json - user data must be preserved
                if item == "poi.json" and os.path.exists(dst):
                    safe_log('info', f"Skipping poi.json - preserving existing user data")
                    continue
                
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            safe_log('debug', "Files copied successfully")
            
            # Remove temporary download directory
            shutil.rmtree(new_plugin_dir)
            safe_log('debug', "Temporary directory removed")
            
            # Auto-remove old backups if enabled
            auto_remove_str = config.get_str("planetpoi_auto_remove_backups")
            if auto_remove_str == "1":
                safe_log('info', "Auto-remove backups enabled - removing all backup directories")
                self.remove_old_backups()
            else:
                # Keep the .disabled backup directory for user reference
                safe_log('info', f"Backup created at {backup_dir} (.disabled prevents loading as plugin)")
            
            safe_log('info', f"Upgrade to {tag_name} complete - please restart EDMC")
            Release.installed = True
            return True
            
        except Exception as e:
            safe_log('error', f"Failed to copy files: {e}")
            # Try to restore from backup
            if os.path.exists(backup_dir):
                safe_log('info', "Attempting to restore from backup")
                try:
                    shutil.rmtree(Release.plugin_dir)
                    shutil.copytree(backup_dir, Release.plugin_dir)
                    safe_log('info', "Restored from backup successfully")
                except Exception as restore_error:
                    safe_log('error', f"Failed to restore from backup: {restore_error}")
            
            return False

    def remove_old_backups(self):
        """Remove old .disabled backup directories"""
        try:
            plugins_dir = os.path.dirname(Release.plugin_dir)
            plugin_basename = os.path.basename(Release.plugin_dir)
            
            safe_log('debug', f"Looking for old backups in {plugins_dir}")
            
            for item in os.listdir(plugins_dir):
                # Match pattern: EDMC-PlanetPOI.X.Y.Z.disabled
                if item.startswith(plugin_basename + ".") and item.endswith(".disabled"):
                    backup_path = os.path.join(plugins_dir, item)
                    safe_log('info', f"Removing old backup: {backup_path}")
                    try:
                        shutil.rmtree(backup_path)
                        safe_log('info', f"Successfully removed {item}")
                    except Exception as e:
                        safe_log('error', f"Failed to remove backup {item}: {e}")
        except Exception as e:
            safe_log('error', f"Failed to scan for old backups: {e}")

    @classmethod
    def get_auto(cls):
        """Get auto-update setting"""
        auto_update_str = config.get_str("planetpoi_auto_update")
        return 1 if auto_update_str == "1" else 0

    @classmethod
    def plugin_start(cls, plugin_dir):
        """Initialize plugin directory"""
        cls.plugin_dir = plugin_dir
