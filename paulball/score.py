import os
from math import exp, factorial

import numpy as np
import pandas as pd
from scipy import stats

from paulball.utils import get_data


class PredictScoreline(object):
    """_summary_

    Args:
        home_team (_type_): _description_
        away_team (_type_): _description_
        neutral (bool, optional): _description_. Defaults to False.
    """

    def __init__(self, home_team: str, away_team: str, neutral: bool = False):
        self.home_team = home_team
        self.away_team = away_team
        self.neutral = neutral

    def execute(self):
        """driver method"""
        results_df = get_data()

        # home and away team aggregated data
        home_team_df = self.team_record_aggregation(results_df, team_label="home", team_name=self.home_team)
        away_team_df = self.team_record_aggregation(results_df, team_label="away", team_name=self.away_team)

    def team_record_aggregation(self, results_df: pd.DataFrame, team_label: str, team_name: str) -> pd.DataFrame:
        """aggregates the goal scored and conceded by a Team

        Args:
            results_df (pandas.DataFrame): _description_
            team_label (str): whether the team playing at home or away
            team_name (str): team name

        Returns:
            team_df (pandas.DataFrame)
        """
        # opposite to the team_label passed
        alt_team_label = "away" if team_label == "home" else "home"

        team_df = results_df[results_df["{}_team".format(team_label)].isin(team_name)]

        # Aggregation
        team_df = (
            team_df.groupby("{}_team".format(team_label))
            .agg(
                played=pd.NamedAgg(column="date", aggfunc="nunique"),
                goals_for=pd.NamedAgg(column="{}_score".format(team_label), aggfunc="sum"),
                goals_against=pd.NamedAgg(column="{}_score".format(alt_team_label), aggfunc="sum"),
            )
            .reset_index()
        )

        # average interval of Poisson Process. Here, goals scored & conceded
        team_df["goals_per_game_scored"] = team_df["goals_for"] / team_df["played"]
        team_df["goals_per_game_conceded"] = team_df["goals_against"] / team_df["played"]

        return team_df
