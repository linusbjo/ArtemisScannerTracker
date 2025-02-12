"""Artemis Scanner Tracker v0.2.6 by Balvald."""

import json
import logging
import os
import tkinter as tk
from typing import Optional

import myNotebook as nb  # type: ignore # noqa: N813
import requests
from config import appname, config  # type: ignore
from theme import theme  # type: ignore
from ttkHyperlinkLabel import HyperlinkLabel  # type: ignore

import organicinfo as orgi
from journalcrawler import build_biodata_json

frame: Optional[tk.Frame] = None

# Shows debug fields in preferences when True
debug = False

logger = logging.getLogger(f"{appname}.{os.path.basename(os.path.dirname(__file__))}")

PLUGIN_NAME = "AST"

AST_VERSION = "v0.2.6"

AST_REPO = "Balvald/ArtemisScannerTracker"

alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-"

vistagenomicsprices = orgi.getvistagenomicprices()

firstdashboard = True

not_yet_sold_data = {}
sold_exobiology = {}
currententrytowrite = {}
currentcommander = ""
cmdrstates = {}

plugin = None

# Gonna need the files directory to store data for full
# tracking of all the biological things that the CMDR scans.
directory, filename = os.path.split(os.path.realpath(__file__))

filenames = ["\\soldbiodata.json", "\\notsoldbiodata.json",  "\\cmdrstates.json"]

for file in filenames:
    if not os.path.exists(directory + file):
        f = open(directory + file, "w", encoding="utf8")
        f.write(r"{}")
        f.close()
    elif file == "\\soldbiodata.json" or file == "\\notsoldbiodata.json":
        # (not)soldbiodata file already exists
        with open(directory + file, "r+", encoding="utf8") as f:
            test = json.load(f)
            if type([]) == type(test):
                # we have an old version of the (not)soldbiodata.json
                # clear it, have the user do the journal crawling again.
                logger.warning(f"Found old {file} format")
                logger.warning("Clearing file...")
                f.seek(0)
                f.write(r"{}")
                f.truncate()

# load notyetsolddata

with open(directory + "\\notsoldbiodata.json", "r+", encoding="utf8") as f:
    not_yet_sold_data = json.load(f)

with open(directory + "\\cmdrstates.json", "r+", encoding="utf8") as f:
    cmdrstates = json.load(f)


