import os
from datetime import datetime, timedelta
from random import randrange

import pandas as pd


class DataPrep(object):
    def __init__(self, results_data_path, qualified_teams, start_date, end_date):
        self.RESULT_DATA_PATH = results_data_path
        self.QUALIFIED_TEAMS = qualified_teams
        self.DATA_START_DATE = start_date
        self.DATA_END_DATE = end_date

    def execute(self):
        """driver method"""
        results_df = self.get_results_data()
        rankings_df = self.get_rankings_data()
        points_df = self.join_results_ratings_data(results_df, rankings_df)
        points_df = self.adjusted_goals(points_df)

        return points_df

    def get_results_data(self):
        """gets historical results data

        Returns:
            pandas.DataFrame: results of teams qualified for 2022 FIFA World Cup
        """
        results_df = pd.read_csv(self.RESULT_DATA_PATH, parse_dates=["date"])
        results_df = results_df[results_df["date"].between(self.DATA_START_DATE, self.DATA_END_DATE)]

        qualified_df = results_df[
            results_df["home_team"].isin(self.QUALIFIED_TEAMS) | results_df["away_team"].isin(self.QUALIFIED_TEAMS)
        ]

        return qualified_df

    def get_rankings_data(self):
        """get historical rankings data

        Returns:
            pandas.DataFrame: historical rankings and rating points of teams
        """
        rankings_path = os.path.join("data", "internationals", "rankings-2022-10-06.csv")
        rankings_df = pd.read_csv(rankings_path, parse_dates=["rank_date"])
        rankings_df = rankings_df.rename(columns={"rank_date": "date"})
        rankings_df = rankings_df[rankings_df["date"].between(self.DATA_START_DATE, self.DATA_END_DATE)]

        # mismatched country spellings with results_df
        rankings_rename_country_dict = {"USA": "United States", "Korea Republic": "South Korea", "IR Iran": "Iran"}
        rankings_df["country_full"] = rankings_df["country_full"].replace(rankings_rename_country_dict)

        # create start and end date for which rankings are valid
        rankings_df["end_date"] = rankings_df.groupby("country_full")["date"].shift(-1)
        rankings_df["end_date"] = rankings_df["end_date"].fillna("2022-11-20")
        rankings_df = rankings_df.rename(columns={"date": "start_date"})

        return rankings_df

    def join_results_ratings_data(self, results_df: pd.DataFrame, rankings_df: pd.DataFrame) -> pd.DataFrame:
        """_summary_

        Args:
            results_df (pd.DataFrame): _description_
            rankings_df (pd.DataFrame): _description_

        Returns:
            pd.DataFrame: _description_
        """
        # Home team
        points_df = results_df.merge(
            rankings_df[["country_full", "rank", "total_points", "start_date", "end_date"]],
            left_on=["home_team"],
            right_on=["country_full"],
            how="left",
        ).query("date.between(start_date, end_date)")
        points_df = points_df.rename(
            columns={
                "rank": "home_rank",
                "total_points": "home_points",
            }
        )
        points_df = points_df.drop(columns=["start_date", "end_date", "country_full"])

        # Away team
        points_df = points_df.merge(
            rankings_df[["country_full", "rank", "total_points", "start_date", "end_date"]],
            left_on=["away_team"],
            right_on=["country_full"],
            how="left",
        ).query("date.between(start_date, end_date)")
        points_df = points_df.rename(
            columns={
                "rank": "away_rank",
                "total_points": "away_points",
            }
        )
        points_df = points_df.drop(columns=["start_date", "end_date", "country_full"])

        return points_df

    def adjusted_goals(self, points_df: pd.DataFrame) -> pd.DataFrame:
        """adjusts the goals scored by a team based on quality of opposition

        Args:
            points_df (pd.DataFrame): dataframe with team scores and ratings

        Returns:
            pd.DataFrame: dataframe with additional columns of adjusted goals
        """
        points_df.loc[:, "adj_home_score"] = (points_df["home_score"] * points_df["away_points"]) / (
            points_df["home_points"]
        )
        points_df.loc[:, "adj_away_score"] = (points_df["away_score"] * points_df["home_points"]) / (
            points_df["away_points"]
        )
        points_df = points_df.drop(columns=["home_score", "away_score"]).rename(
            columns={"adj_home_score": "home_score", "adj_away_score": "away_score"}
        )

        return points_df
    

def get_random_date(start_date:str, end_date:str) -> datetime:
    """returns a random date between start_date and end_date.
    If the returned date is less than three months away from end_date,
    the function returns a date 3 months prior to end_date.

    Args:
        start_date (str)
        end_date (str)

    Returns:
        datetime
    """
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    date_diff = end_date - start_date
    int_diff = date_diff.days

    # sanity check: difference shouldn't be less than 90
    # or three months as that could result in team not having played any match
    if int_diff < 90:
        int_diff = 90

    random_days = randrange(int_diff)
    return start_date + timedelta(days=random_days)
