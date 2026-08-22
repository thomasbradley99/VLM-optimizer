"""Pre-cut the clip geometries the sweep needs. CPU only -- no API calls, so it runs alongside
anything that is network-bound."""
import json, os, sys, time
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE); sys.path.insert(0,HERE+"/mutator")
import pipeline as P
cfg=json.load(open(HERE+"/mutator/notebook/candidates/config_023.json")); cfg.pop("lever",None)
for L,o in ((5.0,2.0),(4.0,1.5)):
    c=P.normalise({**cfg,"chunk_len":L,"overlap":o})
    t0=time.time(); P.build_chunks(c, verbose=False)
    print(f"{L:g}s: {len(P.starts(c))} clips cut in {(time.time()-t0)/60:.1f} min", flush=True)