class ArtemisScannerTracker:
    """Artemis Scanner Tracker plugin class."""

    def __init__(self) -> None:
        """Initialize the plugin by getting values from the config file."""
        self.AST_in_Legacy: Optional[bool] = False

        # Be sure to use names that wont collide in our config variables
        # Bools for show hide checkboxes

        self.AST_hide_fullscan: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_fullscan"))
        self.AST_hide_species: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_species"))
        self.AST_hide_progress: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_progress"))
        self.AST_hide_last_system: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_last_system"))
        self.AST_hide_last_body: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_last_body"))
        self.AST_hide_system: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_system"))
        self.AST_hide_body: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_body"))
        self.AST_hide_value: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_value"))
        self.AST_hide_sold_bio: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_sold_bio"))
        self.AST_hide_CCR: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_CCR"))
        self.AST_hide_after_selling: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_after_selling"))
        self.AST_hide_after_full_scan: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_after_full_scan"))
        self.AST_hide_value_when_zero: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_value_when_zero"))

        # option for shorterned numbers
        self.AST_shorten_value: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_shorten_value"))

        # bool to steer when the CCR feature is visible
        self.AST_near_planet: Optional[tk.BooleanVar] = False

        # positions as lat long, lat at index 0, long at index 1
        self.AST_current_pos_vector = [None, None, None]
        self.AST_scan_1_pos_vector = [None, None]
        self.AST_scan_2_pos_vector = [None, None]

        self.AST_CCR: Optional[tk.IntVar] = tk.IntVar(value=0)

        # value to steer the autohiding functionality
        self.AST_after_selling: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_after_selling"))

        # hide feature for Scans in the system for the button:
        self.AST_hide_scans_in_system: Optional[tk.IntVar] = tk.IntVar(value=config.get_int("AST_hide_scans_in_system"))

        # radius of the most current planet
        self.AST_current_radius: Optional[tk.StringVar] = tk.StringVar(value="")

        self.AST_current_pos: Optional[tk.StringVar] = tk.StringVar(value="")
        self.AST_scan_1_pos_dist: Optional[tk.StringVar] = tk.StringVar(value="")
        self.AST_scan_2_pos_dist: Optional[tk.StringVar] = tk.StringVar(value="")

        # last Commander
        self.AST_last_CMDR: Optional[tk.StringVar] = tk.StringVar(value=str(config.get_str("AST_last_CMDR")))

        self.AST_scan_1_dist_green = False
        self.AST_scan_2_dist_green = False

        # Artemis Scanner State infos
        self.AST_last_scan_plant: Optional[tk.StringVar] = tk.StringVar(value=str())
        self.AST_last_scan_system: Optional[tk.StringVar] = tk.StringVar(value=str())
        self.AST_last_scan_body: Optional[tk.StringVar] = tk.StringVar(value=str())
        self.AST_current_scan_progress: Optional[tk.StringVar] = tk.StringVar(value=())
        self.AST_current_system: Optional[tk.StringVar] = tk.StringVar(value=str())
        self.AST_current_body: Optional[tk.StringVar] = tk.StringVar(value=str())
        self.AST_state: Optional[tk.StringVar] = tk.StringVar(value=str())

        self.rawvalue = int(config.get_int("AST_value"))

        if self.rawvalue is None:
            self.rawvalue = 0

        self.AST_value: Optional[tk.StringVar] = tk.StringVar(value=((f"{self.rawvalue:,} Cr.")))

        self.updateavailable = False

        response = requests.get(f"https://api.github.com/repos/{AST_REPO}/releases/latest")

        if response.ok:
            data = response.json()

            if AST_VERSION != data['tag_name']:
                self.updateavailable = True
        else:
            logger.error("Check for update failed!")

        logger.info("ArtemisScannerTracker instantiated")

    def on_load(self) -> str:
        """
        on_load is called by plugin_start3 below.

        It is the first point EDMC interacts with our code
        after loading our module.

        :return: The name of the plugin, which will be used by EDMC for logging
                 and for the settings window
        """
        return PLUGIN_NAME

    def on_unload(self) -> None:
        """
        on_unload is called by plugin_stop below.

        It is the last thing called before EDMC shuts down.
        Note that blocking code here will hold the shutdown process.
        """
        self.on_preferences_closed("", False)  # Save our prefs

    def setup_preferences(self, parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]: # noqa #CCR001
        """
        setup_preferences is called by plugin_prefs below.

        It is where we can setup our
        own settings page in EDMC's settings window.
        Our tab is defined for us.

        :param parent: the tkinter parent that our returned Frame will want to inherit from
        :param cmdr: The current ED Commander
        :param is_beta: Whether or not EDMC is currently marked as in beta mode
        :return: The frame to add to the settings window
        """
        global currentcommander
        currentcommander = cmdr
        if currentcommander != "" and currentcommander is not None:
            load_cmdr(cmdr)

        line = "_____________________________________________________"

        current_row = 0
        frame = nb.Frame(parent)

        prefs_label(frame, f"Artemis Scanner Tracker {AST_VERSION} by Balvald", current_row, 0, tk.W)

        current_row += 1

        prefs_label(frame, line, current_row, 0, tk.W)
        prefs_label(frame, line, current_row, 1, tk.W)

        current_row += 1

        checkboxlistleft = ["Hide full status", "Hide species",
                            "Hide system of last Scan", "Hide current system",
                            "Hide scanned/sold species in system", line,
                            "Autom. hide values after selling all", "Autom. hide unsold value when 0 Cr."]
        checkboxlistright = ["Hide value of unsold Scans", "Hide scan progress",
                             "Hide body of last Scan", "Hide current Body",
                             "Hide clonal colonial distances", line,
                             "Autom. hide values after finished scan", "Force hide/show autom. hidden"]

        variablelistleft = [self.AST_hide_fullscan, self.AST_hide_species,
                            self.AST_hide_last_system, self.AST_hide_system,
                            self.AST_hide_sold_bio, line, self.AST_hide_after_selling,
                            self.AST_hide_value_when_zero]
        variablelistright = [self.AST_hide_value, self.AST_hide_progress,
                             self.AST_hide_last_body, self.AST_hide_body,
                             self.AST_hide_CCR, line,
                             self.AST_hide_after_full_scan]

        for i in range(max(len(checkboxlistleft), len(checkboxlistright))):
            if i < len(checkboxlistleft):
                if checkboxlistleft[i] == line:
                    prefs_label(frame, line, current_row, 0, tk.W)
                else:
                    prefs_tickbutton(frame, checkboxlistleft[i], variablelistleft[i], current_row, 0, tk.W)
            if i < len(checkboxlistright):
                if checkboxlistright[i] == line:
                    prefs_label(frame, line, current_row, 1, tk.W)
                    current_row += 1
                    continue
                if checkboxlistright[i] == "Force hide/show autom. hidden":
                    prefs_button(frame, checkboxlistright[i], self.forcehideshow, current_row, 1, tk.W)
                    current_row += 1
                    continue
                prefs_tickbutton(frame, checkboxlistright[i], variablelistright[i], current_row, 1, tk.W)
            current_row += 1

        if debug:

            debuglistleft = ["species", "System of last Scan",
                             "Body of last Scan", "Scan progress",
                             "Scanned Value"]
            debuglistright = [self.AST_last_scan_plant, self.AST_last_scan_system,
                              self.AST_last_scan_body, self.AST_current_scan_progress,
                              self.AST_value]

            for i in range(max(len(debuglistleft), len(debuglistright))):
                if i < len(debuglistleft):
                    prefs_label(frame, debuglistleft[i], current_row, 0, tk.W)
                if i < len(debuglistright):
                    prefs_entry(frame, debuglistright[i], current_row, 1, tk.W)
                current_row += 1

        prefs_label(frame, line, current_row, 0, tk.W)
        prefs_label(frame, line, current_row, 1, tk.W)

        current_row += 1

        prefs_tickbutton(frame, "Shorten credit values", self.AST_shorten_value, current_row, 0, tk.W)

        current_row += 1

        prefs_label(frame, line, current_row, 0, tk.W)
        prefs_label(frame, line, current_row, 1, tk.W)

        current_row += 1

        text = "Scan game journals for exobiology"
        prefs_button(frame, text, self.buildsoldbiodatajson, current_row, 0, tk.W)
        text = "Scan local journal folder for exobiology"
        prefs_button(frame, text, self.buildsoldbiodatajsonlocal, current_row, 1, tk.W)

        current_row += 1

        prefs_label(frame, line, current_row, 0, tk.W)
        prefs_label(frame, line, current_row, 1, tk.W)

        current_row += 1

        text = "To reset the status, body, system and species"
        prefs_label(frame, text, current_row, 0, tk.W)

        current_row += 1

        text = "of the last scan press the button below"
        prefs_label(frame, text, current_row, 0, tk.W)

        current_row += 1

        prefs_button(frame, "RESET", self.reset, current_row, 0, tk.W)

        current_row += 1

        return frame

    def on_preferences_closed(self, cmdr: str, is_beta: bool) -> None:
        """
        on_preferences_closed is called by prefs_changed below.

        It is called when the preferences dialog is dismissed by the user.

        :param cmdr: The current ED Commander
        :param is_beta: Whether or not EDMC is currently marked as in beta mode
        """
        global currentcommander, plugin
        if currentcommander != "" and currentcommander is not None:
            save_cmdr(currentcommander)
        if currentcommander != cmdr and cmdr != "" and cmdr is not None:
            currentcommander = cmdr
            load_cmdr(currentcommander)

        # Update last scan plant for switch of the shortening value option
        update_last_scan_plant()

        if self.AST_shorten_value.get():
            self.AST_value.set(shortcreditstring(self.rawvalue))
        else:
            self.AST_value.set(f"{self.rawvalue:,} Cr.")

        worth = self.AST_last_scan_plant.get().split(" (")[1]
        self.AST_state.set(str(self.AST_last_scan_plant.get().split(" (")[0]) + " (" +
                           self.AST_current_scan_progress.get() + ") on: " +
                           self.AST_last_scan_body.get() + " (" + str(worth))

        config.set("AST_value", int(self.rawvalue))

        config.set("AST_hide_value", int(self.AST_hide_value.get()))
        config.set("AST_hide_fullscan", int(self.AST_hide_fullscan.get()))
        config.set("AST_hide_species", int(self.AST_hide_species.get()))
        config.set("AST_hide_progress", int(self.AST_hide_progress.get()))
        config.set("AST_hide_last_system", int(self.AST_hide_last_system.get()))
        config.set("AST_hide_last_body", int(self.AST_hide_last_body.get()))
        config.set("AST_hide_system", int(self.AST_hide_system.get()))
        config.set("AST_hide_body", int(self.AST_hide_body.get()))
        config.set("AST_hide_sold_bio", int(self.AST_hide_sold_bio.get()))
        config.set("AST_hide_CCR", int(self.AST_hide_CCR.get()))
        config.set("AST_hide_after_selling", int(self.AST_hide_after_selling.get()))
        config.set("AST_hide_after_full_scan", int(self.AST_hide_after_full_scan.get()))
        config.set("AST_hide_value_when_zero", int(self.AST_hide_value_when_zero.get()))

        config.set("AST_shorten_value", int(self.AST_shorten_value.get()))

        config.set("AST_after_selling", int(self.AST_after_selling.get()))

        config.set("AST_hide_scans_in_system", int(self.AST_hide_scans_in_system.get()))

        logger.debug(f"Currently last Commander is: {cmdr}")

        config.set("AST_last_CMDR", str(cmdr))

        logger.debug("ArtemisScannerTracker saved preferences")

        rebuild_ui(plugin, cmdr)

    def setup_main_ui(self, parent: tk.Frame) -> tk.Frame:
        """
        Create our entry on the main EDMC UI.

        This is called by plugin_app below.

        :param parent: EDMC main window Tk
        :return: Our frame
        """
        global frame, currentcommander

        try:
            load_cmdr(self.AST_last_CMDR.get())
        except KeyError:
            # last Commander saved is just not known
            pass

        frame = tk.Frame(parent)

        rebuild_ui(self, currentcommander)

        return frame

    def reset(self) -> None:
        """Reset function of the Reset Button."""
        self.AST_current_scan_progress.set("0/3")
        self.AST_last_scan_system.set("")
        self.AST_last_scan_body.set("")
        self.AST_last_scan_plant.set("None")
        self.AST_state.set("None")
        self.rawvalue = 0
        self.AST_value.set("0 Cr.")
        self.AST_scan_1_pos_vector = [None, None]
        self.AST_scan_2_pos_vector = [None, None]

    def clipboard(self) -> None:
        """Copy value to clipboard."""
        dummytk = tk.Tk()  # creates a window we don't want
        dummytk.clipboard_clear()
        dummytk.clipboard_append(self.rawvalue)
        dummytk.destroy()  # destroying it again we don't need another full window everytime we copy to clipboard.

    def forcehideshow(self) -> None:
        """Force plugin to show values when Auto hide is on."""
        global currentcommander, frame

        state = bool(self.AST_after_selling.get())
        self.AST_after_selling.set(int(not (state)))
        rebuild_ui(self, currentcommander)

    def switchhidesoldexobio(self) -> None:
        """Switch the ui button to expand and collapse the list of sold/scanned exobiology."""
        global currentcommander, frame
        state = bool(self.AST_hide_scans_in_system.get())
        self.AST_hide_scans_in_system.set(int(not (state)))
        rebuild_ui(self, currentcommander)

    def buildsoldbiodatajsonlocal(self) -> None:
        """Build the soldbiodata.json using the neighboring journalcrawler.py searching through local journal folder."""
        global logger
        directory, filename = os.path.split(os.path.realpath(__file__))

        self.rawvalue = build_biodata_json(logger, os.path.join(directory, "journals"))

    def buildsoldbiodatajson(self) -> None:
        """Build the soldbiodata.json using the neighboring journalcrawler.py."""
        # Always uses the game journal directory

        global logger

        # this the actual path from the config.
        journaldir = config.get_str('journaldir')

        if journaldir in [None, "", "None"]:
            # config.default_journal_dir is a fallback that won't work in a linux context
            journaldir = config.default_journal_dir

        self.rawvalue = build_biodata_json(logger, journaldir)


