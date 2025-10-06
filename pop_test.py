# population_example.py
import os
import requests
import pandas as pd
from urllib.parse import urlencode

API_URL = "https://api.api-ninjas.com/v1/population"  # docs: endpoint
# docs: header 'X-Api-Key' required. :contentReference[oaicite:1]{index=1}

def get_population(country_name, api_key=None, timeout=10):
    if api_key is None:
        api_key = os.environ.get("API_NINJAS_KEY")  # use env var
        if not api_key:
            raise RuntimeError("Set API_NINJAS_KEY environment variable with your API Ninjas key.")
    headers = {"X-Api-Key": api_key}
    params = {"country": country_name}
    resp = requests.get(API_URL, headers=headers, params=params, timeout=timeout)
    # basic error handling
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} - {resp.text}")
    return resp.json()

def main():
    country = "Japan"   # change to any country name or 2-letter code (e.g. 'JP')
    api_key = None      # set to a string to override env var

    try:
        json_data = get_population(country, api_key=api_key)
    except Exception as e:
        print("Request failed:", e)
        return

    # Inspect top-level content
    print("Top-level keys:", list(json_data.keys()))

    # According to docs, response contains country_name, historical_population, population_forecast, ...
    # If present, convert the historical_population list into a DataFrame and show head()
    if isinstance(json_data, dict) and "historical_population" in json_data:
        df_hist = pd.json_normalize(json_data, record_path="historical_population")
        print("\nHistorical population (first rows):")
        print(df_hist.head())
    else:
        # Some endpoints return arrays; handle generically
        try:
            df = pd.json_normalize(json_data)
            print("\nNormalized JSON (first rows):")
            print(df.head())
        except Exception:
            print("\nRaw JSON (preview):")
            import json
            print(json.dumps(json_data, indent=2)[:1000])  # truncated

if __name__ == "__main__":
    main()


