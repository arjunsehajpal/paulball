from math import exp, factorial

import numpy as np
import pandas as pd

from paulball.utils import DataPrep, get_random_date, monte_carlo_simulation


class PredictScoreline(object):
    """predicts the probability of win for a particular football match

    Args:
        home_team (str): team playing at home ground
        away_team (str): visiting team
        neutral (bool, optional): whether the venue is neutral or not. Defaults to False.
    """

    def __init__(self):
        pass

    def __call__(
        self,
        home_team: str,
        away_team: str,
        neutral: bool,
        results_df: pd.DataFrame,
        rankings_df: pd.DataFrame,
        qualified_teams: list,
        start_date: str,
        end_date: str,
    ):
        self.home_team = home_team
        self.away_team = away_team
        self.neutral = neutral
        self.results_df = results_df
        self.rankings_df = rankings_df
        self.qualified_teams = qualified_teams
        self.start_date = start_date
        self.end_date = end_date

        score_tuple = self.execute()

        return score_tuple

    def execute(self):
        """driver method"""
        dp_obj = DataPrep(self.results_df, self.rankings_df, self.qualified_teams, self.start_date, self.end_date)
        results_df = dp_obj.execute()

        # home and away team aggregated data
        home_team_df = self.team_record_aggregation(results_df, team_label="home", team_name=self.home_team)
        away_team_df = self.team_record_aggregation(results_df, team_label="away", team_name=self.away_team)

        # goal summaries
        home_goals_dict = self.goal_summaries(home_team_df, team_label="home", team_name=self.home_team)
        away_goals_dict = self.goal_summaries(away_team_df, team_label="away", team_name=self.away_team)

        # projected goals
        projected_home_goals, projected_away_goals = self.projected_goals(home_goals_dict, away_goals_dict)

        # probability distribution of number of goals that can be scored
        home_goal_prob_df, home_goal_prob_list = self.teams_goals_probability(projected_home_goals)
        away_goal_prob_df, away_goal_prob_list = self.teams_goals_probability(projected_away_goals)

        # scoreline matrix
        _ = self.expected_scoreline(away_goal_prob_df, home_goal_prob_list)

        return (projected_home_goals, projected_away_goals)

    def team_record_aggregation(self, results_df: pd.DataFrame, team_label: str, team_name: str) -> pd.DataFrame:
        """aggregates the goal scored and conceded by a Team

        Args:
            results_df (pandas.DataFrame): dataframe with results of all the teams eligible
            team_label (str): whether the team playing at home or away
            team_name (str): team name

        Returns:
            team_df (pandas.DataFrame)
        """
        # opposite to the team_label passed
        alt_team_label = "away" if team_label == "home" else "home"

        team_df = results_df[results_df["{}_team".format(team_label)] == team_name]

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

    def goal_summaries(self, teams_df: pd.DataFrame, team_label: str, team_name: str) -> float:
        """calculates point estimates of goals scored and conceded

        Args:
            teams_df (pd.DataFrame): dataframe with results of all the teams eligible
            team_label (str): whether the team playing at home or away
            team_name (str): team name

        Returns:
            dict
        """
        avg_gpg_scored = teams_df["goals_per_game_scored"].mean()
        avg_team_gpg_scored = teams_df[teams_df["{}_team".format(team_label)] == team_name][
            "goals_per_game_scored"
        ].squeeze()
        avg_team_gpg_conceded = teams_df[teams_df["{}_team".format(team_label)] == team_name][
            "goals_per_game_conceded"
        ].squeeze()

        return {
            "avg_gpg_scored": avg_gpg_scored,
            "avg_team_gpg_scored": avg_team_gpg_scored,
            "avg_team_gpg_conceded": avg_team_gpg_conceded,
        }

    def projected_goals(self, home_goals_dict: dict, away_goals_dict: dict) -> float:
        """calculate projected goals teams will score in next match

        Args:
            home_goals_dict (dict): goal summaries of home team
            away_goals_dict (dict): goal summaries of away team

        Returns:
            float: projected goals
        """
        home_attack = home_goals_dict["avg_team_gpg_scored"] / home_goals_dict["avg_gpg_scored"]
        away_defence = away_goals_dict["avg_team_gpg_conceded"] / home_goals_dict["avg_gpg_scored"]
        away_attack = away_goals_dict["avg_team_gpg_scored"] / away_goals_dict["avg_gpg_scored"]
        home_defence = home_goals_dict["avg_team_gpg_conceded"] / away_goals_dict["avg_gpg_scored"]

        projected_home_goals = home_attack * away_defence * home_goals_dict["avg_gpg_scored"]
        projected_away_goals = away_attack * home_defence * away_goals_dict["avg_gpg_scored"]

        return projected_home_goals, projected_away_goals

    def teams_goals_probability(self, projected_goals: float) -> pd.Series:
        """calculates the probability of goals scored by a team (upto 8 goals)

        Args:
            projected_goals (float): projected goals predicted by Poisson Modelling

        Returns:
            pd.Series: probabilities of number of goals scored
        """
        goal_prob_list = []
        for i in range(0, 9):
            prob = ((projected_goals**i) * exp(-1 * projected_goals)) / factorial(i)
            goal_prob_list.append(prob)

        goal_prob_df = pd.Series(goal_prob_list, index=range(0, 9))

        return goal_prob_df, goal_prob_list

    def expected_scoreline(self, away_goal_prob_df: pd.Series, home_goal_prob_list: list) -> pd.DataFrame:
        """returns the matrix of probable scorelines, ranging from 0-0 to 8-8

        Args:
            away_goal_prob_df (pd.Series): probabilities of number of goals away team can score
            home_goal_prob_list (list): probabilities of number of goals home team can score

        Returns:
            pd.DataFrame: matrix of probable scorelines
        """
        # initialize placeholders to store final values
        expected_scoreline_df = pd.DataFrame()
        home_win_probability = 0
        away_win_probability = 0
        draw_probability = 0
        max_probability = 0  # Probability of most probable result

        # the loop tries to perform A * B.T operation, where A and B are n*1 matrices
        for i, home_goal in enumerate(home_goal_prob_list):
            temp_df = home_goal * away_goal_prob_df
            expected_scoreline_df = pd.concat((expected_scoreline_df, temp_df), axis=1).rename(columns={0: str(i)})
            mx_prob = max(temp_df)

            # if mx_prob is greater than max_probability, overwrite it
            if mx_prob >= max_probability:
                max_probability = mx_prob

            # sum of probability where home score > away score
            hw_prob = sum(temp_df.iloc[:i])

            # probability where home score == away score
            dr_prob = temp_df.iloc[i]

            # sum of probability where home score < away score
            if i < len(home_goal_prob_list):
                aw_prob = sum(temp_df.iloc[i + 1 :])

            # running sums
            home_win_probability += hw_prob
            away_win_probability += aw_prob
            draw_probability += dr_prob

        return expected_scoreline_df


