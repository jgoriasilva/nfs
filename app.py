import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import re
import os

EXP_REGEX = r"[\n\t\r\xa0]"


def filter_data(data):
    return re.sub(EXP_REGEX, "", data)


def convert_to_float(data: str) -> str | float:
    try:
        data = data.replace(',','.')
        data = float(data)
    except ValueError:
        print(f"Could not convert {data} to float.")
    return data


def find_store_id(CNPJ, address) -> str:
    if os.path.exists("stores.csv"):
        stores = pd.read_csv("stores.csv", index_col=0)
        store_ids = stores[(stores["address"] == address) & (stores["CNPJ"] == CNPJ)]["store_id"]
        if len(store_ids):
            store_id = store_ids[0]
            return store_id
        else:
            store_id = len(stores)
    else:
        store_id = "0"
        stores = pd.DataFrame()

    stores = pd.concat([stores, pd.DataFrame(data=[[store_id, CNPJ, address]], columns=["store_id", "CNPJ", "address"])])
    stores.to_csv("stores.csv")
    
    return store_id


def parse_NFCe(chaves: set, URL: str) -> tuple[pd.DataFrame, str, str]:
    page = requests.get(URL)
    soup = bs(page.content, "html.parser")

    chave = soup.find("span", class_="chave").text.replace(' ','')

    if chave in chaves:
        print("NFCe already parsed.")
        return pd.DataFrame(), None, None

    CNPJ, address = soup.find(id="conteudo").findChildren(class_="text")
    CNPJ = filter_data(CNPJ.text).replace("CNPJ:","")
    address = filter_data(address.text)

    store_id = find_store_id(CNPJ, address)

    data = []
    tab_results = soup.find(id="tabResult")
    for product in tab_results.find_all("tr"):
        name = re.sub(EXP_REGEX, "", product.find("span", class_="txtTit").text).lower()
        # quantity = re.sub(EXP_REGEX, "", product.find("span", class_="Rqtd").text).replace("Qtde.:","")
        # quantity = convert_to_float(quantity)
        unit = re.sub(EXP_REGEX, "", product.find("span", class_="RUN").text).replace("UN: ","").lower()
        unit_value = re.sub(EXP_REGEX, "", product.find("span", class_="RvlUnit").text).replace("Vl. Unit.:", "")
        unit_value = round(convert_to_float(unit_value), 2)
        # value = quantity * unit_value
        data.append([store_id, name, unit, unit_value])
    
    return pd.DataFrame(data, columns=['store_id','name', 'unit', 'unit_value']), chave, store_id
    
    
def main() -> None:
    with open("URLs.txt", "r") as f:
        URLs = f.read().splitlines()

    if os.path.exists("purchases.csv"):
        purchases = pd.read_csv("purchases.csv", index_col=0)
    else:
        purchases = pd.DataFrame()

    if os.path.exists("nfces.csv"):
        nfces = pd.read_csv("nfces.csv", index_col=0)
        chaves = set(nfces["chave"])
    else:
        nfces = pd.DataFrame()
        chaves = set()
    
    for URL in URLs:
        df_nfce, chave, store_id = parse_NFCe(chaves, URL)
        purchases = pd.concat([purchases, df_nfce]).reset_index(drop=True)
        if chave is not None and store_id is not None:
            nfces = pd.concat([nfces, pd.DataFrame(data=[[chave, store_id]], columns=["chave", "store_id"])]).reset_index(drop=True)
    
    purchases.to_csv("purchases.csv")
    nfces.to_csv("nfces.csv")

    # with open("URLs.txt", "w") as f:
    #     f.write("")


if __name__ == '__main__':
    main()