# region eventhandling

def dashboard_entry(cmdr: str, is_beta, entry) -> None:  # noqa #CCR001
    """
    React to changes in the CMDRs status (Movement for CCR feature).

    :param cmdr: The current ED Commander
    :param is_beta: Is the game currently in beta
    :param entry: full excerpt from status.json
    """
    global plugin, currentcommander, firstdashboard

    if plugin.AST_in_Legacy is True:
        # We're in legacy we don't update anything through dashboard entries
        return

    flag = False

    if currentcommander != cmdr and currentcommander != "" and currentcommander is not None:
        # Check if new and old Commander are in the cmdrstates file.
        save_cmdr(currentcommander)
        # New Commander not in cmdr states file.
        if cmdr not in cmdrstates.keys():
            # completely new cmdr theres nothing to load
            cmdrstates[cmdr] = ["None", "None", "None", "0/3", "None", 0, "None", "None", "None"]
        else:
            if cmdr is not None and cmdr != "":
                load_cmdr(cmdr)

        # Set new Commander to currentcommander
        currentcommander = cmdr

        flag = True

    if firstdashboard:
        firstdashboard = False
        plugin.on_preferences_closed(cmdr, is_beta)

    if "PlanetRadius" in entry.keys():
        # We found a PlanetRadius again, this means we are near a planet.
        if not plugin.AST_near_planet:
            # We just came into range of a planet again.
            flag = True
        plugin.AST_near_planet = True
        plugin.AST_current_radius = entry["PlanetRadius"]
        plugin.AST_current_pos_vector[0] = entry["Latitude"]
        plugin.AST_current_pos_vector[1] = entry["Longitude"]
        plugin.AST_current_pos_vector[2] = entry["Heading"]
        if plugin.AST_current_pos_vector[2] < 0:
            # Frontier gives us different value intervals for headings in the status.json
            # Within a vehicle (srv, ship) its (0, 360) but on foot it is (-180, 180) ffs!
            # With this change we force every bearing to be in the (0, 360) interval
            plugin.AST_current_pos_vector[2] += 360
        text = "lat: " + str(round(plugin.AST_current_pos_vector[0], 2)) + \
               ", long: " + str(round(plugin.AST_current_pos_vector[1], 2)) + ", B:" + \
               str(plugin.AST_current_pos_vector[2])  # + ", " + str(plugin.AST_current_radius)
        plugin.AST_current_pos.set(text)

        if plugin.AST_current_scan_progress.get() in ["1/3", "2/3"] and plugin.AST_scan_1_pos_vector[0] is not None:
            distance1 = orgi.computedistance(plugin.AST_current_pos_vector[0],
                                             plugin.AST_current_pos_vector[1],
                                             plugin.AST_scan_1_pos_vector[0],
                                             plugin.AST_scan_1_pos_vector[1],
                                             plugin.AST_current_radius)
            plugin.AST_scan_1_pos_dist.set(str(round(distance1))
                                           + " m / " + str(plugin.AST_CCR.get()) + " m, B:" +
                                           str(round(orgi.bearing(plugin.AST_current_pos_vector[0],
                                                                  plugin.AST_current_pos_vector[1],
                                                                  plugin.AST_scan_1_pos_vector[0],
                                                                  plugin.AST_scan_1_pos_vector[1]), 2)))
            olddist1check = plugin.AST_scan_1_dist_green
            plugin.AST_scan_1_dist_green = False
            if plugin.AST_CCR.get() < distance1:
                plugin.AST_scan_1_dist_green = True
            if olddist1check != plugin.AST_scan_1_dist_green:
                flag = True
        if plugin.AST_current_scan_progress.get() in ["1/3", "2/3"] and plugin.AST_scan_2_pos_vector[0] is not None:
            distance2 = orgi.computedistance(plugin.AST_current_pos_vector[0],
                                             plugin.AST_current_pos_vector[1],
                                             plugin.AST_scan_2_pos_vector[0],
                                             plugin.AST_scan_2_pos_vector[1],
                                             plugin.AST_current_radius)
            plugin.AST_scan_2_pos_dist.set(str(round(distance2, 2))
                                           + " m / " + str(plugin.AST_CCR.get()) + " m, B:" +
                                           str(round(orgi.bearing(plugin.AST_current_pos_vector[0],
                                                                  plugin.AST_current_pos_vector[1],
                                                                  plugin.AST_scan_2_pos_vector[0],
                                                                  plugin.AST_scan_2_pos_vector[1]), 2)))
            olddist2check = plugin.AST_scan_2_dist_green
            plugin.AST_scan_2_dist_green = False
            if plugin.AST_CCR.get() < distance2:
                plugin.AST_scan_2_dist_green = True
            if olddist2check != plugin.AST_scan_2_dist_green:
                flag = True
    else:
        if plugin.AST_near_planet:
            # Switch happened we went too far from the planet to get any reference from it.
            flag = True
        plugin.AST_near_planet = False
        plugin.AST_current_radius = None
        plugin.AST_current_pos_vector[0] = None
        plugin.AST_current_pos_vector[1] = None
        plugin.AST_current_pos_vector[2] = None
        plugin.AST_current_pos.set("No reference point")

    if flag:
        rebuild_ui(plugin, cmdr)


