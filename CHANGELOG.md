*In compliance with the [GPL-2.0](https://opensource.org/licenses/GPL-2.0) license: I declare that this version of the program contains my modifications, which can be seen through the usual "git" mechanism.*  


2022-08  
Contributor(s):  
notapirate  
>caja, nautilus, nemo, thunar clients: move __future__ import to the top (#357)  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2022-06  
Contributor(s):  
Daniel O'Connor  
>Adjust setup  
>Shift  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2022-04  
Contributor(s):  
Daniel O'Connor  
>Improve pylint errors - Autopep8 a number of items; format with black. (#346)
* Improve pylint errors - unused-imports

    clients/thunar/RabbitVCS.py:32:0: W0611: Unused import datetime (unused-import)
    clients/thunar/RabbitVCS.py:33:0: W0611: Unused import time (unused-import)
    clients/thunar/RabbitVCS.py:46:0: W0611: Unused import os (unused-import)
    clients/thunar/RabbitVCS.py:31:0: W0611: Unused isdir imported from os.path (unused-import)
    clients/thunar/RabbitVCS.py:31:0: W0611: Unused isfile imported from os.path (unused-import)
    clients/thunar/RabbitVCS.py:31:0: W0611: Unused basename imported from os.path (unused-import)
    clients/thunar/RabbitVCS.py:55:0: W0611: Unused SEPARATOR imported from rabbitvcs.util.contextmenu (unused-import)
    clients/thunar/RabbitVCS.py:54:0: W0611: Unused disable imported from rabbitvcs.util.decorators (unused-import)
    clients/thunar/RabbitVCS.py:41:0: W0611: Unused Gtk imported from gi.repository (unused-import)

* Autopep8

* Reformat with black  
>Merge pull request #328 from JorisHansMeijer/masterPrevent double scanning all version controlled items in a directory (speed up nautilus)  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2021-04  
Contributor(s):  
JorisHansMeijer  
Daniel O'Connor  
>Merge pull request #288 from ugurbor/masterSwitch After Branching Feature  
>Merge pull request #332 from rabbitvcs/fix-320Fix filtering  
>Fix arguments  
>Merge pull request #330 from JorisHansMeijer/masterFix keyboard button up/down handling  
>Merge pull request #327 from JorisHansMeijer/masterFix log window text color for os dark mode  
>Fix keyboard button up/down handlingWhen the keyboard button up/down was used to navigate the revisions table. The paths table was not updated.  
>Prevent double scanning all version controlled items in a directory  
>Formatting  
>As dark mode, fix text colorThe text color of the log windows was always black. However when selecting dark mode in the os the window is also black. This means the text is no longer readable. This fix makes the text the correct color for dark mode and normal mode.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2020-06  
Contributor(s):  
Gabriel  
Patrick Monnerat  
adamplumb  
>cli client: fix typo.  
>changes: do not dereference event object if None..  
>Merge pull request #302 from gabrielfin/fix-svn-conflict-editCompare revision numbers as ints not strings  
>Compare revision numbers as ints not strings  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2020-05  
Contributor(s):  
Gabriel  
Patrick Monnerat  
adamplumb  
>editconflicts: do not wait on Gtk.Edit conflicts class does not queue Gtk events intended to be handled bythe caller, thus Gtk.main() must not be invoked.Reported-By: gabrielfin on githubFixes: #300  
>Merge pull request #301 from gabrielfin/fix-revision-selectionFix revision selection not working in log dialog  
>Fix revision selection not working in log dialog  
>Fix crashes due to uninitialized locale.Reported-By: metal450 on githubIssue: https://github.com/rabbitvcs/rabbitvcs/issues/295  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2020-04  
Contributor(s):  
Patrick Monnerat  
>svn.get_repo_url: always return a string.Fixes #292Reported-By: ugurbor on github  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2020-03  
Contributor(s):  
ugurbor  
>wrong usage of variable  
>work as the setting suggests  
>switch after branch feature  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2020-02  
Contributor(s):  
Adam Plumb  
>Release v0.18  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-12  
Contributor(s):  
Patrick Monnerat  
>Context menu: do not display empty menus.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-09  
Contributor(s):  
Patrick Monnerat  
>caja, nautilus, nemo, thunar clients: unify get_local_path() method.  
>caja, nautilus, nemo, thunar clients: rename *VFSFile_table to VFSFile_tableThis allows accessing it from debug in a client-agnostic way.  
>Remove leftover conditional GTK2 code.GTK2 is not supported anymore.  
>nautilus, caja, nemo clients: get file paths from GIO.GFileThis is straighter than (trying to) unescape the url path part and suppressescalls to unquote_url().  
>vcs/status: avoid implicit string conversions in json.This is accomplished by converting strings to/from unicode in__getstate__ and __setstate__.Without this fix, non-ascii filenames are badly processed by Python 2.  
>Commit: Use Gtk object value instead of local toggle.Using the "show unversioned files" Gtk CheckButton object value allowsto get rid of the "isInitDone" hack.Also fix a unicode/str problem.  
>Contextual menus: show menu item tooltips... and fix a misnamed Gtk function call.  
>Annotate: enrich user interface- The "from" revision has been suppressed: much confusing and  unsupported by git.- Displayed revisions are now handled via a history stack (in the  same way as a web browser do): the "Refresh" button has been  replaced by history navigation icons. Long clicks (> 1 second) on  "previous" and "next" icons show an history popup menu.- Double-clicking a row pushes the target revision on the history stack.- A contextual menu allows several view/diff/compare operations to be  performed on file's revisions.  
>Explicit event parameter in button/key event callbacks... and check for button press/release now that both event types arepropagated.  
>Annotate: move table building to generic class  
>Debug: define 'extension' in python console.Also fix string type in "Add Emblem"  
>Debug: replace the IPython interactive shell by a Gtk-based Python consoleIPython is very unstable across versions and recent API changes are poorlydocumented.In addition, implementing a Gtk Python console is even simpler thaninterfacing IPython.  
>Remove 2 unused version comparision functions.  
>Define all classes as new style  
>settings: add options to control syntax highlighting and colorization  
>annotate: colorize row background according to author and revision.This allows identifying more easily lines common to a single commit andto the same author.Background colors are randomly generated in the HSL color space to easeluminance control (we generate light colors only), then converted to RGBfor gtk.This commit also gets the file log in the loading action rather than in theclass initialization.  
>git log: use committer for author only if the latter is unknown  
>Annotate: add a tooltip with the line's short commit message  
>Widget Table: keep selection while handling multiline toggle clickSave selected row indexes as TreePaths to support Tree class.Table class get_selected_rows method still returns them as a list of integers.Fix some handling of mouse events.  
>Widget Table/Tree: fix append() and populate() for Tree support.  
>Annotate: highlight syntax using pygments libraryGtkSourceView does not fit well our needs since it handles a multilinetext view, not a table view. The pygments library supports custom formatters,thus allowing to format source as Pango markup language independent lines.This commit gets rid of (unused) existing provision of GtkSourceView andimplements syntax highlighting in the annotate module if pygments library isavailable.  
>subversion annotate: properly handle lines without blame information.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-08  
Contributor(s):  
Patrick Monnerat  
>Dialogs: use locale collating sequence for string sorting.Reported-By: tylla on githubFixes #202  
>subversion log: fix "Edit Author" and "Edit Message" commit commands.- Simplify dialog.- Do not change display if the command fails.- Do not preset author dialog with "(no author)".- Fix an encoding bug.  
>Implement configurable date/time format.  
>Fix internationalisation problems in log and browse.  
>subversion: ensure i18n strings are properly handled.  
>format_long_text: fix unicode encoding of non-ascii characters.  
>Rename odd entities.  
>New hidden object field type in Gtk tables to hold the original string.As strings with invalid characters are altered for display, a hidden fieldis needed to hold the original value if the target string is used as a "key"(i.e.: a value that is retrieved and used upon user action). Such a fieldcannot be a string: this would cause Gtk to crash on conversion.For this purpose, a new table field type is introduced to keep hidden objects.S objects can be used to set such fields.Modules that display "key" strings in Gtk tables now feature hiddenobject fields to hold the real "key" value.  
>Recognize S objects as strings in type tests.  
>Avoid a Gdk crash when sys.argv contains strings with surrogates.In Python 3, Gdk.init_check() encodes sys.argv without handling surrogates,causing an UnicodeEncodeError exception while importing Gtk.The new class SanizeArgv implements a mechanism to avoid that:- The first Gdk/Gtk import performed by a program should be preceded by  a SanitizeArgv object creation.- After Gdk/Gtk import, call this object's method restore().This has to be done in all modules that may perform the initial Gdk/Gtk import,and the algorithm is not 100% reliable in the sense that 2 differentconsecutive strings with surrogates may map to the same display representation.In any case, this is just a Gdk bug workaround.  
>Use our own encoding/error handler in quote_url() and unquote_url().  
>Use our own utf-8 codec with surrogates to create StreamReaders.  
>Use the S class for the to_bytes() function.  
>Send strings to dbus as arrays of bytes.DBus does not like invalid characters in strings while the exact representationof file names should be transmitted. The solution used here is to send theutf-8 encoding of each string as a byte array.  
>Fix subversion annotate.- Start line numbers at 1.- Properly run from browser contextual menu.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-07  
Contributor(s):  
Patrick Monnerat  
>Encoding: new str subclass S to support Python 2/3 compatibility.New module rabbitvcs.util.strings introduces a new utf-8 encoding andsurrogateescape error handler that work also in Python < 3.1.Str subclass S supports built-in Python string representation (eitherunicode or utf-8 bytes) with the encode() and decode() method overloadedto use our new encoding and error handler by default. Additional methodsbytes(), unicode() and display() are featured. The display() method shouldbe used to map surrogates that are not displayable.The rabbitvcs.util.helper.to_text() function is then obsolete and has beensuppressed.Because pysvn causes errors when passing str subclass arguments (due to a PyXXbug), S objects are converted back to pure str class before being passedto this module.  
>New feature: default commit message.The settings dialog now supports editing a default commit message that isused to preset the commit dialog.This feature implements what has been discussed in #237.  
>Fix error notification dialog initialization  
>Add missing icons to log contextual menu entries.Drop redundant log menu item definition.  
>Fix clipboard handling in browser and log.  
>SVN browser: add a "create folder here" button.This allows doing it even when there's no empty space in the item view fora right click contextual menu to target the currently listed directory.Fixes #68  
>Revert commit fb1646eNow that the log message pop-up dialog is fixed, it is safe to commit with anempty log message.  
>Fix log message, SSL and authentication related dialogs.  
>New folder dialog: initially disable OK button  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-06  
Contributor(s):  
Patrick Monnerat  
adamplumb  
>SVN browser: hide problematic contextual menu entries on parent directory.  
>Merge pull request #268 from monnerat/fixesSome fixes  
>Commit: disable OK button if log message is emptyPySVN refuses to commit with an empty log message: force the user to enter one.  
>Fix handling of toggles in Table and Tree widgets.  
>Be more tolerant about non-UTF8 characters.While using StreamReader's, map invalid bytes to their backslash-escapedrepresentation.Fixes #132  
>format_datetime: internationalize datetime format strings.This allows specifying alternate date/time formats as gettext strings.This fix is inspired from #156, although not implementing configurabledate/time formats.  
>Show changes between revisions: properly use last selected as 2nd revision.Fixes #228  
>git push: implement "force with lease"Fixes #236  
>Git commit: use local timezone.Fixes #255  
>Change version number (at last) to 0.17.1Fixes #246  
>Git commit: always show separate versioned and unversioned item counts.Fixes #248  
>Nautilus client: fix computation of base directory.  
>Avoid returning a "None" status if not found in status map.  
>Accept that GtkSpell and GtkSource gi typelibs are not presentFixes #263  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-04  
Contributor(s):  
Patrick Monnerat  
adamplumb  
>Merge pull request #262 from rabbitvcs/gtk3Gtk3  
>Merge pull request #261 from monnerat/pm-gtk3A whole bunch of work on the gtk3 branch.  
>Fix property page in Nemo client.  
>Rename clients/nautilus-3 into clients/nautilus  
>Rename thunar-gtk3 to thunar.  
>Expand revision entry horizontally in "Show Changes" window.  
>Make Thunar gtk3 client working.Remove Thunar gtk2 client.  
>Log: only show first message line in revisions table.Since the whole message is shown in its own scrollable widget upon selection,it is clearer to show only the first line of a multi-line message in therevisions table.  
>Add a vertical scroll to git tag message display.This eases supporting very long commit messages.  
>Localize spell checker.  
>Work on internationalization.The language configuration parameter is suppressed: instead, dynamic languagechange is supported and a SetLocale checker service is implemented.Clients set the checker service locale upon connection. The cli clientis internationalized too.The checker service locale is displayed in the pertaining settings page.Stop checker function from settings has been reworked to avoid exceptions.  
>Use Gtk.Grid wherever possible.Gtk 3 has deprecated Gtk.HBox, Gtk.VBox, Gtk.Alignment, Gtk.Table andrecommends using Gtk.Grid instead of Gtk.Box, as the later is in the pipelinefor soon deprecation too.As a consequence, Gtk.Grid is the only generic container available now.This commit replaces uses of the above deprecated widgets by Gtk.Grid's. Theonly place Gtk.Box is retained is for Gtk.Dialogs' top child, as glade does notallow to replace these internal widgets.  
>Status cache: preserve the status class.This allows using class variables of an item retrieved from the cache.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2019-03  
Contributor(s):  
Adam Plumb  
Patrick Monnerat  
adamplumb  
>Fix browser dialog in SVN branch/tag.  
>Fix git tags manager for Python 3  
>Replace deprecated Gtk.VBox and Gtk.HBox by Gtk.Box.  
>Git update: put merge and rebase radio buttons in same group.  
>Janitorial: strip trailing spacing and map tabs in Python files.  
>Fix automatic destination setting in git clone.  
>Move to using regular json  
>Merge pull request #257 from monnerat/pm-gtk3Gtk3/Python3 contributions  
>Fix git annotate.  
>Do not use deprecated Gtk.Action in menu items.  
>Gtk3 ComboBox has no get_active_text() method  
>Remove unneeded constructors  
>Remove more deprecations, rework glade files, fix Caja client problems.New icons cancel, ok, yes, no, editprops.No more deprecated Gtk.Aligment widgets: replaced by Gtk.Box'es.No more deprecated Gtk stock items: replaced by strings and icon names.Replace deprecated positional parameters by keyword parameters.Use Gtk3 namespaced constants.Reenable multithreading.Improve Python 2/3 compatibility: strings/bytes, sort, urllib, Popen encoding.Some more gyttyup/dulwich string/bytes conversions.Add missing config spec for merge_tool.  
>Execute non threadsafe sequences in main thread.Do not call Gdk.treads_enter()/Gtk.threads_leave() anymore.  
>vcs status: initialize TestStatusObjects class variables.  
>Use a custom helper function for conversions to text type.  
>Get rid of GObject deprecated features.Some of them are conditioned to GObject version, some others are moved toGLib.Also be sure to properly flush service start message.  
>About dialog: gtk 3 compatibility + show icon and license.  
>Gdk3: use new definitions for keyval.  
>Context menu: filter-out "Rename" on working copies.As they are not member of themselves, they should be renamed as unversionedfiles.  
>Access Gdk module directly (Gtk.gdk does not exist in Gtk3)  
>log/show_changes_previous_revision: define rev_last  
>cgi.escape() deprecation  
>Widget: fix ComboBox text entry access  
>helper: Python 3 compatibility  
>widget: adjust child access in ComboBox  
>diff: use idle_add() from GLib  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2018-10  
Contributor(s):  
Adam Plumb  
Dimitris  
adamplumb  
>Merge in master  
>Fix issues related to log and changes  
>Merge pull request #245 from karate/masterFix 'Show changes against previous revision' in log window #244  
>Fix env var  
>Merge in origin master  
>Fix 'Show changes against previous revision' in log window #244  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2018-06  
Contributor(s):  
Adam Plumb  
>Some more work on diff and checkout  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2018-05  
Contributor(s):  
Adam Plumb  
Philip Raets  
adamplumb  
>Fix graph renderer issue  
>Fix combobox to work better, though still not perfect  
>Get update widget and manager working somewhat  
>Merge in philipraets branch  
>Merge pull request #232 from philipraets/gtk3Gtk3  
>Some further gtk work  
>gtk3 changes  
>Update branch.py  
>Update applypatch.py  
>Update helper.py  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2018-03  
Contributor(s):  
Adam Plumb  
Eli Schwartz  
adamplumb  
>Get Add window working  
>Some initial work on python3/gtk3 UI windows.  Make windows single threaded for now to prevent crashes  
>Merge pull request #227 from eli-schwartz/nemo-updatesMerge updates from nemo-extensions  
>Import extension from linuxmint/nemo-extensions.Originally committed by Will Rouesnel <w.rouesnel@gmail.com>  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2018-02  
Contributor(s):  
Adam Plumb  
>Some more work towards python3/gtk3.  Got the add action mostly working  
>Start converting xml files to gtk3  
>Add new thunar-gtk3 client.  This required some minor refactoring for existing clients  
>Speed up VCS guessing  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-11  
Contributor(s):  
Kory Becker  
adamplumb  
>Merge pull request #218 from primaryobjects/clone-clipboardSet clone dialog Url to value in clipboard.  
>Null check on clipboard text.  
>Removed unused ref.  
>Changed to gtk clipboard.  
>Refactored to use gtk instead of tkinter.  
>Set clone dialog url textbox to value in clipboard.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-09  
Contributor(s):  
Leigh Scott  
>fix indent (linuxmint/nemo-extensions#231)  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-07  
Contributor(s):  
Adam Plumb  
>Update subversion to only save status objects for files and directories in the current view  
>Do not require recursive statuses for git.  Should help with memory and cpu usage.  
>Get urlparse/urlunparse working better for python2 and 3 compatibility  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-06  
Contributor(s):  
Adam Plumb  
adamplumb  
leigh123linux  
>Rabbitvcs: Specify nemo import version (linuxmint/nemo-extensions#227)  
>Bump version to v0.17  
>Fix my bafoonish error  
>Issue #25, Fix some issues that are blockers for python2.4  
>Stops log from crashing for some folks  
>Python3 api change  
>Issue 176, Fixed unexpected keyword argument 'depth' on add_backwards call from apply_patch  
>Issue #193, Fix SIGABRT with threads_init call  
>Remove debug line  
>Only import from gi if needed  
>Add UI components to the settings dialog to enable/disable svn and git.  Also, disable mercurial entirely for now.  It's just creating clutter with no realy benefit.  
>Some minor fixes to get initial git repos resulting in fewer errors  
>Fix urlparse usage for python2  
>Merge pull request #191 from gilder0/fixIssue167#167 - GIT: Add showing branch name in commit dialog  
>Fix contextmenuitems import  
>Merge pull request #190 from gilder0/fixAutoStartServicefix auto-start service when checkerservice was killed  
>Merge pull request #189 from gilder0/fixIssue173Fix issue173  
>Merge pull request #187 from gilder0/fixPushGIT - fix showing Push dialog  
>Refactor fetch to use git cmdline too. Fixes issues with fetching and the update dialog.  
>Fix issues with remotes dialog.  Can now add/edit/remove remotes.  
>Merge pull request #186 from gilder0/fullMergeLogGIT - Full merge log  
>Merge pull request #151 from virtualthoughts/masterBetter conflict resolving  
>Fix push config call to include new dulwich config stack usage  
>Improve the opening mechanism so there are multiple options  
>Let the caller force the export as needed  
>Force the export to happen so it won't fail it run multiple times  
>Fix context menu loading  
>Merge pull request #175 from nokroeger/masterFix svn export: respect the provided Revision parameter rather than o…  
>Merge pull request #150 from Mondane/patch-1Add support for Ubuntu sidebar window grouping.  
>Merge pull request #135 from rapgro/python3-urlparsePython 3: modifications of modernize tool, some minor manual fixes to keep python2 compatibility  
>Merge pull request #133 from rapgro/log-guessprevent some crashes in rabbitvcs log command  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-04  
Contributor(s):  
Arkadiusz Kleszcz  
>#167 - GIT: Add showing branch name in commit dialog  
>fix auto-start service when checkerservice was killed  
>correct import order to fix : https://github.com/rabbitvcs/rabbitvcs/issues/17  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2017-03  
Contributor(s):  
Arkadiusz Kleszcz  
>GIT - push dialog - Better presenting changes to push  
>GIT - fix showing Push dialog  
>GIT : Show proper mergeInfo on Log dialog  
>GIT: shorter names of remote branches in log window  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-12  
Contributor(s):  
Nils Oliver Kröger  
>Fix svn export: respect the provided Revision parameter rather than overwriting it.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-11  
Contributor(s):  
leigh123linux  
>nemo-rabbitvcs: remove _ from get_name_and_desc  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-09  
Contributor(s):  
leigh123linux  
>add more  
>Add support for nemo's plugin manager  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-04  
Contributor(s):  
Mondane  
>Add support for Ubuntu sidebar window grouping.A solution for https://github.com/rabbitvcs/rabbitvcs/issues/149 . Now, you can create this desktop file on Ubuntu:

```
[Desktop Entry]
Encoding=UTF-8
Name=RabbitVCS
Exec=rabbitvcs browser
Icon=rabbitvcs
Categories=Application;Development;
Type=Application
StartupNotify=true
StartupWMClass=RabbitVCS
Terminal=0
```

and have all RabbitVCS windows grouped below it.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-02  
Contributor(s):  
Raphael Groner  
>prevent some crashes in rabbitvcs log command, see https://bugzilla.redhat.com/show_bug.cgi?id=1141530  
>modifications of modernize tool, some minor manual fixes to keep python2 compatibility  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2016-01  
Contributor(s):  
Daniel O'Connor  
>Merge pull request #125 from Fordi/masterImplemented multi-check  
>Merge pull request #124 from MasterAler/masterminor fix: commits without date specified are shown correctly  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2015-11  
Contributor(s):  
MasterAler  
Bryan Elliott  
>Added ability for multiple checkboxes to get set when a checkbox is toggled while multiple rows are selected.  Implementation: all selected checkboxes recieve `not {checkbox's initial state}`  
>minor fix: commits without date specified are shown correctly, not causing error  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2015-09  
Contributor(s):  
babybear  
>Added better edit-conflict support  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2015-03  
Contributor(s):  
abaheti  
Daniel O'Connor  
>Merge pull request #89 from abaheti/masterFixing https://github.com/rabbitvcs/rabbitvcs/issues/70  
>Merge pull request #84 from Draccoz/masterNew feature: hide context menu items  
>Fixing https://github.com/rabbitvcs/rabbitvcs/issues/70This is an issue with the export where on selecting the partition, it deletes all the files on that partition. Even after deleting all the files, the export fails to get the file.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2015-02  
Contributor(s):  
Dracco  
>New feature: hide context menu items  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-11  
Contributor(s):  
Kory Becker  
Daniel O'Connor  
>Merge pull request #71 from primaryobjects/show_unversionedFixed "Show unversioned files" checkbox to operate correctly on commit dialog.  
>Fixed "Show unversioned files" checkbox to operate correctly on the commit dialog.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-10  
Contributor(s):  
fuesika  
Daniel O'Connor  
>Merge pull request #61 from fuesika/masterbugfix for issue #59: update threading for use with latest glib (2.42), fix for issue #60: update of README  
>bugfix for issue #59, update threading for use with latest glib (2.42)  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-09  
Contributor(s):  
Kory Becker  
Daniel O'Connor  
>Merge pull request #56 from primaryobjects/log_branch_tagAdded branch and tag identifiers to log history  
>Display branch and tag names in log history.  
>Merge pull request #54 from primaryobjects/push_tagsAdded push tags option.  
>Added push tags option.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-08  
Contributor(s):  
Kory Becker  
Daniel O'Connor  
>Merge pull request #46 from primaryobjects/masterUsername/Password Prompt for Clone, Push, Pull  
>Updated version to 0.16.1, includes password prompt.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-05  
Contributor(s):  
Michael Webster  
>all: don't let python extensions prevent terminating nemo with ctrl-c  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2014-04  
Contributor(s):  
Daniel O'Connor  
>#14 - Avoid errors, and hide ignored by default from staging.  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 


2013-11  
Contributor(s):  
Will Rouesnel  
>Check for base_dir attr when opening menu in RabbitVCSThis is the cause of a lot of spurious Python exceptions when runningRabbitVCS. They are harmless, but should be checked since they fill up.xsession-errors  
- - - - - - - - - - - - - - - - - - - - - - - - - - - 

