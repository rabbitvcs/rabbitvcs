RabbitVCS
=========

RabbitVCS is a set of graphical tools written to provide simple and 
straightforward access to the version control systems you use.  We currently support
Subversion and Git on a variety of clients such as Nautilus, Thunar, Nemo, Caja, and on the command line.


System Requirements
-------------------
* pygtk             >= 2.12
* python-configobj  >= 4.4.0
* python-gobject    >= 2.14
* python-simplejson >= 2.1.1

For spell checking of commit messages:
* python-gtkspell (newer versions of ubuntu, this is called python-gtkspellcheck)

For subversion:
* python-svn >= 1.7.2
* subversion >= 1.4.6

For git:
* dulwich >= 0.9.7
* git
* tkinter (for now, newer versions of ubuntu this is called python-tk)

Recommends:
* meld (graphical diff tool)


For Debian-based distros you can run: 
```
# apt-get install python-gtk2 python-configobj python-gobject python-simplejson python-gtkspellcheck python-svn subversion python-dulwich git meld python-tk
```

For Fedora-based distros you can run:
```
# dnf install nautilus-python pysvn python-configobj python-devel dbus-python python-dulwich tkinter subversion meld
```

Manual Installation
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

Once this is run, make sure you install one or more client below.


Clients
-------
RabbitVCS is the core library and set of dialogs, but you interact with them through our clients.  Each client needs to be purposefully installed and has its own README.  Here is a list of our currently working clients:

 * [Nautilus 3](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/nautilus-3.0)
 * [Thunar](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/thunar)
 * [Nemo](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/nemo)
 * [Caja](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/caja)
 * [Command Line](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients/cli)

We have some others as well that are either incomplete, experimental, or non-working.  [Check them out!](https://github.com/rabbitvcs/rabbitvcs/tree/master/clients)


Upgrade
--------------
To upgrade an existing version manually, copy the contents of the repository to the rabbitvcs lib folder.
Most likely it is located at `/usr/lib/pymodules/python2.7/rabbitvcs`. In case of Debian-based distros this is will be `/usr/lib/python2.7/dist-packages/rabbitvcs`.  For Fedora-based distros on 64-bit make sure to check `/usr/lib64`.


References
----------
Homepage: http://www.rabbitvcs.org
