from seriesly import Seriesly

db = Seriesly()['fast']
doc = db.get_all()
time = {}
for k,v in doc.iteritems():
    if "mc-curr_items" in v.keys() and "mc-host" in v.keys():
        time[k]= {"item": v["mc-curr_items"], "ip":v["mc-host"]}
    else:
        time[k]= {"item": "No items"}

for k, v in sorted(time.iteritems()):
    print k, v

