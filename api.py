from nba_api.stats.endpoints import (
    leaguedashplayerstats,
    scoreboardv2
)

from nba_api.stats.static import teams

from nba_api.live.nba.endpoints import scoreboard

from datetime import datetime
import pandas as pd
import os
import json

# ---------------------------------
# NBA TEAM ID MAP
# ---------------------------------
def build_team_id_map():

    nba_teams = teams.get_teams()

    return {
        team["id"]: team["abbreviation"]
        for team in nba_teams
    }

# ---------------------------------
# VALID NBA TEAMS
# ---------------------------------
VALID_NBA_TEAMS = [

    "ATL", "BOS", "BKN", "CHA", "CHI",
    "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM",
    "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR",
    "SAC", "SAS", "TOR", "UTA", "WAS"

]

# ---------------------------------
# TEAM NORMALIZATION
# ---------------------------------
def normalize_team_abbreviation(team):

    if pd.isna(team):
        return ""

    team = str(team).strip().upper()

    return team

# ---------------------------------
# SCHEDULE VALIDATION
# ---------------------------------
def validate_games(games):

    valid_games = []

    for game in games:

        away = normalize_team_abbreviation(
            game.get("away")
        )

        home = normalize_team_abbreviation(
            game.get("home")
        )

        if away not in VALID_NBA_TEAMS:
            print(f"INVALID AWAY TEAM IN SCHEDULE: {away}")
            continue

        if home not in VALID_NBA_TEAMS:
            print(f"INVALID HOME TEAM IN SCHEDULE: {home}")
            continue

        if away == home:
            print(f"INVALID MATCHUP SAME TEAM: {away} vs {home}")
            continue

        valid_games.append({
            "game_id": game.get("game_id"),
            "away": away,
            "home": home
        })

    return valid_games

# ---------------------------------
# DAILY SLATE VERIFICATION
# ---------------------------------
def verify_daily_slate(games):

    try:

        game_count = len(games)

        print("DAILY SLATE VERIFICATION COUNT:")
        print(game_count)

        if game_count == 0:
            return False

        # NBA daily slates under 2 games are suspicious
        # unless it is a known small playoff slate.
        if game_count < 2:
            print("DAILY SLATE WARNING: LOW GAME COUNT")
            return False

        return True

    except Exception as e:

        print("DAILY SLATE VERIFICATION ERROR:")
        print(str(e))

        return False

# ---------------------------------
# LIVE SCHEDULE CONSISTENCY CHECK
# ---------------------------------
def check_schedule_consistency(
    primary_games,
    secondary_games
):

    try:

        if len(primary_games) == 0:
            return True

        if len(secondary_games) == 0:
            return True

        primary_count = len(primary_games)
        secondary_count = len(secondary_games)

        print("PRIMARY SCHEDULE COUNT:")
        print(primary_count)

        print("SECONDARY SCHEDULE COUNT:")
        print(secondary_count)

        if abs(primary_count - secondary_count) > 2:

            print("SCHEDULE CONSISTENCY WARNING: LARGE SOURCE DIFFERENCE")
            return False

        return True

    except Exception as e:

        print("SCHEDULE CONSISTENCY ERROR:")
        print(str(e))

        return False

