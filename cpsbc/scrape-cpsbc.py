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

cities = ["100 Mile House","108 Mile Ranch","150 Mile House","Abbotsford","Agassiz","Aiyansh","Aldergrove","Alert Bay","Anmore","Argenta","Armstrong","Ashcroft","Atlin","Bamfield","Banff","Barriere","Battleford","Belcarra","Bella Bella","Bella Coola","Black Creek","Blind Bay","Blue River","Bonnington","Bowen Island","Bowser","Brackendale","Brentwood Bay","Brockville","Burnaby","Burns Lake","Calgary","Campbell River","Canoe","Cassidy","Castlegar","Cawston","Cedar","Charlie Lake","Chase","Chemainus","Chetwynd","Chicago","Chilliwack","Christina Lake","Clearwater","Clinton","Cobble Hill","Coldstream","Colwood, BC","Comox","Coquitalm","Coquitlam","Courtenay","Cranbrook","Crawford Bay","Creston","Cultus Lake","Cumberland","Dawson City","Dawson Creek","Dease Lake","Delta","Denman Island","Denny Island","Dewdney","Duncan","Edmonton","Egmont","Elkford","Enderby","Erickson","Errington","Esquimalt","Fairmont Hot Springs","Fanny Bay","Fernie","Field","Fort Langley","Fort Nelson","Fort St James","Fort St John","Fort St. James","Fort St. John","Fort Steele","Fraser Lake","Fredericton","Fruitvale","Furry Creek","Gabriola","Galiano","Ganges","Garden Bay","Garibaldi Highlands","Gibsons","Gillies Bay","Gimli","Gold River","Golden","Grand Forks","Granisle","Granthams Landing","Grasmere","Gray Creek","Greenwood","Guelph","Hagensborg","Halfmoon Bay","Halifax","Harrison Hot Springs","Hazelton","Heriot Bay","High River","Hope","Hornby Island","Houston","Hudson's Hope","Invermere","Kaleden","Kamloops","Kaslo","Kelowna","Keremeos","Kimberley","Kingston","Kitimat","Knutsford","Kootenay Bay","Lac Le Jeune","Ladner","Ladysmith","Lake Country","Lake Cowichan","Langford","Langley","Lantzville","Lax Kw'alaams","Lazo","Lethbridge","Likely","Lillooet","Lindell Beach","Lions Bay","Lisburn","Logan Lake","Lumby","Lytton","Mackenzie","Madeira Park","Malahat","Manning Park","Mansons Landing","Maple Ridge","Mara","Marysville","Masset","Mayne","McBride","Merritt","Metchosin","Midway","Mill Bay","Milner","Mission","Montrose","Mount Lehman","Nakusp","Nanaimo","Nanoose Bay","Naramata","Nelson","New Aiyansh","New Denver","New Westminister","New Westminster","North Delta","North Saanich","North Vancouver","Not in Practice","Okanagan Falls","Oliver","Osoyoos","Ottawa","Owen Sound","Oyama","Panorama","Parksville","PATIALA","Peachland","Pemberton","Pender Island","Penticton","Pitt Meadows","Port Alberni","Port Alice","Port Clements","Port Coquitlam","Port Hardy","Port McNeill","Port Moody","Portland","Powell River","Prince George","Prince Rupert","Princeton","Qualicum Beach","Quathiaski Cove","Quebec","Queen Charlotte","Queen Charlotte City","Quesnel","Red Deer","Regina","Revelstoke","Richmond","Richmond Hill","Riondel","Roberts Creek","Rock Creek","Rosedale","Rossland","Rossland PO Box 1856","Royston","Saanichton","Salmo","Salmon Arm","Salt Spring Island","San Josef","Sardis","Saskatoon","Saturna","Sayward","Scotch Creek","Sechelt","Shawnigan Lake","Sherwood Park","Sicamous","Sidney","Slocan Park","Smithers","Sooke","Sorrento","South Surrey","Sparwood","Squamish","St Catharines","St. John's","Stewart","Stittsville","Stratford","Summerland","Sun Peaks","Surrey","Tahsis","Tampa","Tappen","Tatla Lake","Tatlayoko Lake","Telkwa","Terrace","Thetis Island","Tofino","Toronto","Trail","Tsawwassen","Tumbler Ridge","Ucluelet","Valemount","Vanciuver","Vancouber","Vancouver","Vanderhoof","Vernon","Victoria","View Royal","Waglisla","Wardner","Wasa","West Burlington","West Kelowna","West Vancouver","Westbank","Whaletown","Whistler","White Rock","Whitehorse","Williams Lake","Wilson Creek","Windermere","Winfield","Winlaw","Winnipeg","Youbou"]

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
    for s in td.strings:
        d["practice"] = s
        break
    td = td.next_sibling
    d["gender"] = td.text
    td = td.next_sibling
    d["accepting_new_patients"] = td.text
    d["specialities"] = []
    spec = tag.find(attrs={"class": "specialty_list"})
    if spec is not None:
        for li in spec.find_all("li"):
            d["specialities"].append(li.string)
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

    if last_name_prefix == "":
        result_path = "results/{}.json".format(city)
    else:
        result_path = "results/{}-{}.json".format(city, last_name_prefix)

    if os.path.isfile(result_path):
        continue

    print("{} {}".format(city, last_name_prefix))

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
            for br in soup.find_all("br"):
                br.replace_with("\n")
            d, _ = parse_result_page(soup)
            doctors.extend(d)

    except TooManyResultsError:
        for letter in string.ascii_uppercase:
            queries_to_try.append((city, letter))

    except NoResultsError:
        print("no doctors found for {} {}".format(city, last_name_prefix))

    if len(doctors) != 0:
        with open(result_path, "w") as f:
            json.dump(doctors, f)

