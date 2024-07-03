import sys
import select
import os
import time
import ndcctools.taskvine as vine
import pickle
from multiprocessing import Pipe

class VineChain():
    """
    A chain is group of tasks or groups that are executed in order
    by default, running a singular group or signature eventually executes chain(group(sig))
    """
    def __init__ (self, *args):
        self._chain = []
        for arg in iter(args):
            try:
                iargs = iter(arg):
                for iarg in iargs:
                    if isinstance(iarg, VineGroup):
                        self._group.append(iarg)
                    elif isinstance(iarg, VineSignature):
                        self._group.append(iarg)
                    else:
                        raise TypeError
            except TypeError:
                raise 

            except:
                if isinstance(arg, VineGroup):
                    self._group.append(arg)
                elif isinstance(arg, VineSignature):
                    self._group.append(arg)
                else:
                    raise TypeError

    def run(self):
        self._current_link = self._chain.pop(0):
        while self._current_link:
            link = self._current_link
            if isinstance(link, VineGroup):
                

            # This is simple, execute task then grab next link
            elif isinstance(link, VineSignature):
                            
class VineGroup():
    """
    A group is a collection of tasks and chains that can execute in parallel:
    """
    def __init__ (self, *args):
        self._group = []
        for arg in iter(args):
            try:
                iargs = iter(arg):
                for iarg in iargs:
                    if isinstance(iarg, VineChain):
                        self._group.append(iarg)
                    elif isinstance(iarg, VineSignature):
                        self._group.append(iarg)
                    else:
                        raise TypeError
            except TypeError:
                raise 

            except:
                if isinstance(arg, VineChain):
                    self._group.append(arg)
                elif isinstance(arg, VineSignature):
                    self._group.append(arg)
                else:
                    raise TypeError
                
    def run(self):
        chain = VineChain(self)
        chain.run()
    
class VineSignature():
    def __init__(self, function, *args, **kwargs):
        self._function = function
        self._args = args
        self._kwargs = kwargs

    def set_manager(self, manager):
        self._manager = manager
        return self

    def run(self)
        group = VineGroup(self)
        group.run()
        
    def print(self):
        print(self._function, self._args, self._kwargs) 


def run_manager(name):
    
    p_read, c_write = Pipe()
    c_read, p_write = Pipe() 
    pid = os.fork()
    
    # Stem
    if pid:

        return p_read, p_write

    # Manager
    else:

        time.sleep(1) 
        tasks = []
        m = vine.Manager(port=[9123,9143], name=name)
        while(True):
            if c_read.poll():
                try:
                    t = c_read.recv() 
                    if isinstance(t, VineSignature):
                        pass
                        # create task
                except:
                    pass
            
            if not m.empty():
                t = m.wait(5)
                if t:
                    pass
                    
        # create tasks
        # wait for tasks
        # Send complete tasks
    
        




        
