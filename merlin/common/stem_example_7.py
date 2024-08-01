import ndcctools.taskvine.stem as stem

def add(x, y, z=0):
    return x + y + z

a = stem.Group([stem.Seed(add,2,2,z=0).set_manager("manager1") for i in range(2)])
b = stem.Group([stem.Seed(add).set_manager("manager1") for i in range(2)])
c = stem.Group([stem.Seed(add).set_manager("manager1") for i in range(2)])
d = stem.Group([stem.Seed(add).set_manager("manager1") for i in range(2)])
chain = stem.Chain(a,b.map("all"),c.map("all"),d.map("all"))
chain.run()

    
    