predict_score = PredictScoreline()


@monte_carlo_simulation(100)
def match_simulator(home_team, away_team, result_df, rankings_df, Configurations, neutral=True):
    """simulates the result of a match multiple times.
    The start date is updated

    Returns:
        results (list[tuple]): a list of all the simulated results
    """
    current_iter_start_date = get_random_date(Configurations.START_DATE, Configurations.END_DATE)
    try:
        results = predict_score(
            home_team=home_team,
            away_team=away_team,
            neutral=neutral,
            results_df=result_df,
            rankings_df=rankings_df,
            qualified_teams=Configurations.QUALFIED_TEAMS,
            start_date=current_iter_start_date,
            end_date=Configurations.END_DATE,
        )
        return results
    except TypeError as T:
        print("encountered following error:\n", T)
        return (np.nan, np.nan)


def predict_final_score(home_team, away_team, config, neutral=True):
    """predicts the final score of the match.
    This function is a wrapper on match_simulator.

    Args:
        home_team (str): home team
        away_team (str): away team
        config (callable): a class capturing all the config variables
        neutral (bool, optional): if the match if being played at a Neutral venue or not. Defaults to True.

    Returns:
        tuple: aggregated match result
    """
    result_df = pd.read_csv(config.RESULT_DATA_PATH)
    rankings_df = pd.read_csv(config.RANKINGS_DATA_PATH, parse_dates=["rank_date"])

    results = match_simulator(home_team, away_team, result_df, rankings_df, config)
    home_team_score_list, away_team_score_list = zip(*results)
    home_team_score, away_team_score = np.nanmean(home_team_score_list), np.nanmean(away_team_score_list)
    print("{} {:.2f}-{:.2f} {}".format(home_team, home_team_score, away_team_score, away_team))