def journal_entry(cmdr: str, is_beta: bool, system: str, station: str, entry, state) -> None:  # noqa #CCR001
    """
    React accordingly to events in the journal.

    Scan Organic events tell us what we have scanned.
    Scan Type of these events can tell us the progress of the scan.
    Add the value of a finished Scan to the tally
    :param cmdr: The current ED Commander
    :param is_beta: Is the game currently in beta
    :param system: Current system, if known
    :param station: Current station, if any
    :param entry: the current Journal entry
    :param state: More info about the commander, their ship, and their cargo
    """
    global plugin, currentcommander

    if (int(state["GameVersion"][0]) < 4) and (plugin.AST_in_Legacy is False):
        # We're in Legacy, we'll not change the state of anything through journal entries.
        plugin.AST_in_Legacy = True
        return
    else:
        plugin.AST_in_Legacy = False

    if currentcommander != cmdr and currentcommander != "" and currentcommander is not None:
        # Check if new and old Commander are in the cmdrstates file.
        save_cmdr(currentcommander)
        # New Commander not in cmdr states file.
        if cmdr not in cmdrstates.keys():
            # completely new cmdr theres nothing to load
            cmdrstates[cmdr] = ["None", "None", "None", "0/3", "None", 0, "None", "None", "None"]
        else:
            # Load cmdr from cmdr states.
            if cmdr is not None:
                load_cmdr(cmdr)
        # Set new Commander to currentcommander
        currentcommander = cmdr

        rebuild_ui(plugin, cmdr)

    if plugin.AST_current_system.get() != system:
        plugin.AST_current_system.set(system)
        rebuild_ui(plugin, cmdr)

    if plugin.AST_current_system.get() == "" or plugin.AST_current_system.get() == "None":
        plugin.AST_current_system.set(str(system))

    flag = False

    # TODO: Check if upon death in 4.0 Horizons do we lose Exobiodata.
    # Probably?
    # Check how real death differs from frontline solutions ground combat zone death.
    # Yes it does. Frontline solutions does not have a Resurrect event.

    if entry["event"] == "Resurrect":
        # Reset - player was unable to sell before death
        flag = True
        resurrection_event(cmdr)

    if entry["event"] == "ScanOrganic":
        flag = True
        bioscan_event(cmdr, is_beta, entry)

    if entry["event"] in ["Location", "Embark", "Disembark", "Touchdown", "Liftoff", "FSDJump"]:
        flag = True
        system_body_change_event(cmdr, entry)

    if entry["event"] == "SellOrganicData":
        flag = True
        biosell_event(cmdr, entry)

    if flag:
        # save most recent relevant state so in case of crash of the system
        # we still have a proper record as long as it finishes saving below.
        plugin.on_preferences_closed(cmdr, is_beta)


def resurrection_event(cmdr: str) -> None:
    """Handle resurrection event aka dying."""
    global not_yet_sold_data, plugin
    not_yet_sold_data[cmdr] = []
    plugin.rawvalue = 0
    plugin.AST_value.set("0 Cr.")
    plugin.AST_current_scan_progress.set("0/3")


def bioscan_event(cmdr: str, is_beta, entry) -> None:  # noqa #CCR001
    """Handle the ScanOrganic event."""
    global currententrytowrite, plugin, vistagenomicsprices

    # In the eventuality that the user started EMDC after
    # the "Location" event happens and directly scans a plant
    # these lines wouldn"t be able to do anything but to
    # set the System and body of the last Scan to "None"
    old_AST_last_scan_system = plugin.AST_last_scan_system.get()
    old_AST_last_scan_body = plugin.AST_last_scan_body.get()
    old_AST_last_scan_plant = str(plugin.AST_last_scan_plant.get().split(" (Worth: ")[0])

    plugin.AST_last_scan_system.set(plugin.AST_current_system.get())
    plugin.AST_last_scan_body.set(plugin.AST_current_body.get())
    plantname, plantworth = update_last_scan_plant(entry)

    if entry["ScanType"] == "Log":
        plugin.AST_current_scan_progress.set("1/3")
        plugin.AST_CCR.set(orgi.getclonalcolonialranges(orgi.genusgeneraltolocalised(entry["Genus"])))
        plugin.AST_scan_1_pos_vector[0] = plugin.AST_current_pos_vector[0]
        plugin.AST_scan_1_pos_vector[1] = plugin.AST_current_pos_vector[1]
        plugin.AST_scan_2_pos_vector = [None, None]
        plugin.AST_scan_2_pos_dist.set("")
        plugin.on_preferences_closed(cmdr, is_beta)
    elif entry["ScanType"] in ["Sample", "Analyse"]:
        if (entry["ScanType"] == "Analyse"):

            plugin.rawvalue += int(plantworth)

            if plugin.AST_shorten_value.get():
                plugin.AST_value.set(shortcreditstring(plugin.rawvalue))
            else:
                plugin.AST_value.set(f"{plugin.rawvalue:,} Cr.")
            # Found some cases where the analyse happened
            # seemingly directly after a log.
            plugin.AST_current_scan_progress.set("3/3")
            # clear the scan locations to [None, None]
            plugin.AST_scan_1_pos_vector = [None, None]
            plugin.AST_scan_2_pos_vector = [None, None]
            plugin.AST_scan_1_dist_green = False
            plugin.AST_scan_2_dist_green = False
            plugin.AST_CCR.set(0)
            plugin.AST_scan_1_pos_dist.set("")
            plugin.AST_scan_2_pos_dist.set("")
            currententrytowrite["species"] = plantname
            currententrytowrite["system"] = plugin.AST_current_system.get()
            currententrytowrite["body"] = plugin.AST_current_body.get()
            if cmdr not in not_yet_sold_data.keys():
                not_yet_sold_data[cmdr] = []
            if currententrytowrite not in not_yet_sold_data[cmdr]:
                # If there is no second Sample scantype event
                # we have to save the data here.
                not_yet_sold_data[cmdr].append(currententrytowrite)
                file = directory + "\\notsoldbiodata.json"
                with open(file, "r+", encoding="utf8") as f:
                    notsolddata = json.load(f)
                    if cmdr not in notsolddata.keys():
                        notsolddata[cmdr] = []
                    notsolddata[cmdr].append(currententrytowrite)
                    f.seek(0)
                    json.dump(notsolddata, f, indent=4)
                    f.truncate()
                currententrytowrite = {}
        else:
            notthesame = (not (old_AST_last_scan_system == plugin.AST_last_scan_system.get()
                          and old_AST_last_scan_body == plugin.AST_last_scan_body.get()
                          and old_AST_last_scan_plant == str(plugin.AST_last_scan_plant.get().split(" (Worth: ")[0])))
            # Check if we already have scan progress 2/3 with same species on the same body.
            # case 1: "0/3" not the same -> clear 1st distance change 2nd
            # case 2: "0/3" same -> change 2nd distance
            # case 3: "1/3" not the same -> clear 1st distance change 2nd
            # case 4: "1/3" same -> change 2nd distance
            # case 5: "2/3" not the same -> clear 1st distance change 2nd
            # case 6: "2/3" same -> no changing!
            # case 7: "3/3" not the same -> clear 1st distance change 2nd
            # case 8: "3/3" same -> clear 1st distance change 2nd

            if (plugin.AST_current_scan_progress.get() != "2/3"):
                # case 1, 2, 3, 4, 7, 8 change second distance
                plugin.AST_scan_2_pos_vector[0] = plugin.AST_current_pos_vector[0]
                plugin.AST_scan_2_pos_vector[1] = plugin.AST_current_pos_vector[1]

            # clear 1st distance when not the same body and species as previous scan.

            if (plugin.AST_current_scan_progress.get() == "3/3"):
                # case 7, 8 clear 1st distance
                plugin.AST_scan_1_pos_vector = [None, None]
                plugin.AST_scan_1_pos_dist.set("")

            if notthesame:
                # case 1, 3, 5, 7 clear first distance
                plugin.AST_scan_1_pos_vector = [None, None]
                plugin.AST_scan_1_pos_dist.set("")
                if (plugin.AST_current_scan_progress.get() == "2/3"):
                    # case 5 change second distance
                    plugin.AST_scan_2_pos_vector[0] = plugin.AST_current_pos_vector[0]
                    plugin.AST_scan_2_pos_vector[1] = plugin.AST_current_pos_vector[1]

            plugin.AST_current_scan_progress.set("2/3")
            plugin.AST_CCR.set(orgi.getclonalcolonialranges(orgi.genusgeneraltolocalised(entry["Genus"])))
    else:
        # Something is horribly wrong if we end up here
        # If anyone ever sees this
        # we know they added a new ScanType, that we might need to handle
        plugin.AST_current_scan_progress.set("Excuse me what the fuck ¯\\(°_o)/¯")

    plugin.AST_after_selling.set(0)

    if plugin.AST_hide_after_full_scan.get() == 1 and plugin.AST_current_scan_progress.get() == "3/3":
        plugin.AST_after_selling.set(1)

    # We now need to rebuild regardless how far we progressed
    rebuild_ui(plugin, cmdr)


