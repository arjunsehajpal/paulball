import os
from datetime import datetime, timedelta
from random import randrange

import pandas as pd


class DataPrep(object):
    def __init__(self, results_df, rankings_df, qualified_teams, start_date, end_date):
        self.results_df = results_df
        self.rankings_df = rankings_df
        self.QUALIFIED_TEAMS = qualified_teams
        self.DATA_START_DATE = start_date
        self.DATA_END_DATE = end_date

    def execute(self):
        """driver method"""
        self.process_results_data()
        self.process_rankings_data()
        self.join_results_ratings_data()
        self.adjusted_goals()

        return self.points_df

    def process_results_data(self):
        """processes historical results data"""
        self.results_df = self.results_df[self.results_df["date"].between(self.DATA_START_DATE, self.DATA_END_DATE)]

        self.results_df = self.results_df[
            self.results_df["home_team"].isin(self.QUALIFIED_TEAMS)
            | self.results_df["away_team"].isin(self.QUALIFIED_TEAMS)
        ]

    def process_rankings_data(self):
        """processes historical rankings data"""
        self.rankings_df = self.rankings_df.rename(columns={"rank_date": "date"})
        self.rankings_df = self.rankings_df[self.rankings_df["date"].between(self.DATA_START_DATE, self.DATA_END_DATE)]

        # mismatched country spellings with results_df
        rankings_rename_country_dict = {"USA": "United States", "Korea Republic": "South Korea", "IR Iran": "Iran"}
        self.rankings_df["country_full"] = self.rankings_df["country_full"].replace(rankings_rename_country_dict)

        # create start and end date for which rankings are valid
        self.rankings_df["end_date"] = self.rankings_df.groupby("country_full")["date"].shift(-1)

        self.rankings_df["end_date"] = self.rankings_df["end_date"].fillna(self.DATA_END_DATE)
        self.rankings_df = self.rankings_df.rename(columns={"date": "start_date"})

    def join_results_ratings_data(self) -> pd.DataFrame:
        """joins results data with the rankings data.
        Because, rankings are assigned at some time interval,
        all the matches occuring between old ranking and
        new ranking are assigned old rankings.
        """
        # Home team
        self.points_df = self.results_df.merge(
            self.rankings_df[["country_full", "rank", "total_points", "start_date", "end_date"]],
            left_on=["home_team"],
            right_on=["country_full"],
            how="left",
        ).query("date.between(start_date, end_date)")
        self.points_df = self.points_df.rename(
            columns={
                "rank": "home_rank",
                "total_points": "home_points",
            }
        )
        self.points_df = self.points_df.drop(columns=["start_date", "end_date", "country_full"])

        # Away team
        self.points_df = self.points_df.merge(
            self.rankings_df[["country_full", "rank", "total_points", "start_date", "end_date"]],
            left_on=["away_team"],
            right_on=["country_full"],
            how="left",
        ).query("date.between(start_date, end_date)")
        self.points_df = self.points_df.rename(
            columns={
                "rank": "away_rank",
                "total_points": "away_points",
            }
        )
        self.points_df = self.points_df.drop(columns=["start_date", "end_date", "country_full"])

    def adjusted_goals(self) -> pd.DataFrame:
        """adjusts the goals scored by a team based on quality of opposition

        Returns:
            pd.DataFrame: dataframe with additional columns of adjusted goals
        """
        self.points_df.loc[:, "adj_home_score"] = (self.points_df["home_score"] * self.points_df["away_points"]) / (
            self.points_df["home_points"]
        )
        self.points_df.loc[:, "adj_away_score"] = (self.points_df["away_score"] * self.points_df["home_points"]) / (
            self.points_df["away_points"]
        )
        self.points_df = self.points_df.drop(columns=["home_score", "away_score"]).rename(
            columns={"adj_home_score": "home_score", "adj_away_score": "away_score"}
        )


def get_random_date(start_date: str, end_date: str) -> datetime:
    """returns a random date between start_date and end_date.
    If the returned date is less than three months away from end_date,
    the function returns a date 3 months prior to end_date.

    Args:
        start_date (str)
        end_date (str)

    Returns:
        str: a random
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
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")


def monte_carlo_simulation(n_simulations):
    """a decorator to run a function multiple times.

    Returns:
        list
    """

    def simulate(func):
        def wrapper(home_team, away_team, result_df, rankings_df, Configurations, neutral=True):
            results = []
            for i in range(0, n_simulations):
                results.append(func(home_team, away_team, result_df, rankings_df, Configurations, neutral=True))
            return results

        return wrapper

    return simulate
