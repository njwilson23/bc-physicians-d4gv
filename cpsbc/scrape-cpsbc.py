import bs4
import json
import os
import requests
import string

BASEURL = "https://www.cpsbc.ca/physician_search"

class TooManyResultsError(Exception):
    pass

class NoResultsError(Exception):
    pass

if not os.path.isdir("results"):
    os.mkdir("results")

with open("cities.json") as f:
    cities = json.load(f).get("cities", [])

def get_nonce_and_cookie():
    req = requests.get(BASEURL)
    if req.status_code != 200:
        raise IOError(req.status_code)

    soup = bs4.BeautifulSoup(req.content.decode("utf-8"), "html5lib")
    tag = soup.find(attrs={"name": "filter[nonce]"})
    nonce = tag.attrs["value"]
    return nonce, req.cookies

def make_params(community_name, last_name, nonce):
    params = {
        "filter_first_name": "",
        "filter_last_name": last_name,
        "filter_gp_or_spec": "G",
        "filter_accept_new_pat": "0",
        "filter_specialty": "",
        "filter_gender": "",
        "filter_language": "",
        "filter_city": community_name,
        "filter_radius": "",
        "filter_postal_code": "",
        "filter_active": "Y",
        "filter_nonce": nonce
    }
    return params

def get_query(cookie, params=None, url=None):
    if params is not None:
        resp = requests.post(BASEURL, params=params, cookies=cookie)
    elif url is not None:
        resp = requests.get(url, cookies=cookie)
    else:
        raise ValueError()
    resp.status_code
    if resp.status_code != 200:
        raise IOError(resp.status_code)

    return bs4.BeautifulSoup(resp.content.decode("utf-8"), "html5lib")

def extract_doctor(tag):
    d = {}
    td = tag.find("td", attrs={"class": "title-address"})
    d["name"] = td.a.text.strip(" »")
    d["addresses"] = []
    for li in td.find_all("li"):
        d["addresses"].append(li.find(attrs={"class": "physio-address-data"}).text)
    td = td.next_sibling
    d["practice"] = td.text
    td = td.next_sibling
    d["gender"] = td.text
    td = td.next_sibling
    d["accepting_new_patients"] = td.text
    return d

def parse_result_page(soup):
    # read doctors from page
    doctors = []
    tag = soup.find(attrs={"class": "college-physio-search-results"})

    if tag is None:
        tag = soup.find(attrs={"class": ["messages", "error"]})
        if tag is not None and "too many results" in tag.text:
            raise TooManyResultsError()
        elif tag is not None and "no results" in tag.text:
            raise NoResultsError()
        raise Exception("parse_result_page: unknown error")

    for tr in tag.find_all("tr"):
        if tr.attrs.get("class", [""])[0] in ("odd", "even"):
            doc = extract_doctor(tr)
            #print(doc.get("name", "ERROR"))
            doctors.append(doc)

    # get further pages
    further_links = []
    for li in soup.find("ul", attrs={"class": "pager"}).find_all("li"):
        if "active" not in li.a.attrs.get("class", []) and "last" not in li.attrs.get("class", []):
            further_links.append(li.a.attrs["href"])
    return doctors, further_links

nonce, cookie = get_nonce_and_cookie()

queries_to_try = [(city, "") for city in cities]

while len(queries_to_try) != 0:
    city, last_name_prefix = queries_to_try.pop()

    print("{} {}".format(city, last_name_prefix))

    if last_name_prefix == "":
        result_path = "results/{}.json".format(city)
    else:
        result_path = "results/{}-{}.json".format(city, last_name_prefix)

    if os.path.isfile(result_path):
        continue

    try:
        params = make_params(city, last_name_prefix, nonce)
        soup = get_query(cookie, params=params)
        for br in soup.find_all("br"):
            br.replace_with("\n")
    except Exception as e:
        print("failure working on {}".format(city))
        print("  ", type(e))
        print("  ", e)
        continue

    doctors = []
    try:
        doctors, further_links = parse_result_page(soup)
        for link in further_links:
            soup = get_query(cookie, url=link)
            d, _ = parse_result_page(soup)
            doctors.extend(d)

    except TooManyResultsError:
        for letter in string.ascii_uppercase:
            queries_to_try.append((city, letter))

    except NoResultsError:
        pass

    if len(doctors) != 0:
        with open(result_path, "w") as f:
            json.dump(doctors, f)

