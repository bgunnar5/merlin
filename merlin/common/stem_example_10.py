import ndcctools.taskvine.stem as stem
from functools import partial

def add(a, b, c, d, e, f):
    return a + b + c + d + e + f

f = partial(add, c=1, d=2, e=3, f=4)
g = lambda x, y: add(x, 2, 4, 6, 8, y)

a = stem.Group([stem.Seed(f,2,2).set_manager("manager1") for i in range(2)])
b = stem.Group([stem.Seed(f).set_manager("manager1") for i in range(2)])
c = stem.Group([stem.Seed(g).set_manager("manager1") for i in range(2)])
d = stem.Group([stem.Seed(g).set_manager("manager1") for i in range(2)])
chain = stem.Chain(a,b.map("all"),c.map("all"),d.map("all"))
chain.run()

    
    