# ---------------------------------
# NAME NORMALIZATION
# ---------------------------------
def normalize_player_name(name):

    if pd.isna(name):
        return ""

    name = str(name).strip().lower()

    replacements = {
        "'": "",
        "’": "",
        "-": " ",
        ".": "",
        ",": ""
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    name = " ".join(name.split())

    return name

def try_live_scoreboard():

    try:

        board = scoreboard.ScoreBoard()

        data = board.get_dict()

        if not isinstance(data, dict):
            print("LIVE SCOREBOARD INVALID DATA TYPE")
            return []

        games_data = data.get("scoreboard", {}).get("games", [])

        if not isinstance(games_data, list):
            print("LIVE SCOREBOARD GAMES NOT LIST")
            return []

        return games_data

    except Exception as e:

        print("LIVE SCOREBOARD ERROR:")
        print(str(e))

        return []
    
    
# ---------------------------------
# SECONDARY LIVE SCHEDULE SOURCE
# ---------------------------------
def try_secondary_schedule_source():

    try:

        print("SECONDARY SCHEDULE SOURCE CHECK STARTED")

        today = datetime.now().strftime("%m/%d/%Y")

        board = scoreboardv2.ScoreboardV2(
            game_date=today
        )

        game_header = board.get_data_frames()[0]

        if game_header.empty:
            print("SECONDARY SCHEDULE SOURCE EMPTY")
            return []

        
        team_id_map = build_team_id_map()
        
        secondary_games = []

        for _, row in game_header.iterrows():

            game_status_text = str(
                row.get("GAME_STATUS_TEXT", "")
            ).upper()


            if "UNNECESSARY" in game_status_text:
                continue

            secondary_games.append({
                "game_id": row.get("GAME_ID"),
                "away": team_id_map.get(row.get("VISITOR_TEAM_ID")),
                "home": team_id_map.get(row.get("HOME_TEAM_ID"))
            })

        print("SECONDARY SCHEDULE SOURCE LOADED")
        print(secondary_games)

        return secondary_games

    except Exception as e:

        print("SECONDARY SCHEDULE SOURCE ERROR:")
        print(str(e))

        return []

def get_games():

    try:

        today = datetime.now().strftime("%m/%d/%Y")
        print("NBA API DATE REQUESTED:")
        print(today)

        games_data = try_live_scoreboard()

        print("LIVE SCOREBOARD GAME COUNT:")
        print(len(games_data))

        secondary_games_data = try_secondary_schedule_source()

        print("SECONDARY SCHEDULE GAME COUNT:")
        print(len(secondary_games_data))

        schedule_consistent = check_schedule_consistency(
            games_data,
            secondary_games_data
        )

        print("SCHEDULE CONSISTENCY CHECK:")
        print(schedule_consistent)


        games = []

        # NORMAL LIVE API PATH
        if len(games_data) > 0:

            print("DATA MODE: LIVE")

            for game in games_data:

                games.append({

                "game_id": game.get("gameId"),
                "away": game.get("awayTeam", {}).get("teamTricode"),
                "home": game.get("homeTeam", {}).get("teamTricode")

                })

        # SECONDARY LIVE API PATH
        if len(games) == 0 and len(secondary_games_data) > 0:

            print("DATA MODE: SECONDARY LIVE SCHEDULE")

            for game in secondary_games_data:

                games.append({

                    "game_id": game.get("game_id"),
                    "away": game.get("away"),
                    "home": game.get("home")

                })


        # FALLBACK IF LIVE SOURCES FAIL
        if len(games) == 0:

            print("DATA MODE: FALLBACK")
            print("USING FALLBACK PLAYOFF GAMES")

            games = get_fallback_games()

        games = validate_games(games)

        slate_verified = verify_daily_slate(games)

        print("DAILY SLATE VERIFIED:")
        print(slate_verified)

        print("PARSED GAMES:")
        print(games)

        if len(games) == 0:
            print("NO VALID GAMES AFTER SCHEDULE VALIDATION")

        if len(games_data) > 0:

            schedule_source = "LIVE_SCOREBOARD"

        elif len(secondary_games_data) > 0:

            schedule_source = "SECONDARY_LIVE_SCHEDULE"

        else:

            schedule_source = "VALIDATED_FALLBACK"

        return games, schedule_source, slate_verified, schedule_consistent

    except Exception as e:

        print("GAME API ERROR:")
        print(str(e))

        games = validate_games(
            get_fallback_games()
        )

        return games, "VALIDATED_HARD_FAILSAFE", verify_daily_slate(games), False


# ---------------------------------
# FALLBACK SCHEDULE
# ---------------------------------
def get_fallback_games():

    return [

        {
            "game_id": None,
            "away": "CLE",
            "home": "DET"
        }

    ]

# ---------------------------------
# REAL PLAYER STATS
# ---------------------------------
def get_real_player_stats():

    try:

        df = leaguedashplayerstats.LeagueDashPlayerStats(
            season='2025-26',
            per_mode_detailed='PerGame'
        ).get_data_frames()[0]

        df = df[[

            "PLAYER_NAME",
            "TEAM_ABBREVIATION",
            "MIN",
            "FGA",
            "PTS"

        ]]

        df.columns = [

            "player",
            "team",
            "minutes",
            "fga",
            "points"

        ]

        print("PLAYER DATA LOADED")

        return df

    except Exception as e:

        print("PLAYER API ERROR:")
        print(str(e))

        return None
    
# ---------------------------------
# EXTERNAL LINEUP INGESTION
# ---------------------------------

def normalize_external_lineup_url(source_url):

    if not source_url:
        return source_url

    source_url = source_url.strip()

    if "docs.google.com/spreadsheets" in source_url:

        if "/edit" in source_url:
            source_url = source_url.split("/edit")[0]

        if "gid=" in source_url:
            gid = source_url.split("gid=")[-1].split("&")[0]
        else:
            gid = "0"

        source_url = f"{source_url}/export?format=csv&gid={gid}"

    return source_url

def refresh_lineups_from_external_csv(source_url):

    try:

        if not source_url:
            print("NO EXTERNAL LINEUP SOURCE URL PROVIDED")
            return False

        normalized_source_url = normalize_external_lineup_url(source_url)

        print("NORMALIZED LINEUP SOURCE URL:")
        print(normalized_source_url)

        external_df = pd.read_csv(normalized_source_url)

        required_columns = ["date", "team", "player", "status"]

        for col in required_columns:
            if col not in external_df.columns:
                print(f"EXTERNAL LINEUP SOURCE MISSING COLUMN: {col}")
                return False

        external_df = external_df[required_columns]

        external_df["team"] = external_df["team"].apply(
            normalize_team_abbreviation
        )

        external_df["player_normalized"] = external_df["player"].apply(
            normalize_player_name
        )

        os.makedirs("data", exist_ok=True)

        external_df.to_csv(
            "data/today_lineups.csv",
            index=False
        )

        print("EXTERNAL LINEUPS INGESTED SUCCESSFULLY")
        print(external_df)

        return True

    except Exception as e:

        print("EXTERNAL LINEUP INGESTION ERROR:")
        print(str(e))

        return False    
    
# ---------------------------------
# LINEUP SOURCE
# ---------------------------------
def get_today_lineups():

    lineup_path = os.getenv(
        "LINEUP_SOURCE_PATH",
        "data/today_lineups.csv"
    )

    try:

        if lineup_path.startswith("http"):
            lineups_df = pd.read_csv(lineup_path)

        else:

            if not os.path.exists(lineup_path):
                print("LINEUP FILE NOT FOUND")
                return pd.DataFrame(columns=["date", "team", "player", "status"])

            lineups_df = pd.read_csv(lineup_path)

        today_str = datetime.now().strftime("%Y-%m-%d")

        today_lineups_df = lineups_df[
            lineups_df["date"].astype(str) == today_str
        ]

        if today_lineups_df.empty and not lineups_df.empty:

            print("NO LINEUPS FOUND FOR TODAY. USING MOST RECENT AVAILABLE LINEUP DATE.")

            lineups_df["lineup_date_warning"] = (
                "Stale lineup date used"
            )

            most_recent_lineup_date = lineups_df["date"].astype(str).max()

            lineups_df = lineups_df[
                lineups_df["date"].astype(str) == most_recent_lineup_date
            ]

        else:

            lineups_df = today_lineups_df

        lineups_df = lineups_df[
            lineups_df["status"].isin([
                "Projected",
                "Confirmed"
            ])
        ]
        
        required_columns = ["date", "team", "player", "status"]

        for col in required_columns:
            if col not in lineups_df.columns:
                lineups_df[col] = ""

        if "lineup_date_warning" not in lineups_df.columns:
            lineups_df["lineup_date_warning"] = ""

        lineups_df = lineups_df[
            required_columns + ["lineup_date_warning"]
        ]

        lineups_df["team"] = lineups_df["team"].apply(
            normalize_team_abbreviation
        )

        if "player_normalized" not in lineups_df.columns:
            lineups_df["player_normalized"] = lineups_df["player"].apply(
                normalize_player_name
            )

        print("LINEUP DATA LOADED")
        print(lineups_df)

        return lineups_df

    except Exception as e:

        print("LINEUP FILE ERROR:")
        print(str(e))

        return pd.DataFrame(columns=["date", "team", "player", "status"])    
# ---------------------------------
# Provider Performance
# ---------------------------------
def update_source_grading(
    source_name,
    success,
    player_count,
    duplicate_count,
    missing_players
):

    try:

        os.makedirs("results", exist_ok=True)

        grading_path = "results/source_grades.json"

        if os.path.exists(grading_path):

            with open(grading_path, "r") as f:
                grades = json.load(f)

        else:

            grades = {}

        if source_name not in grades:

            grades[source_name] = {

                "successful_refreshes": 0,
                "failed_refreshes": 0,
                "total_refreshes": 0,
                "avg_player_count": [],
                "duplicate_issues": 0,
                "missing_players": 0

            }

        grades[source_name]["total_refreshes"] += 1

        if success:
            grades[source_name]["successful_refreshes"] += 1
        else:
            grades[source_name]["failed_refreshes"] += 1

        grades[source_name]["avg_player_count"].append(player_count)

        if duplicate_count > 0:
            grades[source_name]["duplicate_issues"] += duplicate_count

        grades[source_name]["missing_players"] += missing_players

        with open(grading_path, "w") as f:
            json.dump(grades, f, indent=4)

        print("SOURCE GRADING UPDATED")

        return True

    except Exception as e:

        print("SOURCE GRADING ERROR:")
        print(str(e))

        return False    