def update_last_scan_plant(entry=None):
    """."""
    global plugin
    plantname = str(plugin.AST_last_scan_plant.get().split(" (Worth: ")[0])
    if entry is not None:
        plantname = orgi.generaltolocalised(entry["Species"].lower())
    try:
        plantworth = vistagenomicsprices[plantname]
        worthstring = f"{plantworth:,} Cr."
    except KeyError:
        plantworth = None
        worthstring = "N/A"
    if plugin.AST_shorten_value.get():
        worthstring = shortcreditstring(plantworth)
    plugin.AST_last_scan_plant.set(plantname + " (Worth: " + worthstring + ")")
    return plantname, plantworth


def system_body_change_event(cmdr: str, entry) -> None:  # noqa #CCR001
    """Handle all events that give a tell in which system we are or on what planet we are on."""
    global plugin

    systemchange = False

    try:
        if plugin.AST_current_system.get() != entry["StarSystem"]:
            systemchange = True
        # Get current system name and body from events that need to happen.
        plugin.AST_current_system.set(entry["StarSystem"])
        plugin.AST_current_body.set(entry["Body"])
    except KeyError:
        # Could throw a KeyError in old Horizons versions
        pass

    if systemchange:
        rebuild_ui(plugin, cmdr)

    # To fix the aforementioned eventuality where the systems end up
    # being "None" we update the last scan location
    # When the CMDR gets another journal entry that tells us
    # the players location.

    if (((plugin.AST_last_scan_system.get() == "")
         or (plugin.AST_last_scan_body.get() == "")
         or (plugin.AST_last_scan_system.get() == "None")
         or (plugin.AST_last_scan_body.get() == "None"))):
        plugin.AST_last_scan_system.set(entry["StarSystem"])
        plugin.AST_last_scan_body.set(entry["Body"])

    if cmdrstates[cmdr][1] == "" or cmdrstates[cmdr][2] == "":
        cmdrstates[cmdr][1] = plugin.AST_last_scan_system.get()
        cmdrstates[cmdr][2] = plugin.AST_last_scan_body.get()
        save_cmdr(cmdr)


