RabbitVCS
=========

RabbitVCS is a set of graphical tools written to provide simple and 
straightforward access to the version control systems you use.

RabbitVCS is now distributed in two parts.  The first part is the python module
that is not connected to any file manager or text editor.  This is what is now 
known as "rabbitvcs".  The second part is the series of front-ends or clients
that we distribute.  These consist of a Nautilus extension, a Thunar extension,
a Gedit plugin, and a command line utility.  All of these clients use the same
python module as a back-end.


System Requirements
-------------------
* pygtk             >= 2.12
* python-configobj  >= 4.4.0
* python-gobject    >= 2.14
* python-simplejson >= 2.1.1

For spell checking of commit messages:
* python-gtkspell

For subversion:
* python-svn >= 1.7.2
* subversion >= 1.4.6

For git:
* dulwich >= 0.9.7
* git

Recommends:
* meld (graphical diff tool)


For debian based distros you can run: 
```
# apt-get install python-gtk2 python-configobj python-gobject  python-simplejson  python-gtkspell  python-svn  subversion python-dulwich git meld
```

Installation
------------
Note that you will require superuser rights in order to install RabbitVCS.
Execute the following as root or using sudo:
```
# python setup.py install
```

On Ubuntu or Debian-based distros, instead run:
```
# python setup.py install --install-layout=deb
```

Each clients' README file contains details on their dependencies and installation.

Manual Upgrade
--------------
To upgrade an existing version manually, copy the contents of the repository to the rabbitvcs lib folder.
Most likely it is located at `/usr/lib/pymodules/python2.7/rabbitvcs`. In case of Debian-based distros this is will be `/usr/lib/python2.7/dist-packages/rabbitvcs`.

References
----------
Homepage: http://rabbitvcs.org
