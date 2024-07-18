import ndcctools.taskvine.stem as stem
from functools import partial

def add(a, b, c, d, e, f):
    return a + b + c + d + e + f

func = partial(add, c=1, d=2, e=3, f=4)
a = stem.Group([stem.Seed(func,2,2).set_manager("manager1") for i in range(2)])
b = stem.Group([stem.Seed(func).set_manager("manager1") for i in range(2)])
c = stem.Group([stem.Seed(func).set_manager("manager1") for i in range(2)])
d = stem.Group([stem.Seed(func).set_manager("manager1") for i in range(2)])
chain = stem.Chain(a,b.map("all"),c.map("all"),d.map("all"))
chain.run()

    
    

