from aco_sim.model import catalogue,make_population,make_agents,simulate,REGIONS,SPECIALTIES,RESOURCES

def test_catalogue():
 c=catalogue();assert len(c)==49 and c.ipu.nunique()==26 and c.pathway_id.nunique()==49

def test_results():
 a=make_agents(make_population(),agents_per_region=15)
 d=simulate(a)
 assert len(d)==13*18*4
 assert set(d.Region)==set(REGIONS)
 assert set(d.Specialty)==set(SPECIALTIES)
 assert set(d.Resource)==set(RESOURCES)
 assert (d.Demand>=0).all() and (d.Supply>=0).all()
 assert ((d.Demand-d.Supply-d.Gap).abs()<1e-8).all()
