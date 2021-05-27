import pandas as pd
import json

df = pd.read_csv("hepes_optimization.csv")
addresses = ["{}{}".format(b,a) for a in [1,2,3,4,5,6] for b in ["A","B","C","D"]]
addresses_96 = ["{}{}".format(b,a) for a in [1,2,3,4,5,6,7,8,9,10,11,12] for b in ["A","B","C","D","E","F","G","H"]]


setup = []
tubes = {}
for i, row in df.iterrows():
    if row["Component"] != "Total volume":
        setup.append({"name": row["Component"], "address": addresses[i]})
        tube_num = 0
        for name, ele in row.items():
            if "Volume" in name and pd.notna(ele):
                if tube_num not in tubes:
                    tubes[tube_num] = []
                tubes[tube_num].append({"name": row["Component"], "volume": ele})
                tube_num+=1

buffers = []
for k,v in tubes.items():
    buffers.append({"address": addresses_96[k], "buffer_volumes": v})


d = {"setup": setup, "buffers": buffers}
with open("hepes.json", "w") as outfile: 
    json.dump(d, outfile)