def biosell_event(cmdr: str, entry) -> None:  # noqa #CCR001
    """Handle the SellOrganicData event."""
    global currententrytowrite, not_yet_sold_data, sold_exobiology
    soldvalue = 0

    logger.info('called biosell_event')

    if cmdr != "" and cmdr is not None and cmdr not in sold_exobiology.keys():
        sold_exobiology[cmdr] = {alphabet[i]: {} for i in range(len(alphabet))}

    # currentbatch describes which species we are selling.
    # currentbatch has the form: {<species> : <amount> , ....}
    currentbatch = {}

    for sold in entry["BioData"]:
        if sold["Species_Localised"] in currentbatch.keys():
            # found that we are selling at least two of the same species
            currentbatch[sold["Species_Localised"]] += 1
        else:
            currentbatch[sold["Species_Localised"]] = 1
        # Adding the value of the sold species to the tally
        soldvalue += sold["Value"]
        # If I add a counter for all biodata sold
        # I would also need to look at biodata["Bonus"]
        # -> Nah its impossible to track bonus while not sold yet
        # Could only be used for a profit since last reset metric.
    # build by system dict, has the form of {<system> : {<species> : <amount>}}
    logger.info(f'Value that was sold: {soldvalue}')
    bysystem = {}
    if cmdr not in not_yet_sold_data.keys():
        not_yet_sold_data[cmdr] = []
    for biodata in not_yet_sold_data[cmdr]:
        if biodata["system"] in bysystem.keys():
            # We already know the system
            if (biodata["species"] in bysystem[biodata["system"]].keys()):
                # We also have found the same species before
                # We've found atleast 2
                bysystem[biodata["system"]][biodata["species"]] += 1
            else:
                # Species was not catologued in the bysystem structure
                bysystem[biodata["system"]][biodata["species"]] = 1
        else:
            # create new entry for the system and add the single species to it
            bysystem[biodata["system"]] = {}
            bysystem[biodata["system"]][biodata["species"]] = 1

    # Create a structure to check which system might be the one that we are selling
    soldbysystempossible = {}

    # Get every system
    for system in bysystem:
        # and we assume every system to be the one that was possibly sold from
        soldbysystempossible[system] = True
        for species in currentbatch:
            if species not in bysystem[system].keys():
                # Species that we are selling does not appear in its bysystem structure
                # so it cant be the system that we sold from
                soldbysystempossible[system] = False
                # since we found out the system can't be the one we sold we break here
                # and continue with the next system
                break
            if soldbysystempossible[system] is False:
                continue
            # Checking if we have any systems that have too few of a certain species
            if bysystem[system][species] < currentbatch[species]:
                soldbysystempossible[system] = False
                break
    logger.info(f'All possible systems: {soldbysystempossible}')
    # this is still not perfect because it cannot be.
    # if the player sells the data by system and 2 systems
    # have the same amount of the same species then no one can tell
    # which system was actually sold at vista genomics.
    # In described case whatever is the first system we encounter
    # through iteration will be chosen as the system that was sold.
    thesystem = ""

    amountpossiblesystems = sum(1 for value in soldbysystempossible.values() if value is True)

    for system in soldbysystempossible:
        if soldbysystempossible[system] is True:
            if amountpossiblesystems > 1:
                logger.warning('More than one system could have been the one getting sold.')
                logger.warning('Please sell all other data before your next death.')
                logger.warning('Otherwise the soldbiodata.json may have uncatchable discrepancies.')
            # We always take the first system that is possible
            # If there are two we cannot tell which one was sold
            # Though it should not really matter as long as
            # the CMDR hasn't died right after without selling
            # the data aswell.
            thesystem = system
            logger.info(f'Likely system that was sold from: {thesystem}')
            break

    if thesystem != "":
        # CMDR sold by system.
        i = 0
        while i < len(not_yet_sold_data[cmdr]):
            # Check if were done with the batch we sold yet
            done = True
            for species in currentbatch:
                if currentbatch[species] > 0:
                    done = False
            if done:
                break

            firstletter = not_yet_sold_data[cmdr][i]["system"][0].lower()
            if firstletter not in alphabet:
                firstletter = "-"
            # Checking here more granularily which data was sold
            # We do know though that the specifc data was sold only
            # in one system that at this point is saved in
            # the variable"thesystem"
            if (thesystem not in sold_exobiology[cmdr][firstletter].keys()
               and (thesystem[0].lower() == firstletter or firstletter == "-")):
                sold_exobiology[cmdr][firstletter][thesystem] = []

            check = (not_yet_sold_data[cmdr][i]["system"] == thesystem
                     and not_yet_sold_data[cmdr][i]
                     not in sold_exobiology[cmdr][firstletter][thesystem]
                     and not_yet_sold_data[cmdr][i]["species"] in currentbatch.keys())

            if check:
                if currentbatch[not_yet_sold_data[cmdr][i]["species"]] > 0:
                    sold_exobiology[cmdr][firstletter][thesystem].append(not_yet_sold_data[cmdr][i])
                    currentbatch[not_yet_sold_data[cmdr][i]["species"]] -= 1
                    not_yet_sold_data[cmdr].pop(i)
                    continue
            i += 1

        f = open(directory + "\\notsoldbiodata.json", "r+", encoding="utf8")
        scanneddata = json.load(f)
        scanneddata[cmdr] = []
        f.seek(0)
        json.dump(scanneddata, f, indent=4)
        f.truncate()
        f.close()

        if not_yet_sold_data[cmdr] != []:
            file = directory + "\\notsoldbiodata.json"
            with open(file, "r+", encoding="utf8") as f:
                notsolddata = json.load(f)
                for data in not_yet_sold_data[cmdr]:
                    notsolddata[cmdr].append(data)
                f.seek(0)
                json.dump(notsolddata, f, indent=4)
                f.truncate()

    else:
        # CMDR sold the whole batch.
        for data in not_yet_sold_data[cmdr]:
            firstletter = data["system"][0].lower()
            if firstletter not in alphabet:
                firstletter = "-"

            if (data["system"] not in sold_exobiology[cmdr][firstletter].keys()
               and (data["system"][0].lower() == firstletter or firstletter == "-")):
                sold_exobiology[cmdr][firstletter][data["system"]] = []

            if data["species"] not in currentbatch.keys():
                continue

            if (data not in sold_exobiology[cmdr][firstletter][data["system"]]
               and currentbatch[data["species"]] > 0):
                currentbatch[data["species"]] -= 1
                sold_exobiology[cmdr][firstletter][data["system"]].append(data)
        not_yet_sold_data[cmdr] = []
        # We can already reset to 0 to ensure that after selling all data at once
        # we end up with a reset of the Scanned value metric
        logger.info('Set Unsold Scan Value to 0 Cr')
        plugin.AST_value.set("0 Cr.")
        plugin.rawvalue = 0
        f = open(directory + "\\notsoldbiodata.json", "r+", encoding="utf8")
        scanneddata = json.load(f)
        scanneddata[cmdr] = []
        f.seek(0)
        json.dump(scanneddata, f, indent=4)
        f.truncate()
        f.close()

    # Remove the value of what was sold from
    # the amount of the Scanned value.
    # Specifically so that the plugin still keeps track properly,
    # when the player sells on a by system basis.
    logger.info(f'Removing {soldvalue} from plugin value')
    plugin.rawvalue -= soldvalue
    # newvalue = int(plugin.AST_value.get().replace(",", "").split(" ")[0]) - soldvalue
    if plugin.AST_shorten_value.get():
        plugin.AST_value.set(shortcreditstring(plugin.rawvalue))
    else:
        plugin.AST_value.set(f"{plugin.rawvalue:,} Cr.")

    # No negative value of biodata could still be unsold on the Scanner
    # This means that there was data on the Scanner that
    # the plugin was unable to record by not being active.
    # If the value was reset before we will reset it here again.
    if int(plugin.rawvalue) < 0:
        logger.info('Set Unsold Scan Value to 0 Cr')
        plugin.AST_value.set("0 Cr.")
        plugin.rawvalue = 0
    # Now write the data into the local file
    file = directory + "\\soldbiodata.json"
    with open(file, "r+", encoding="utf8") as f:
        solddata = json.load(f)

        if cmdr not in solddata.keys():
            solddata[cmdr] = {alphabet[i]: {} for i in range(len(alphabet))}

        if sold_exobiology[cmdr] != []:
            for letter in sold_exobiology[cmdr]:
                for system in sold_exobiology[cmdr][letter]:
                    if system not in solddata[cmdr][letter].keys():
                        solddata[cmdr][letter][system] = []
                    for item in sold_exobiology[cmdr][letter][system]:
                        solddata[cmdr][letter][system].append(item)
            sold_exobiology[cmdr] = {alphabet[i]: {} for i in range(len(alphabet))}
        f.seek(0)
        json.dump(solddata, f, indent=4)
        f.truncate()

    # After selling all the unsold value we finished selling and things switch to hiding things if
    # we are in autohiding mode
    if (plugin.rawvalue == 0 and plugin.AST_hide_after_selling.get() == 1):
        plugin.AST_after_selling.set(1)

    # If we sell the exobiodata in the same system as where we currently are
    # Then we want to remove the "*" around the body names of the newly sold biodata
    # So just rebuild the ui for good measure.
    rebuild_ui(plugin, cmdr)

# endregion


plugin = ArtemisScannerTracker()


# region saving/loading


