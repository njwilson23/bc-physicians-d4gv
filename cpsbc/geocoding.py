import os
import requests
import picogeojson
import re
import json
import pandas as pd

data = pd.read_csv("CPSBC-data-v0.2.6.csv")

results = {}

for irow, row in data.iterrows():

    if str(irow) in results:
        continue

    if irow%100 == 0:
        print(irow)
        with open("bc-geodata.json", "w") as f:
            json.dump(results, f)

    addr = row.Address.split("//")
    for i, part in enumerate(addr):
        if re.match("[0-9]{2}", part) is not None:
            addr = addr[i:]
            break

    resp = requests.get("https://apps.gov.bc.ca/pub/geocoder/addresses.json",
                        params = {
                            "addressString": " ".join(addr),
                            "maxResults": 1,
                            "provinceCode": "BC",
                            "locality": row.Locality
                        })

    if resp.status_code == 200:
        for pt in picogeojson.result_fromstring(resp.content.decode("utf-8")).features("Point"):
            results[str(irow)] = {"lon": pt.geometry.coordinates[0],
                                  "lat": pt.geometry.coordinates[1],
                                  "name": row.Name,
                                  "addr": row.Address}
            break # only one

with open("bc-geodata.json", "w") as f:
    json.dump(results, f)



index = []
lon = []
lat = []
names = []
for irow, row in data.iterrows():
    index.append(irow)
    if str(irow) in results:
        if results[str(irow)]["name"] != row.Name:
            raise KeyError(irow)
        lon.append(results[str(irow)]["lon"])
        lat.append(results[str(irow)]["lat"])

geotable = pandas.DataFrame(dict(index=index, Longitude=lon, Latitude=lat))

geotable.to_csv("bc-geodata.csv")

merged = pandas.concat([data, geotable[["Longitude", "Latitude"]]], axis=1)

feature_collection = picogeojson.FeatureCollection(
    [picogeojson.Feature(
        picogeojson.Point([row.Longitude, row.Latitude]),
        {"Name": row.Name,
         "Locality": row.Locality,
         "Address": row.Address}) for _, row in merged.iterrows()])

with open("doctors.geojson", "w") as f:
    f.write(picogeojson.tostring(feature_collection))
