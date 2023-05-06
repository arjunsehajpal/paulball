from config import Configurations
from paulball.score import predict_final_score


HOME_TEAM = "Qatar"
AWAY_TEAM = "Ecuador"

predict_final_score(home_team=HOME_TEAM, away_team=AWAY_TEAM, config=Configurations)
