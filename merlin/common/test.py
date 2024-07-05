import VineStem as stem

def add(x, y, z=3):
    return x + y + z

a = stem.Group([stem.Seed(add,i,i+1,z=i+2).set_manager("manager1") for i in range(200)])
b = stem.Seed(add,1,1,z=5).set_manager("manager1")
c = stem.Group([stem.Seed(add,2,2).set_manager("manager1") for i in range(2)])
d = stem.Seed(add,3,3).set_manager("manager1")
chain = stem.Chain(a,b,c,d)
chain.run()

    
    