def save_cmdr(cmdr) -> None:
    """Save information specific to the cmdr in the cmdrstates.json."""
    global plugin, directory

    if cmdr not in cmdrstates.keys():
        cmdrstates[cmdr] = ["None", "None", "None", "0/3", "None", 0, "None", "None", "None"]

    valuelist = [plugin.AST_last_scan_plant.get(), plugin.AST_last_scan_system.get(), plugin.AST_last_scan_body.get(),
                 plugin.AST_current_scan_progress.get(), plugin.AST_state.get(), plugin.rawvalue,
                 plugin.AST_CCR.get(), plugin.AST_scan_1_pos_vector.copy(), plugin.AST_scan_2_pos_vector.copy()]

    for i in range(len(cmdrstates[cmdr])):
        cmdrstates[cmdr][i] = valuelist[i]

    file = directory + "\\cmdrstates.json"

    open(file, "r+", encoding="utf8").close()
    with open(file, "r+", encoding="utf8") as f:
        f.seek(0)
        json.dump(cmdrstates, f, indent=4)
        f.truncate()


def load_cmdr(cmdr) -> None:
    """Load information about a cmdr from cmdrstates.json."""
    global cmdrstates, plugin
    file = directory + "\\cmdrstates.json"

    with open(file, "r+", encoding="utf8") as f:
        cmdrstates = json.load(f)

    plugin.AST_last_scan_plant.set(cmdrstates[cmdr][0])
    plugin.AST_last_scan_system.set(cmdrstates[cmdr][1])
    plugin.AST_last_scan_body.set(cmdrstates[cmdr][2])
    plugin.AST_current_scan_progress.set(cmdrstates[cmdr][3])
    plugin.AST_state.set(cmdrstates[cmdr][4])
    plugin.rawvalue = int(str(cmdrstates[cmdr][5]).split(" ")[0].replace(",", ""))
    plugin.AST_CCR.set(cmdrstates[cmdr][6])
    plugin.AST_scan_1_pos_vector = cmdrstates[cmdr][7]
    plugin.AST_scan_2_pos_vector = cmdrstates[cmdr][8]

# endregion


# region UI


def clear_ui() -> None:
    """Remove all labels from this plugin."""
    global frame
    # remove all labels from the frame
    for label in frame.winfo_children():
        label.destroy()


def rebuild_ui(plugin, cmdr: str) -> None:  # noqa #CCR001
    """Rebuild the UI in case of preferences change."""
    global frame

    clear_ui()

    # recreate UI
    current_row = 0

    if plugin.updateavailable:
        latest = f"github.com/{AST_REPO}/releases/latest"
        HyperlinkLabel(frame, text="Update available!", url=latest, underline=True).grid(row=current_row, sticky=tk.W)
        current_row += 1

    uielementcheck = [plugin.AST_hide_fullscan.get(), plugin.AST_hide_species.get(), plugin.AST_hide_progress.get(),
                      plugin.AST_hide_last_system.get(), plugin.AST_hide_last_body.get(), plugin.AST_hide_value.get(),
                      plugin.AST_hide_system.get(), plugin.AST_hide_body.get()]
    uielementlistleft = ["Last Exobiology Scan:", "Last Species:", "Scan Progress:",
                         "System of last Scan:", "Body of last Scan:", "Unsold Scan Value:",
                         "Current System:", "Current Body:"]
    uielementlistright = [plugin.AST_state, plugin.AST_last_scan_plant, plugin.AST_current_scan_progress,
                          plugin.AST_last_scan_system, plugin.AST_last_scan_body, plugin.AST_value,
                          plugin.AST_current_system, plugin.AST_current_body]
    uielementlistextra = [None, None, None, None, None, "clipboardbutton", None, None]

    skipafterselling = ["Last Exobiology Scan:", "Last Species:", "Scan Progress:",
                        "System of last Scan:", "Body of last Scan:"]

    for i in range(max(len(uielementlistleft), len(uielementlistright))):
        if uielementcheck[i] != 1:
            if plugin.AST_after_selling.get() != 0:
                if uielementlistleft[i] in skipafterselling:
                    continue
            # Check when we hide the value of unsold scans when it is 0
            if uielementlistleft[i] == "Unsold Scan Value:":
                if (plugin.AST_hide_value_when_zero.get() == 1
                   and int(plugin.rawvalue) == 0):
                    continue
            # Hide when system is the same as the current one.
            if (uielementlistleft[i] in ["System of last Scan:", "Body of last Scan:"]
               and (plugin.AST_hide_after_selling.get() == 1 or plugin.AST_hide_after_full_scan.get() == 1)):
                if uielementlistright[i].get() == uielementlistright[i+3].get():
                    continue
            if i < len(uielementlistleft):
                ui_label(frame, uielementlistleft[i], current_row, 0, tk.W)
            if i < len(uielementlistright):
                ui_entry(frame, uielementlistright[i], current_row, 1, tk.W)
            if uielementlistextra[i] == "clipboardbutton":
                ui_button(frame, "📋", plugin.clipboard, current_row, 2, tk.E)
            current_row += 1

    # Clonal Colonial Range here.
    if plugin.AST_hide_CCR.get() != 1 and plugin.AST_near_planet is True:
        # show distances for the last scans.
        colour = "red"
        if plugin.AST_current_scan_progress.get() in ["0/3", "3/3"]:
            colour = None
        if plugin.AST_scan_1_dist_green:
            colour = "green"
        ui_colourlabel(frame, "Distance to Scan #1: ", current_row, 0, colour, tk.W)
        ui_colourentry(frame, plugin.AST_scan_1_pos_dist, current_row, 1, colour, tk.W)
        current_row += 1
        colour = "red"
        if plugin.AST_current_scan_progress.get() in ["0/3", "1/3", "3/3"]:
            colour = None
        if plugin.AST_scan_2_dist_green:
            colour = "green"
        ui_colourlabel(frame, "Distance to Scan #2: ", current_row, 0, colour, tk.W)
        ui_colourentry(frame, plugin.AST_scan_2_pos_dist, current_row, 1, colour, tk.W)
        current_row += 1
        colour = None
        if ((plugin.AST_scan_1_dist_green
             and plugin.AST_current_scan_progress.get() == "1/3")
            or (plugin.AST_scan_1_dist_green
                and plugin.AST_scan_2_dist_green
                and plugin.AST_current_scan_progress.get() == "2/3")):
            colour = "green"
        ui_colourlabel(frame, "Current Position: ", current_row, 0, colour, tk.W)
        ui_colourentry(frame, plugin.AST_current_pos, current_row, 1, colour, tk.W)
        current_row += 1

    # Tracked sold bio scans as the last thing to add to the UI
    if plugin.AST_hide_sold_bio.get() != 1:
        build_sold_bio_ui(plugin, cmdr, current_row)

    theme.update(frame)  # Apply theme colours to the frame and its children, including the new widgets

