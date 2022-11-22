import os
import pandas as pd


DATA_START_DATE = "2018-08-01"
DATA_END_DATE = "2022-11-20"
QUALIFIED_TEAMS = [
    "Australia",
    "Iran",
    "Japan",
    "Qatar",
    "Saudi Arabia",
    "South Korea",
    "Cameroon",
    "Ghana",
    "Morocco",
    "Senegal",
    "Tunisia",
    "Canada",
    "Costa Rica",
    "Mexico",
    "United States",
    "Argentina",
    "Brazil",
    "Ecuador",
    "Uruguay",
    "Belgium",
    "Croatia",
    "Denmark",
    "England",
    "France",
    "Germany",
    "Netherlands",
    "Poland",
    "Portugal",
    "Serbia",
    "Spain",
    "Switzerland",
    "Wales",
]


def get_data():
    """gets historical results data

    Returns:
        pandas.DataFrame: results of teams qualified for 2022 FIFA World Cup
    """

    results_path = os.path.join("data", "internationals", "results.csv")
    results_df = pd.read_csv(results_path, parse_dates=["date"])
    results_df = results_df[results_df["date"].between(DATA_START_DATE, DATA_END_DATE)]

    qualified_df = results_df[
        results_df["home_team"].isin(QUALIFIED_TEAMS) | results_df["away_team"].isin(QUALIFIED_TEAMS)
    ]

    return qualified_df
