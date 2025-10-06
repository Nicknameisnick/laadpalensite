import requests
import pandas as pd



response = requests.get("https://api.openchargemap.io/v3?output=json&countrycode=NL&maxresults=100&compact=true&verbose=false&key=2960318e-86ae-49e0-82b1-3c8bc6790b41")
responsejson  = response.json()






