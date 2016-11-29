from __future__ import absolute_import
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

from rabbitvcs.util.log import Log

logger = Log("rabbitvcs.util.__init__")

class Function:
    """
    Provides an interface to define and call a function.
    
    Usage:
        f = Function(self.do_this, path)
        f.run()
    
    """
    
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = None
    
    def start(self):
        self.result = self.func(*self.args, **self.kwargs)
    
    def call(self):
        return self.func(*self.args, **self.kwargs)
    
    def set_args(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    
    def get_result(self):
        return self.result

class FunctionQueue:
    """
    Provides an interface to generate a queue of function calls.
    
    """
    
    def __init__(self):
        self.queue = []
        self.cancel = False
        self._exception = None
        self.position = 0
    
    def cancel_queue(self):
        self.cancel = True
    
    def append(self, func, *args, **kwargs):
        """
        Append a Function object to the FunctionQueue
        
        @type   func: def
        @param  func: A method call
        
        @type   *args: list
        @param  *args: A list of arguments
        
        @type   **kwargs: list
        @param  **kwargs: A list of keyword arguments
        
        """
        
        self.queue.append(Function(func, *args, **kwargs))
    
    def insert(self, position, func, *args, **kwargs):
        """
        Insert a Function object into the FunctionQueue
        
        @type   func: def
        @param  func: A method call
        
        @type   *args: list
        @param  *args: A list of arguments
        
        @type   **kwargs: list
        @param  **kwargs: A list of keyword arguments
        
        """
        
        self.queue.insert(position, Function(func, *args, **kwargs))
    
    def set_exception_callback(self, func):
        self._exception = Function(func)
    
    def start(self):
        """
        Runs through the queue and calls each function
        
        """
        
        for func in self.queue:
            if self.cancel == True:
                return
            
            try:
                func.start()
            except Exception as e:
                logger.exception()
                if self._exception:
                    self._exception.set_args(e)
                    self._exception.call()
                break
            
            self.position += 1
    
    def get_position(self):
        return self.position
    
    def get_result(self, index):
        """
        Retrieve the result of a single function call by specifying the order
        in which the function was in the queue.
        
        @type   index: int
        @param  index: The queue index
        
        """
        
        return self.queue[index].get_result()