def build_sold_bio_ui(plugin, cmdr: str, current_row) -> None:  # noqa #CCR001
    # Create a Button to make it shorter?
    soldbiodata = {}
    notsoldbiodata = {}

    file = directory + "\\soldbiodata.json"
    with open(file, "r+", encoding="utf8") as f:
        soldbiodata = json.load(f)

    file = directory + "\\notsoldbiodata.json"
    with open(file, "r+", encoding="utf8") as f:
        notsoldbiodata = json.load(f)

    ui_label(frame, "Scans in this System:", current_row, 0, tk.W)

    if cmdr == "" or cmdr is None or cmdr == "None":
        return

    # Check if we even got a cmdr yet!
    # logger.info(f"Commander: {cmdr}. attempting to access")
    # logger.info(f"data: {soldbiodata[cmdr]}.")
    # logger.info(f"data: {notsoldbiodata}.")

    bodylistofspecies = {}
    try:
        firstletter = plugin.AST_current_system.get()[0].lower()
    except IndexError:
        ui_label(frame, "None", current_row, 1, tk.W)
        # length of string is 0. there is no current system yet.
        # So there is no reason to do anything
        return

    count = 0

    try:
        if plugin.AST_current_system.get() in soldbiodata[cmdr][firstletter].keys():
            for sold in soldbiodata[cmdr][firstletter][plugin.AST_current_system.get()]:
                bodyname = ""

                # Check if body has a special name or if we have standardized names
                if sold["system"] in sold["body"]:
                    # no special name for planet
                    bodyname = sold["body"].replace(sold["system"], "")[1:]
                else:
                    bodyname = sold["body"]

                if sold["species"] not in bodylistofspecies.keys():
                    bodylistofspecies[sold["species"]] = [[bodyname, True]]
                else:
                    bodylistofspecies[sold["species"]].append([bodyname, True])

                count += 1
    except KeyError:
        # if we don't have the cmdr in the sold data yet we just pass all sold data.
        pass

    try:
        for notsold in notsoldbiodata[cmdr]:
            if notsold["system"] == plugin.AST_current_system.get():

                bodyname = ""

                # Check if body has a special name or if we have standardized names
                if notsold["system"] in notsold["body"]:
                    # no special name for planet
                    bodyname = notsold["body"].replace(notsold["system"], "")[1:]
                else:
                    bodyname = notsold["body"]

                if notsold["species"] not in bodylistofspecies.keys():
                    bodylistofspecies[notsold["species"]] = [[bodyname, False]]
                else:
                    bodylistofspecies[notsold["species"]].append([bodyname, False])

                count += 1
    except KeyError:
        # if we don't have the cmdr in the notsold data yet we just pass.
        pass

    if bodylistofspecies == {}:
        ui_label(frame, "None", current_row, 1, tk.W)
    else:
        ui_label(frame, count, current_row, 1, tk.W)

    # skip
    if plugin.AST_hide_scans_in_system.get() != 0:
        ui_button(frame, "▼", plugin.switchhidesoldexobio, current_row, 2, tk.W)

        return

    ui_button(frame, "▲", plugin.switchhidesoldexobio, current_row, 2, tk.W)

    for species in bodylistofspecies.keys():
        current_row += 1
        ui_label(frame, species, current_row, 0, tk.W)
        bodies = ""
        for body in bodylistofspecies[species]:
            if body[1]:
                bodies = bodies + body[0] + ", "
            else:
                bodies = bodies + "*" + body[0] + "*, "
        while (bodies[-1] == "," or bodies[-1] == " "):
            bodies = bodies[:-1]

        ui_label(frame, bodies, current_row, 1, tk.W)


def shortcreditstring(number):
    """Create string given given number of credits with SI symbol prefix and money unit e.g. KCr. MCr. GCr. TCr."""
    if number is None:
        return "N/A"
    prefix = ["", "K", "M", "G", "T", "P", "E", "Z", "Y", "R", "Q"]
    fullstring = f"{number:,}"
    prefixindex = fullstring.count(",")
    if prefixindex <= 0:
        # no unit prefix just -> write a shorter number
        return fullstring + " Cr."
    if prefixindex >= len(prefix):
        # Game probably won't be able to handle it if someone sold this at once.
        return "SELL ALREADY! WE RAN OUT OF SI PREFIXES (╯°□°）╯︵ ┻━┻"
    unit = " " + prefix[prefixindex] + "Cr."
    index = fullstring.find(",") + 1
    fullstring = fullstring[:index].replace(",", ".")+fullstring[index:].replace(",", "")
    fullstring = f"{round(float(fullstring), (4-index+1)):.6f}"[:5]
    if fullstring[1] == ".":
        fullstring = fullstring[0] + "," + fullstring[2:]
        unit = " " + prefix[prefixindex-1] + "Cr."
    return fullstring + unit


def prefs_label(frame, text, row: int, col: int, sticky) -> None:
    """Create label for the preferences of the plugin."""
    nb.Label(frame, text=text).grid(row=row, column=col, sticky=sticky)


def prefs_entry(frame, textvariable, row: int, col: int, sticky) -> None:
    """Create an entry field for the preferences of the plugin."""
    nb.Label(frame, textvariable=textvariable).grid(row=row, column=col, sticky=sticky)


def prefs_button(frame, text, command, row: int, col: int, sticky) -> None:
    """Create a button for the prefereces of the plugin."""
    nb.Button(frame, text=text, command=command).grid(row=row, column=col, sticky=sticky)


def prefs_tickbutton(frame, text, variable, row: int, col: int, sticky) -> None:
    """Create a tickbox for the preferences of the plugin."""
    nb.Checkbutton(frame, text=text, variable=variable).grid(row=row, column=col, sticky=sticky)


def ui_label(frame, text, row: int, col: int, sticky) -> None:
    """Create a label for the ui of the plugin."""
    tk.Label(frame, text=text).grid(row=row, column=col, sticky=sticky)


def ui_entry(frame, textvariable, row: int, col: int, sticky) -> None:
    """Create a label that displays the content of a textvariable for the ui of the plugin."""
    tk.Label(frame, textvariable=textvariable).grid(row=row, column=col, sticky=sticky)


def ui_colourlabel(frame, text: str, row: int, col: int, colour: str, sticky) -> None:
    """Create a label with coloured text for the ui of the plugin."""
    tk.Label(frame, text=text, fg=colour).grid(row=row, column=col, sticky=sticky)


def ui_colourentry(frame, textvariable, row: int, col: int, colour: str, sticky) -> None:
    """Create a label that displays the content of a textvariable for the ui of the plugin."""
    tk.Label(frame, textvariable=textvariable, fg=colour).grid(row=row, column=col, sticky=sticky)


def ui_button(frame, text, command, row: int, col: int, sticky) -> None:
    """Create a button for the ui of the plugin."""
    tk.Button(frame, text=text, command=command).grid(row=row, column=col, sticky=sticky)

# endregion


def plugin_start3(plugin_dir: str) -> str:
    """
    Handle start up of the plugin.

    See PLUGINS.md#startup
    """
    pluginname = plugin.on_load()
    return pluginname


def plugin_stop() -> None:
    """
    Handle shutdown of the plugin.

    See PLUGINS.md#shutdown
    """
    plugin.on_unload()
    return


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
    """
    Handle preferences tab for the plugin.

    See PLUGINS.md#configuration
    """
    preferenceframe = plugin.setup_preferences(parent, cmdr, is_beta)
    return preferenceframe


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Handle any changed preferences for the plugin.

    See PLUGINS.md#configuration
    """
    rebuild_ui(plugin, cmdr)

    plugin.on_preferences_closed(cmdr, is_beta)
    return


def plugin_app(parent: tk.Frame) -> tk.Frame:
    """
    Set up the UI of the plugin.

    See PLUGINS.md#display
    """
    global frame
    frame = plugin.setup_main_ui(parent)
    return frame
