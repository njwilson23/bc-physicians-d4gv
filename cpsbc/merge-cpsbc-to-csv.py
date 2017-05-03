import os
import json
import pandas
import functools

VERSION = "0.2.3"

outfnm = "CPSBC-data-v{}.csv".format(VERSION)
if os.path.exists(outfnm):
    raise IOError("{} already exists".format(outfnm))

def read_json(fnm):
    with open(os.path.join("results", fnm), "r") as f:
        ds = json.load(f)
    for d in ds:
        d["locality"] = fnm[:-5].split("-")[0]
    return ds

def extend(L1, L2):
    L1.extend(L2)
    return L1

files = filter(lambda a: a.endswith(".json"), os.listdir("results/"))
all_doctors = functools.reduce(extend, map(read_json, files))
print("{} doctors found".format(len(all_doctors)))

names = [d["name"] for d in all_doctors]
addr = [d["addresses"][0].replace("\n", "//") for d in all_doctors]
gender = [d["gender"] for d in all_doctors]
practice = [d["practice"] for d in all_doctors]
newpat = [d["accepting_new_patients"] for d in all_doctors]

gfp = ["General Family Practice" in p for p in practice]
ccfp = ["CCFP" in d["specialities"] for d in all_doctors]
ccfp_em = ["CCFP (EM)" in d["specialities"] for d in all_doctors]
emer_med = ["Emergency Medicine+" in d["specialities"] for d in all_doctors]
an_path = ["RCPSC - Anatomical Pathology" in d["specialities"] for d in all_doctors]
int_med = ["RCPSC - Internal Medicine" in d["specialities"] for d in all_doctors]
med_bio = ["RCPSC - Medical Biochemistry" in d["specialities"] for d in all_doctors]
gen_surg = ["RCPSC - General Surgery" in d["specialities"] for d in all_doctors]

locality = [d["locality"] for d in all_doctors]

data = pandas.DataFrame(
    {
        "Name": names,
        "Address": addr,
        "Gender": gender,
        "Accepting_New_Patients": newpat,
        "General_Family_Practice": gfp,
        "CCFP": ccfp,
        "CCFP_EM": ccfp_em,
        "Emergency_Medicine": emer_med,
        "Anatomical_Pathology": an_path,
        "Internal_Medicine": int_med,
        "Medical_Biochemistry": med_bio,
        "General_Surgery": gen_surg,
        "Locality": locality
    })

data.to_csv(outfnm)
