#
# This is an extension to the Nautilus file manager to allow better 
# integration with the Subversion source control system.
# 
# Copyright (C) 2006-2008 by Jason Field <jason@jasonfield.com>
# Copyright (C) 2007-2008 by Bruce van der Kooij <brucevdkooij@gmail.com>
# Copyright (C) 2008-2010 by Adam Plumb <adamplumb@gmail.com>
# 
# RabbitVCS is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# RabbitVCS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with RabbitVCS;  If not, see <http://www.gnu.org/licenses/>.
#

import os

import pygtk
import gobject
import gtk
import pango

from datetime import datetime
import time

from rabbitvcs.ui import InterfaceView
from rabbitvcs.ui.action import GitAction
import rabbitvcs.ui.widget
from rabbitvcs.ui.dialog import DeleteConfirmation
import rabbitvcs.util.helper
import rabbitvcs.vcs

from Tkinter import *
import ttk
import tkMessageBox

from rabbitvcs import gettext
_ = gettext.gettext

class GitRemotes(InterfaceView):
    """
    Provides a UI interface to manage items
    """
    
    def __init__(self, path):
        self.vcs = rabbitvcs.vcs.VCS()
        self.git = self.vcs.git(path)

        # Create main window.
        window = Tk()
        window.title("Remote Repository Manager")
        window.resizable(0,0)
        window["padx"] = 0
        window["pady"] = 0
        window.bind("<Escape>", (lambda event: window.destroy()))
        self.window = window

        # Create treeview.
        self.treeView = ttk.Treeview(window, show="headings", columns=("Name", "Host"))
        self.treeView.column("Name", width=200)
        self.treeView.column("Host", width=500)
        self.treeView.heading("Name", text="Name")
        self.treeView.heading("Host", text="Host")
        self.treeView.bind("<Delete>", (lambda event: self.onRemove()))
        self.treeView.bind("<Return>", (lambda event: self.onEdit()))
        self.treeView.bind("<Escape>", (lambda event: window.destroy()))
        self.treeView.bind("<KP_Enter>", self.OnDoubleClick)
        self.treeView.bind("<Double-1>", self.OnDoubleClick)
        
        # Setup grid.
        self.treeView.grid(row=0, column=0, columnspan=80)
        
        # Create Add button.
        button = Button(window, width=5, text="Add", command = (lambda: self.onAdd()))
        button.grid(row=1, column=0)

        # Create Edit button.
        button = Button(window, width=5, text="Edit", command = (lambda: self.onEdit()))
        button.grid(row=1, column=1)

        # Create Remove button.
        button = Button(window, width=5, text="Remove", command = (lambda: self.onRemove()))
        button.grid(row=1, column=2)

        # Create Close button.
        button = Button(window, width=5, text="Close", command = (lambda: window.destroy()))
        button.grid(row=1, column=79)

        # Load remotes from Git.
        self.load()

        # Position window in center of screen.
        self.center(window)

        # Display window.
        window.mainloop()

    def onAdd(self):
        # Display add dialog.
        self.dialog()

    def onEdit(self):
        # Get the selected value.
        name, host = self.getSelectedValues()

        if name and host:
            # Display edit dialog.
            self.dialog(name, host)
        else:
            tkMessageBox.showinfo("Error", "Please select a Git remote to edit.", parent=self.window)

    def onRemove(self):
        # Get the selected value.
        name, host = self.getSelectedValues()

        # Show a confirm prompt to delete the Git remote.
        if name:
            if tkMessageBox.askyesno("Delete Remote", "Are you sure you want to delete \"" + name + "\"?"):
                # Delete the Git remote.
                self.git.remote_delete(name)

                # Reload items in treeview.
                self.load()
        else:
            tkMessageBox.showinfo("Error", "Please select a Git remote to remove.", parent=self.window)

    def onSave(self, window, name, host, originalName = None):
        if name and host:
            # Close dialog window.
            window.destroy()

            if originalName:
                # Edit existing remote.
                self.git.remote_set_url(originalName, host)
                self.git.remote_rename(originalName, name)
            else:
                # Save new remote.
                self.git.remote_add(name, host)

            # Reload items in treeview.
            self.load()

            # Find the newly added/edited row and select it.
            for i in self.treeView.get_children():
                item = self.treeView.item(i)
                if str(item["values"][0]) == name:
                    self.treeView.selection_set(i)
                    break
        else:
            tkMessageBox.showinfo("Error", "Please enter a Git remote name and host url.", parent=window)

    def OnDoubleClick(self, event):
        self.onEdit()

    def dialog(self, name = None, host = None):
        label = "Add"
        if name:
            label = "Edit"

        # Create add dialog.
        dialog = Tk()

        # Setup add dialog.
        dialog.title(label + " Git Remote")
        dialog.resizable(0,0)
        dialog["padx"] = 40
        dialog["pady"] = 15

        # Create Name label.
        entryLabel = Label(dialog)
        entryLabel["text"] = "Name:"
        entryLabel.grid(row=0, column=0)

        # Create Name textbox.
        txtName = Entry(dialog)
        txtName["width"] = 50
        txtName.bind("<Return>", (lambda event: self.onSave(dialog, txtName.get(), txtHost.get(), name)))
        txtName.bind("<KP_Enter>", (lambda event: self.onSave(dialog, txtName.get(), txtHost.get(), name)))
        txtName.bind("<Escape>", (lambda event: dialog.destroy()))
        txtName.grid(row=0, column=1, columnspan=60)
        txtName.focus()

        # Create Host label.
        entryLabel2 = Label(dialog)
        entryLabel2["text"] = "Host:"
        entryLabel2.grid(row=1, column=0)

        # Create Host textbox.
        txtHost = Entry(dialog)
        txtHost["width"] = 50
        txtHost.bind("<Return>", (lambda event: self.onSave(dialog, txtName.get(), txtHost.get(), name)))
        txtHost.bind("<KP_Enter>", (lambda event: self.onSave(dialog, txtName.get(), txtHost.get(), name)))
        txtHost.bind("<Escape>", (lambda event: dialog.destroy()))
        txtHost.grid(row=1, column=1, columnspan=60)

        # Create OK button.
        button = Button(dialog, width=5, text="OK", command = (lambda: self.onSave(dialog, txtName.get(), txtHost.get(), name)))
        button.grid(row=2, column=60)

        # Create Cancel button.
        button = Button(dialog, width=5, text="Cancel", command = (lambda: dialog.destroy()))
        button.grid(row=2, column=59)

        # Set default value, if editing.
        if name:
            txtName.insert(0, name)
            txtHost.insert(0, host)

        # Position window in center of screen.
        self.center(dialog)

        # Show dialog.
        dialog.mainloop()

    def load(self):
        # Clear items from treeview.
        for i in self.treeView.get_children():
            self.treeView.delete(i)

        # Get list of git remote hosts.
        self.remote_list = self.git.remote_list()

        # Insert each remote into the treeview.
        for remote in self.remote_list:
            self.treeView.insert("", 0, values=(remote["name"], remote["host"]))

        # Select the first item.
        for i in self.treeView.get_children():
            self.treeView.selection_set(i)
            self.treeView.focus_set()
            self.treeView.focus(i)
            break

    def getSelected(self):
        # Set default return value.
        selectedItem = None

        # Get current selection.
        selection = self.treeView.selection()

        if selection:
            # Get id of selected row in treeview.
            selectedId = selection[0]

            # Get selected item.
            selectedItem = self.treeView.item(selectedId)

        return selectedItem

    def getSelectedValues(self):
        # Get selected item.
        selectedItem = self.getSelected()

        if selectedItem:
            return str(selectedItem["values"][0]), str(selectedItem["values"][1])
        else:
            return None, None

    def center(self, window):
        # Apparently a common hack to get the window size. Temporarily hide the
        # window to avoid update_idletasks() drawing the window in the wrong
        # position.
        window.withdraw()
        window.update_idletasks()  # Update "requested size" from geometry manager

        x = (window.winfo_screenwidth() - window.winfo_reqwidth()) / 2
        y = (window.winfo_screenheight() - window.winfo_reqheight()) / 2
        window.geometry("+%d+%d" % (x, y))

        # This seems to draw the window frame immediately, so only call deiconify()
        # after setting correct window position
        window.deiconify()

if __name__ == "__main__":
    from rabbitvcs.ui import main
    (options, paths) = main(usage="Usage: rabbitvcs branch-manager path")
    
    window = GitRemotes(paths[0])
