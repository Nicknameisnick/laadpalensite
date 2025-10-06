import requests
import pandas as pd



response = requests.get("https://api.openchargemap.io/v3")
responsejson  = response.json()





