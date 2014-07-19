#
# config.py
#

import os
import warnings

from dulwich.config import ConfigFile

def get_local_config_path(repository_path):
    return repository_path + "/.git/config"

def get_global_config_path():
    return os.path.expanduser("~/.gitconfig")

def get_system_config_path():
    return "/etc/gitconfig"

class GittyupConfig:
    def __init__(self, path):
        """
        Provides direct access to any arbitrary git config file

        @type   path    string
        @param  path    The git config file path

        """
        self.path = path
        if os.path.exists(path):
            self._config = ConfigFile.from_path(path)
        else:
            self._config = ConfigFile()

    def set(self, section, key, value):
        if section not in self._config:
            self._config[section] = {}

        self._config[section][key] = value

    def get(self, section, key):
        try:
            return self._config.get((section,), key)
        except KeyError:
            return u""

    def has(self, section, key=None):
        if key is None:
            return (section in self._config.itersections())
        else:
            try:
                self._config.get(section, key)
            except KeyError:
                return False
            else:
                return True

    def rename(self, section, old_key, new_key):
        self._config[section][new_key] = self._config[section][old_key]
        del self._config[section][old_key]

    def get_all(self):
        return self._config.items()
    
    def set_section(self, section, items):
        self._config[section] = items

    def get_section(self, section):
        return self._config[section]
    
    def rename_section(self, old_section, new_section):
        self._config[new_section] = self._config[old_section]
        del self._config[old_section]
    
    def remove_section(self, section):
        del self._config[section]

    def get_inline_comment(self, section, key):
        if key is not None:
            return self._config[section].inline_comments[key]
        else:
            return self._config.inline_comments[section]
    
    def set_inline_comment(self, section, key, value):
        if section not in self._config.inline_comments:
            self._config.inline_comments[section] = {}
        
        if key is not None:
            self._config[section].inline_comments[key] = value
        else:
            self._config.inline_comments[section] = value
    
    def remove_inline_comment(self, section, key):
        if key is not None:
            del self._config[section].inline_comments[key]
        else:
            self._config.inline_comments[section]

    def get_comment(self, section, key):
        if key is not None:
            return self._config[section].comments[key]
        else:
            return self._config.comments[section]
    
    def set_comment(self, section, key, value):
        if section not in self._config.comments:
            self._config[section].comments = {}
        
        if key is not None:
            self._config[section].comments[key] = value
        else:
            self._config.comments[section] = value
    
    def remove_comment(self, section, key):
        if key is not None:
            del self._config[section].comments[key]
        else:
            del self._config.comments[section]
        
    def write(self):
        self._config.write_to_path(self.path)

class GittyupLocalConfig(GittyupConfig):
    def __init__(self, repository_path):
        """
        Provides direct access to a local repository's git config file
        
        @type   repository_path string
        @param  repository_path The root folder of a git repository
        
        """
        GittyupConfig.__init__(self, get_local_config_path(repository_path))
        
class GittyupGlobalConfig(GittyupConfig):
    def __init__(self):
        """
        Provides direct access to the global-level git config file
        
        """
        GittyupConfig.__init__(self, get_global_config_path())

class GittyupSystemConfig(GittyupConfig):
    def __init__(self):
        """
        Provides direct access to the system-level git config file
        
        """
        GittyupConfig.__init__(self, get_system_config_path())

    def write(self):
        try:
            self._config.write_to_path(self.path)
        except IOError, e:
            warnings.warn("Can't write to system git config file, %s" % str(e), UserWarning)

class GittyupFallbackConfig:
    """
    An abstract class to provide transparent support for accessing local, global,
    and system-level git config files.  Must be sub-classed.
    
    """
    def set(self, section, key, value):
        self._config(section, key).set(section, key, value)
    
    def get(self, section, key):
        return self._config(section, key).get(section, key)
    
    def has(self, section, key=None):
        return self._config(section, key).has(section, key)
    
    def rename(self, section, old_key, new_key):
        self._config(section, old_key).rename(section, old_key, new_key)
    
    def get_all(self):
        raise NotImplementedError()
    
    def set_section(self, section, items):
        self._config(section).set_section(section, items)

    def get_section(self, section):
        return self._config(section).get_section(section)
    
    def rename_section(self, old_section, new_section):
        self._config(old_section).rename_section(old_section, new_section)
    
    def remove_section(self, section):
        self._config(section).remove_section(section)

    def get_inline_comment(self, section, key):
        return self._config(section, key).get_inline_comment(section, key)
    
    def set_inline_comment(self, section, key, value):
        self._config(section, key).set_inline_comment(section, key, value)
    
    def remove_inline_comment(self, section, key):
        self._config(section, key).remove_inline_comment(section, key)

    def get_comment(self, section, key):
        return self._config(section, key).get_comment(section, key)
    
    def set_comment(self, section, key, value):
        self._config(section, key).set_comment(section, key, value)
    
    def remove_comment(self, section, key):
        self._config(section, key).remove_comment(section, key)

    def _config(self, section, key=None):
        raise NotImplementedError()

    def _write(self):
        raise NotImplementedError()

class GittyupLocalFallbackConfig(GittyupFallbackConfig):
    def __init__(self, repository_path):
        """
        Provides transparent access to the local, global, and system-level
        git config files.
        
        @type   repository_path string
        @param  repository_path The root folder of a git repository
        
        """
        self._local = GittyupLocalConfig(repository_path)
        self._global = GittyupGlobalConfig()
        self._system = GittyupSystemConfig()
        self._must_write_to_system = False

    def _config(self, section, key=None):
        if self._local.has(section, key):
            return self._local
        elif self._system.has(section, key):
            self._must_write_to_system = True
            return self._system
        elif self._global.has(section, key):
            return self._global
        else:
            return self._local

    def write(self):
        self._local.write()
        self._global.write()
        
        if self._must_write_to_system:
            # Only root can write to the system config file, so only do it
            # if we must
            self._system.write()

    def get_all(self):
        ret = self._local._config
        ret.update(self._global._config)
        ret.update(self._system._config)
        
        return ret.items()
        

class GittyupGlobalFallbackConfig(GittyupFallbackConfig):
    def __init__(self):
        """
        Provides transparent access to the global and system-level git config 
        files.  It is useful for when you want to set global or system level 
        config parameters, but don't need to access a local repository.

        """
        self._global = GittyupGlobalConfig()
        self._system = GittyupSystemConfig()
        self._must_write_to_system = False

    def _config(self, section, key=None):
        if self._global.has(section, key):
            return self._global
        elif self._system.has(section, key):
            self._must_write_to_system = True
            return self._system
        else:
            return self._global

    def write(self):
        self._global.write()

        if self._must_write_to_system:
            # Only root can write to the system config file, so only do it
            # if we must
            self._system.write()

    def get_all(self):
        ret = self._global._config
        ret.update(self._system._config)
        
        return ret.items()
