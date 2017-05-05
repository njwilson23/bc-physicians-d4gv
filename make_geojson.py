import numpy as np
import karta
import pandas as pd
import sqlalchemy

ridings = karta.read_shapefile("edsre2015/edsre2015.shp")
ridings_simple = karta.read_geojson("edsre2015/edsre2015-simplified100.geojson")
census_ = pd.read_excel("demographics/2011CensusProfiles_87EDs.xlsx",
                            sheetname="Data")
census = census_.iloc[[0, 18, 19, 20, 21, 22, 23, 24]].T[1:]
census.columns = ["Population", "60-64", "65-69", "70-74", "75-79", "80-84",
                  "85+", "MedianAge"]
census.index.name = "Region"
census.index = [a.strip() for a in census.index]
print(census)

data = pd.read_sql("select distinct d.Name, "
                                   "d.Accepting_New_Patients, "
                                   "a.Longitude, a.Latitude, "
                                   "a.Locality "
                   "from doctors d "
                   "left join addresses a "
                   "on d.addr_id = a.addr_id ",
                   sqlalchemy.create_engine("sqlite:///care-providers.db"))

doctors_mp = karta.Multipoint(zip(data.Longitude, data.Latitude),
                              data={"index": list(range(len(data))),
                                    "Accepting_New_Patients": data.Accepting_New_Patients},
                              crs=karta.crs.LonLatWGS84)

ed_name_vec = np.empty(len(doctors_mp), dtype=object)
ed_id_vec = np.empty(len(doctors_mp), dtype=int)

for riding in ridings:
    print(riding.properties["ED_NAME"])
    doctors_in_riding = doctors_mp.within_polygon(riding)
    ed_name_vec[doctors_in_riding.d["index"]] = riding.properties["ED_NAME"]
    ed_id_vec[doctors_in_riding.d["index"]] = riding.properties["ED_ID"]

    riding.properties["DoctorCount"] = len(doctors_in_riding)
    riding.properties["DoctorCountAcceptingNewPatients"] = \
            int(np.sum([a == "Yes" for a in doctors_in_riding.d["Accepting_New_Patients"]]))
    riding.properties["MedianAge"] = census.loc[riding.properties["ED_NAME"], "MedianAge"]
    riding.properties["Population"] = census.loc[riding.properties["ED_NAME"], "Population"]
    riding.properties["Population65+"] = census.loc[riding.properties["ED_NAME"], "65-69"] + \
                                        census.loc[riding.properties["ED_NAME"], "70-74"] + \
                                        census.loc[riding.properties["ED_NAME"], "75-79"] + \
                                        census.loc[riding.properties["ED_NAME"], "80-84"] + \
                                        census.loc[riding.properties["ED_NAME"], "85+"]
    riding.properties["PopulationPerDoctor"] = riding.properties["Population"] // riding.properties["DoctorCount"]
    riding.properties["Population65+PerDoctor"] = riding.properties["Population65+"] // riding.properties["DoctorCount"]


# Write GeoJSON

from picogeojson import FeatureCollection, Feature, Polygon, dumps

def coordinates(geom):
    crds = [geom.get_vertices(karta.crs.LonLatWGS84).tolist()]
    crds[0].append(crds[0][0])
    return crds

features = [Feature(Polygon(coordinates(riding_simple)),
                {"Riding": riding.properties["ED_NAME"],
                 "MedianAge": riding.properties["MedianAge"],
                 "Population": riding.properties["Population"],
                 "Population65+": riding.properties["Population65+"],
                 "PopulationPerDoctor": riding.properties["PopulationPerDoctor"],
                 "Population65+PerDoctor": riding.properties["Population65+PerDoctor"],
                 "DoctorCount":  riding.properties["DoctorCount"],
                 "DoctorCountAcceptingNewPatients": riding.properties["DoctorCountAcceptingNewPatients"]})
            for riding, riding_simple in zip(ridings, ridings_simple)]

coll = FeatureCollection(features)

with open("doctors-plus-stats.geojson", "w") as f:
    f.write(dumps(coll))
