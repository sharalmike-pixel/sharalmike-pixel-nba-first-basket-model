print("NEW APP FILE LOADED")

import streamlit as st
import pandas as pd
import os

os.makedirs("results", exist_ok=True)
os.makedirs("data", exist_ok=True)

bankroll_unlocked = False

with st.sidebar:
    st.markdown("### Private Access")

    bankroll_password_input = st.text_input(
        "Bankroll Password",
        type="password"
    )

    if bankroll_password_input == st.secrets.get("BANKROLL_PASSWORD", ""):
        bankroll_unlocked = True
        st.success("Bankroll unlocked")
    elif bankroll_password_input:
        st.error("Incorrect password")

from api import (
    get_games,
    get_real_player_stats,
    get_today_lineups,
    refresh_lineups_from_external_csv,
    update_source_grading,
    VALID_NBA_TEAMS
)

# ---------------------------------
# BEST PROVIDER SELECTOR
# ---------------------------------
def get_best_active_provider(source_grades_df):

    if source_grades_df.empty:
        return None

    active_df = source_grades_df[
        source_grades_df["provider_status"] == "Active"
    ].copy()

    active_df = active_df[
        active_df["automation_ready"] == "Yes"
    ]

    if active_df.empty:
        return None

    best_provider = active_df.sort_values(
        "reliability_score",
        ascending=False
    ).iloc[0]

    return best_provider["source_name"]

# ---------------------------------
# ODDS CONVERSION
# ---------------------------------
def american_to_probability(odds):

    if odds > 0:
        return 100 / (odds + 100)

    return abs(odds) / (abs(odds) + 100)


# ---------------------------------
# DYNAMIC ODDS GENERATOR
# ---------------------------------
def probability_to_american(probability):

    implied = probability / 100

    if implied <= 0:
        return None

    # SPORTSBOOK JUICE
    implied *= 1.08

    american = ((1 - implied) / implied) * 100

    return int(round(american))


# ---------------------------------
# UI SHELL
# ---------------------------------

st.title("NBA First Basket Dashboard")

st.caption(
    "Live first basket projections, betting analytics, bankroll tracking, and provider monitoring."
)

MODEL_VERSION = "v43_live_ready_bet_form_fixed"

# ---------------------------------
# RESULTS & PERSISTENCE
# ---------------------------------

# ---------------------------------
# RESULTS TRACKER
# ---------------------------------
results_path = "results/first_basket_results.csv"

bets_path = "results/actual_bets.csv"

bankroll_path = "results/bankroll_transactions.csv"

required_bankroll_columns = [
    "date",
    "transaction_type",
    "amount",
    "notes"
]

required_bet_columns = [
    "date_bet",
    "matchup",
    "player",
    "team",
    "bet_type",
    "odds",
    "units",
    "unit_size",
    "total_bet_amount",
    "result",
    "profit_loss",
    "cash_profit_loss",
    "notes"
]

required_result_columns = [
    "date_saved",
    "model_version",
    "schedule_source",
    "schedule_trust_score",
    "slate_verified",
    "matchup",
    "projected_tip_winner",
    "player",
    "team",
    "probability",
    "odds",
    "confidence_score",
    "confidence",
    "edge_tier",
    "model_decision",
    "actual_first_basket",
    "correct_pick",
    "profit_loss",
    "date_completed"
]

if os.path.exists(results_path):

    results_df = pd.read_csv(results_path)

    for col in required_result_columns:
        if col not in results_df.columns:
            results_df[col] = ""

    results_df = results_df[required_result_columns]
    results_df = results_df.drop_duplicates(
            subset=["date_saved", "matchup"],
            keep="last"
        )
    results_df.to_csv(results_path, index=False)

else:

    results_df = pd.DataFrame(
        columns=required_result_columns
    )

if os.path.exists(bets_path):

    bets_df = pd.read_csv(bets_path)

    for col in required_bet_columns:
        if col not in bets_df.columns:
            bets_df[col] = ""

    bets_df = bets_df[required_bet_columns]

else:

    bets_df = pd.DataFrame(
        columns=required_bet_columns
    )

if os.path.exists(bankroll_path):

    bankroll_df = pd.read_csv(bankroll_path)

    for col in required_bankroll_columns:
        if col not in bankroll_df.columns:
            bankroll_df[col] = ""

    bankroll_df = bankroll_df[required_bankroll_columns]

else:

    bankroll_df = pd.DataFrame(
        columns=required_bankroll_columns
    )

# ---------------------------------
# OVERALL PERFORMANCE METRICS
# ---------------------------------
wins = len(
    results_df[
        results_df["correct_pick"] == "Yes"
    ]
)

losses = len(
    results_df[
        results_df["correct_pick"] == "No"
    ]
)

total_tracked = wins + losses

accuracy = (
    round((wins / total_tracked) * 100, 1)
    if total_tracked > 0
    else 0
)

profit_loss = pd.to_numeric(
    results_df["profit_loss"],
    errors="coerce"
).fillna(0).sum()

avg_profit_loss = (
    round(profit_loss / total_tracked, 2)
    if total_tracked > 0
    else 0
)

roi = (
    round((profit_loss / total_tracked) * 100, 1)
    if total_tracked > 0
    else 0
)

completed_bets_df = bets_df[
    bets_df["result"].isin(["Win", "Loss"])
].copy()

actual_bet_count = len(completed_bets_df)

actual_bet_profit = pd.to_numeric(
    completed_bets_df["profit_loss"],
    errors="coerce"
).fillna(0).sum()

actual_cash_profit = pd.to_numeric(
    completed_bets_df["cash_profit_loss"],
    errors="coerce"
).fillna(0).sum()

actual_cash_wagered = pd.to_numeric(
    completed_bets_df["total_bet_amount"],
    errors="coerce"
).fillna(0).sum()

actual_cash_roi = (
    round((actual_cash_profit / actual_cash_wagered) * 100, 1)
    if actual_cash_wagered > 0
    else 0
)

starting_balance = pd.to_numeric(
    bankroll_df[
        bankroll_df["transaction_type"] == "Starting Balance"
    ]["amount"],
    errors="coerce"
).fillna(0).sum()

total_deposits = pd.to_numeric(
    bankroll_df[
        bankroll_df["transaction_type"] == "Deposit"
    ]["amount"],
    errors="coerce"
).fillna(0).sum()

total_withdrawals = pd.to_numeric(
    bankroll_df[
        bankroll_df["transaction_type"] == "Withdrawal"
    ]["amount"],
    errors="coerce"
).fillna(0).sum()

current_bankroll = (
    starting_balance
    + total_deposits
    - total_withdrawals
    + actual_cash_profit
)

net_bankroll_invested = (
    starting_balance
    + total_deposits
)

bankroll_roi = (
    round((actual_cash_profit / net_bankroll_invested) * 100, 1)
    if net_bankroll_invested > 0
    else 0
)

actual_units_wagered = pd.to_numeric(
    completed_bets_df["units"],
    errors="coerce"
).fillna(0).sum()

actual_bet_roi = (
    round((actual_bet_profit / actual_units_wagered) * 100, 1)
    if actual_units_wagered > 0
    else 0
)

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Wins", wins)
col2.metric("Losses", losses)
col3.metric("Accuracy", f"{accuracy}%")
col4.metric("Profit/Loss", round(profit_loss, 2))
col5.metric("Avg P/L", avg_profit_loss)
col6.metric("ROI %", f"{roi}%")

bet_col1, bet_col2, bet_col3, bet_col4, bet_col5 = st.columns(5)

bet_col1.metric("Actual Bets", actual_bet_count)
bet_col2.metric("Unit P/L", round(actual_bet_profit, 2))
bet_col3.metric("Unit ROI %", f"{actual_bet_roi}%")
bet_col4.metric("Cash P/L ($)", round(actual_cash_profit, 2))
bet_col5.metric("Cash ROI %", f"{actual_cash_roi}%")

if bankroll_unlocked:

    bank_col1, bank_col2, bank_col3, bank_col4, bank_col5 = st.columns(5)

    bank_col1.metric("Starting Balance", round(starting_balance, 2))
    bank_col2.metric("Deposits", round(total_deposits, 2))
    bank_col3.metric("Withdrawals", round(total_withdrawals, 2))
    bank_col4.metric("Current Bankroll", round(current_bankroll, 2))
    bank_col5.metric("Bankroll ROI %", f"{bankroll_roi}%")


st.divider()

# ---------------------------------
# NAVIGATION
# ---------------------------------

dashboard_view = st.radio(
    "Navigation",
    [
        "Dashboard",
        "Operations"
    ],
    horizontal=True
)

show_operations = dashboard_view == "Operations"

lineup_provider_mode = "Local CSV"
external_lineup_url = "data/today_lineups.csv"
invalid_external_url = False
selected_provider_rejected = False

if show_operations:

    st.header("Daily Operations")

    st.subheader("Lineup Management")

    lineup_provider_mode = st.selectbox(
        "Lineup Source Mode",
        [
            "Local CSV",
            "External CSV URL",
            "Auto Best Provider",
            "Environment Override"
        ]
    )

    default_lineup_source = os.getenv(
        "LINEUP_SOURCE_PATH",
        "data/today_lineups.csv"
    )

    if lineup_provider_mode == "Local CSV":

        external_lineup_url = "data/today_lineups.csv"

        st.text_input(
            "Lineup Source URL",
            value=external_lineup_url,
            placeholder="Paste lineup CSV URL here",
            disabled=True
        )

    elif lineup_provider_mode == "External CSV URL":

        external_lineup_url = st.text_input(
            "Lineup Source URL",
            value="",
            placeholder="Paste external lineup CSV URL here"
        )

        if not external_lineup_url:
            st.warning(
                "No lineup source URL provided."
            )

        else:

            if (
                external_lineup_url.startswith("http")
                and (
                    ".csv" in external_lineup_url
                    or "sheet" in external_lineup_url
                    or "export" in external_lineup_url
                )
            ):

                st.success(
                    "Lineup source URL detected."
                )

            else:

                st.error(
                    "Source URL may not be a valid CSV/export source."
                )

    elif lineup_provider_mode == "Auto Best Provider":

        external_lineup_url = ""

        if os.path.exists("results/source_grades.json"):

            try:

                auto_provider_df = pd.read_json(
                    "results/source_grades.json"
                ).T.reset_index()

                auto_provider_df = auto_provider_df.rename(
                    columns={
                        "index": "source_name"
                    }
                )

                auto_provider_df["success_rate"] = (
                    (
                        auto_provider_df["successful_refreshes"]
                        /
                        auto_provider_df["total_refreshes"]
                    ) * 100
                ).round(1)

                auto_provider_df["reliability_score"] = (
                    auto_provider_df["success_rate"]
                    -
                    (auto_provider_df["duplicate_issues"] * 5)
                    -
                    (auto_provider_df["missing_players"] * 3)
                ).clip(lower=0, upper=100).round(1)

                auto_provider_df["provider_status"] = auto_provider_df[
                    "reliability_score"
                ].apply(
                    lambda score: "Rejected" if score < 50 else "Active"
                )

                auto_provider_df["automation_ready"] = auto_provider_df[
                    "reliability_score"
                ].apply(
                    lambda score: "Yes" if score >= 75 else "No"
                )

                best_provider = get_best_active_provider(auto_provider_df)

                if best_provider is not None:
                    external_lineup_url = best_provider
                    st.session_state["recommended_provider_url"] = best_provider

            except Exception:

                external_lineup_url = ""

        st.text_input(
            "Lineup Source URL",
            value=external_lineup_url,
            placeholder="Best provider will appear here",
            disabled=True
        )

    else:

        external_lineup_url = default_lineup_source

        st.text_input(
            "Lineup Source URL",
            value=external_lineup_url,
            placeholder="Environment override source",
            disabled=True
        )

    st.caption(
        "CSV must contain these columns: date, team, player, status"
    )

    env_lineup_source = os.getenv("LINEUP_SOURCE_PATH")

    if lineup_provider_mode == "Environment Override":

        st.info(
            f"Active Lineup Mode: ENV Override ({env_lineup_source})"
        )

    elif lineup_provider_mode == "External CSV URL":

        st.info("Active Lineup Mode: External URL")

    elif lineup_provider_mode == "Auto Best Provider":

        if external_lineup_url:
            st.info(
                f"Active Lineup Mode: Auto Best Provider ({external_lineup_url})"
            )

        else:
            st.warning(
                "Active Lineup Mode: Auto Best Provider selected, but no recommended provider is available yet."
            )

    else:

        st.info("Lineup Source: Local File")

    if "last_lineup_refresh" in st.session_state:

        if st.session_state["last_lineup_refresh"] == "Success":
            st.success("Last Lineup Refresh: Success")

        elif st.session_state["last_lineup_refresh"] == "Failed":
            st.error("Last Lineup Refresh: Failed")

        if "last_lineup_refresh_time" in st.session_state:
            st.caption(
                f"Last Refresh Time: {st.session_state['last_lineup_refresh_time']}"
            )
            
        if "last_lineup_source" in st.session_state:
            st.caption(
                f"Last Refresh Source: {st.session_state['last_lineup_source']}"
            )    

        if "last_lineup_count" in st.session_state:
            st.caption(
                f"Last Refresh Player Count: {st.session_state['last_lineup_count']}"
            )

            if st.session_state["last_lineup_count"] != 10:
                st.warning(
                    "Lineup count is not 10. Check for missing or extra starters."
                )        
        
    invalid_external_url = False

    if lineup_provider_mode in [
        "External CSV URL",
        "Auto Best Provider"
    ]:

        if not (
            external_lineup_url.startswith("http")
            and (
                ".csv" in external_lineup_url
                or "sheet" in external_lineup_url
                or "export" in external_lineup_url
            )
        ):
            invalid_external_url = True

    selected_provider_rejected = False

    if os.path.exists("results/source_grades.json"):

        try:

            existing_source_grades_df = pd.read_json(
                "results/source_grades.json"
            ).T.reset_index()

            existing_source_grades_df = existing_source_grades_df.rename(
                columns={
                    "index": "source_name"
                }
            )

            if "source_name" in existing_source_grades_df.columns:

                existing_source_grades_df["success_rate"] = (
                    (
                        existing_source_grades_df["successful_refreshes"]
                        /
                        existing_source_grades_df["total_refreshes"]
                    ) * 100
                ).round(1)

                existing_source_grades_df["reliability_score"] = (
                    existing_source_grades_df["success_rate"]
                    -
                    (existing_source_grades_df["duplicate_issues"] * 5)
                    -
                    (existing_source_grades_df["missing_players"] * 3)
                ).clip(lower=0, upper=100).round(1)

                selected_provider_rejected = (
                    lineup_provider_mode == "External CSV URL"
                    and external_lineup_url
                    and external_lineup_url in existing_source_grades_df[
                        existing_source_grades_df["reliability_score"] < 50
                    ]["source_name"].tolist()
                )

        except Exception:

            selected_provider_rejected = False

    refresh_disabled = (
        (
            lineup_provider_mode in [
                "External CSV URL",
                "Auto Best Provider"
            ]
            and not external_lineup_url
        )
        or invalid_external_url
        or selected_provider_rejected
    )

    if refresh_disabled:

        if (
            lineup_provider_mode in [
                "External CSV URL",
                "Auto Best Provider"
            ]
            and not external_lineup_url
        ):
            st.warning(
                "No valid lineup source is currently available for refresh."
            )

        elif invalid_external_url:
            st.warning(
                "Enter a valid lineup source URL before refreshing."
            )

        elif selected_provider_rejected:
            st.error(
                "This lineup provider is currently rejected. Refresh is disabled."
            )

    if (
        lineup_provider_mode in [
            "External CSV URL",
            "Auto Best Provider"
        ]
        and external_lineup_url
        and not invalid_external_url
        and not selected_provider_rejected
    ):

        st.success(
            "Refresh Status: Ready"
        )

    if (
        lineup_provider_mode in [
            "External CSV URL",
            "Auto Best Provider"
        ]
        and external_lineup_url
        and not invalid_external_url
    ):

        if os.path.exists("results/source_grades.json"):

            try:

                automation_status_df = pd.read_json(
                    "results/source_grades.json"
                ).T.reset_index()

                automation_status_df = automation_status_df.rename(
                    columns={
                        "index": "source_name"
                    }
                )

                automation_status_df["success_rate"] = (
                    (
                        automation_status_df["successful_refreshes"]
                        /
                        automation_status_df["total_refreshes"]
                    ) * 100
                ).round(1)

                automation_status_df["reliability_score"] = (
                    automation_status_df["success_rate"]
                    -
                    (automation_status_df["duplicate_issues"] * 5)
                    -
                    (automation_status_df["missing_players"] * 3)
                ).clip(lower=0, upper=100).round(1)

                selected_provider_score = automation_status_df[
                    automation_status_df["source_name"] == external_lineup_url
                ]

                if not selected_provider_score.empty:

                    selected_score = selected_provider_score.iloc[0]["reliability_score"]

                    if selected_score >= 75:

                        st.success(
                            f"Automation Status: Ready ({selected_score} score)"
                        )

                        st.caption(
                            "Auto-refresh recommendation: Safe."
                        )

                    else:

                        st.warning(
                            f"Automation Status: Not Ready ({selected_score} score)"
                        )

                        st.caption(
                            "Auto-refresh recommendation: Manual review required."
                        )


                else:

                    st.info(
                        "Automation Status: Unknown. Refresh once to create provider history."
                    )

                    st.caption(
                        "Auto-refresh recommendation: Not eligible until provider history exists."
                    )
            except Exception:

                st.warning(
                    "Automation status could not be calculated for selected provider."
                )

    refresh_button_label = (
        "Refresh Best Provider"
        if lineup_provider_mode == "Auto Best Provider"
        else "Refresh External Lineups"
    )

    if st.button(
        refresh_button_label,
        disabled=refresh_disabled
    ):

        refreshed = refresh_lineups_from_external_csv(
            external_lineup_url
        )

        if refreshed:
            
            refreshed_df = pd.read_csv("data/today_lineups.csv")

            duplicate_count = refreshed_df.duplicated(
                subset=["player"]
            ).sum()

            player_count = len(refreshed_df)
            
            st.session_state["last_lineup_refresh"] = "Success"
            st.session_state["last_lineup_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["last_lineup_source"] = external_lineup_url
            st.session_state["last_lineup_count"] = len(
                pd.read_csv("data/today_lineups.csv")
            )
            
            update_source_grading(
                source_name=external_lineup_url,
                success=True,
                player_count=player_count,
                duplicate_count=duplicate_count,
                missing_players=0
            )
            
            st.success("Lineup refresh completed successfully.")
            st.rerun()

        else:
            st.session_state["last_lineup_refresh"] = "Failed"

            update_source_grading(
                source_name=external_lineup_url,
                success=False,
                player_count=0,
                duplicate_count=0,
                missing_players=0
            )

            st.error("Lineup refresh failed. Check the source URL and CSV columns.")

# ---------------------------------
# DATA INGESTION CORE
# ---------------------------------

# ---------------------------------
# LOAD DATA
# ---------------------------------
games, data_mode, slate_verified, schedule_consistent = get_games()

schedule_trust_score = 100

if data_mode == "SECONDARY_LIVE_SCHEDULE":
    schedule_trust_score -= 15

elif data_mode == "VALIDATED_FALLBACK":
    schedule_trust_score -= 35

elif data_mode == "VALIDATED_HARD_FAILSAFE":
    schedule_trust_score -= 55

elif data_mode != "LIVE_SCOREBOARD":
    schedule_trust_score -= 50

if len(games) == 0:
    schedule_trust_score = 0

elif not slate_verified:
    schedule_trust_score -= 20

if not schedule_consistent:
    schedule_trust_score -= 15

schedule_trust_score = max(
    0,
    min(100, schedule_trust_score)
)

if len(games) == 0:

    st.stop()

if show_operations:

    with st.expander("Schedule Health", expanded=False):

        if data_mode == "LIVE_SCOREBOARD":

            st.success("Schedule Source: LIVE NBA SCOREBOARD")

        elif data_mode == "SECONDARY_LIVE_SCHEDULE":

            st.success("Schedule Source: SECONDARY LIVE SCHEDULE")

            st.caption(
                "Secondary live schedule source was used because the primary NBA scoreboard was unavailable."
            )

        elif data_mode == "VALIDATED_FALLBACK":

            st.warning("Schedule Source: VALIDATED FALLBACK GAMES")

            st.caption(
                "Fallback mode means today's schedule is coming from your validated fallback list."
            )

        elif data_mode == "VALIDATED_HARD_FAILSAFE":

            st.error("Schedule Source: VALIDATED HARD FAILSAFE")

            st.caption(
                "Hard failsafe means the schedule system encountered an unexpected error and used validated emergency fallback schedule."
            )

        else:

            st.error(f"Schedule Source: UNKNOWN ({data_mode})")

        if data_mode in [
            "VALIDATED_FALLBACK",
            "VALIDATED_HARD_FAILSAFE"
        ]:

            fallback_games_df = pd.DataFrame(games)

            if "game_id" in fallback_games_df.columns:
                fallback_games_df = fallback_games_df.drop(
                    columns=["game_id"]
                )

            with st.expander("Fallback Schedule", expanded=False): 

                st.caption(
                    f"Fallback Schedule Count: {len(fallback_games_df)}"
                )
                
                if len(fallback_games_df) == 0:
                    st.error(
                        "No fallback schedule is configured."
                    )
                
                if (
                    "away" not in fallback_games_df.columns
                    or "home" not in fallback_games_df.columns
                ):
                    st.error(
                        "Fallback games must include away and home columns."
                    )

                if "away" in fallback_games_df.columns and "home" in fallback_games_df.columns:

                    missing_fallback_teams = fallback_games_df[
                        fallback_games_df["away"].isna()
                        |
                        fallback_games_df["home"].isna()
                        |
                        (fallback_games_df["away"] == "")
                        |
                        (fallback_games_df["home"] == "")
                    ]

                    if not missing_fallback_teams.empty:
                        st.error(
                            "Fallback schedule contains missing team abbreviations."
                        )

                        st.dataframe(
                            missing_fallback_teams,
                            width="stretch"
                        )

                st.dataframe(
                    fallback_games_df,
                    width="stretch"
                )

        st.caption(
            f"Loaded Schedule Count: {len(games)}"
        )

        if slate_verified:

            st.success(
                "Daily Slate Verification: Verified"
            )

        else:

            st.warning(
                "Daily Slate Verification: Review Recommended"
            )

            st.caption(
                "The loaded schedule may be incomplete based on game count checks."
            )

        if schedule_consistent:

            st.success(
                "Schedule Consistency Check: Verified"
            )

        else:

            st.error(
                "Schedule Consistency Check: Conflict Detected"
            )

            st.caption(
                "Primary and secondary schedule sources disagree. Manual slate review recommended."
            )

        if len(games) == 0:

            st.error(
                "No games loaded. Model cannot generate matchup projections."
            )

        elif len(games) < 2:

            st.warning(
                "Low game count detected. Daily schedule may require review."
            )

        st.metric(
            "Schedule Trust Score",
            schedule_trust_score
        )

        if schedule_trust_score >= 85:

            st.success("Schedule Trust Level: Strong")

        elif schedule_trust_score >= 60:

            st.warning("Schedule Trust Level: Moderate")

        else:

            st.error("Schedule Trust Level: Caution")

        st.caption(
            f"Schedule Mode: {data_mode}"
        )

        if schedule_trust_score >= 85:

            st.success(
                "Schedule Recommendation: Safe for production use."
            )

        elif schedule_trust_score >= 60:

            st.warning(
                "Schedule Recommendation: Moderate trust. Manual review recommended."
            )

        else:

            st.error(
                "Schedule Recommendation: High caution. Manual review strongly recommended."
            )

        if schedule_trust_score < 60:

            st.caption(
                "Model Note: Lower schedule trust does not change player rankings yet, but it should reduce wager confidence."
            )

        if schedule_trust_score < 25:

            st.error(
                "Schedule trust is critically low. Projections may be unreliable."
            )


        st.caption("Displays active schedule source.")

      
players_df = get_real_player_stats()


# ---------------------------------
# BANKROLL MANAGEMENT
# ---------------------------------

if show_operations and bankroll_unlocked:

    st.subheader("Bankroll Management")

    with st.form("bankroll_transaction_form"):

        bankroll_date = st.date_input("Transaction Date")

        bankroll_transaction_type = st.selectbox(
            "Transaction Type",
            [
                "Starting Balance",
                "Deposit",
                "Withdrawal",
                "Adjustment"
            ]
        )

        bankroll_amount = st.number_input(
            "Amount ($)",
            value=0.0,
            step=10.0
        )

        bankroll_notes = st.text_input("Transaction Notes")

        submitted_bankroll = st.form_submit_button("Save Transaction")

        if submitted_bankroll:

            new_bankroll_row = pd.DataFrame([{
                "date": str(bankroll_date),
                "transaction_type": bankroll_transaction_type,
                "amount": bankroll_amount,
                "notes": bankroll_notes
            }])

            if os.path.exists(bankroll_path):

                existing_bankroll_df = pd.read_csv(bankroll_path)

                updated_bankroll_df = pd.concat(
                    [existing_bankroll_df, new_bankroll_row],
                    ignore_index=True
                )

            else:

                updated_bankroll_df = new_bankroll_row

            updated_bankroll_df.to_csv(
                bankroll_path,
                index=False
            )

            st.success("Transaction recorded successfully.")
            st.rerun()
            
if show_operations and not bankroll_df.empty:

    if bankroll_unlocked:

        with st.expander("Bankroll History", expanded=False):
            st.dataframe(
                bankroll_df.sort_values(
                    "date",
                    ascending=False
                ),
                width="stretch"
            )            

if show_operations and not bets_df.empty:

    with st.expander("Bet Tracking", expanded=False):

        st.dataframe(
            bets_df.sort_values(
                "date_bet",
                ascending=False
            ),
            width="stretch"
        )

if (
    lineup_provider_mode == "Auto Best Provider"
    and external_lineup_url
    and not invalid_external_url
    and not selected_provider_rejected
    and st.session_state.get("auto_best_provider_refreshed") != True
):

    st.session_state["auto_best_provider_refreshed"] = True

    auto_refreshed = refresh_lineups_from_external_csv(
        external_lineup_url
    )

    if auto_refreshed:

        st.session_state["last_lineup_refresh"] = "Success"
        st.session_state["last_lineup_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state["last_lineup_source"] = external_lineup_url

        if os.path.exists("data/today_lineups.csv"):
            st.session_state["last_lineup_count"] = len(
                pd.read_csv("data/today_lineups.csv")
            )

        st.success(
            "Best provider refreshed lineups successfully."
        )

    else:

        st.session_state["last_lineup_refresh"] = "Failed"

        st.error(
            "Best provider refresh failed. Falling back to existing local lineup file if available."
        )

if lineup_provider_mode == "Auto Best Provider":

    original_lineup_path = os.getenv("LINEUP_SOURCE_PATH")

    os.environ["LINEUP_SOURCE_PATH"] = "data/today_lineups.csv"

    lineups_df = get_today_lineups()

    if original_lineup_path:
        os.environ["LINEUP_SOURCE_PATH"] = original_lineup_path
    else:
        os.environ.pop("LINEUP_SOURCE_PATH", None)

else:

    lineups_df = get_today_lineups()

if (
    lineup_provider_mode == "External CSV URL"
    and not external_lineup_url
):

    st.warning(
        "External mode is selected with no source URL. Local lineup file is being ignored."
    )

    lineups_df = pd.DataFrame(
        columns=["date", "team", "player", "status"]
    )

if lineup_provider_mode == "Local CSV":

    active_lineup_source = "data/today_lineups.csv"

elif lineup_provider_mode in [
    "External CSV URL",
    "Auto Best Provider"
]:

    if lineup_provider_mode == "Auto Best Provider":

        active_lineup_source = "data/today_lineups.csv"

    else:

            active_lineup_source = (
                external_lineup_url
                if external_lineup_url
                else "No external source configured"
            )

else:

    active_lineup_source = os.getenv(
        "LINEUP_SOURCE_PATH",
        "data/today_lineups.csv"
    )

if show_operations:

    if not lineups_df.empty:

        if lineup_provider_mode == "External CSV URL" and not external_lineup_url:
            st.warning("Lineup Source: External Mode Selected, But No URL Provided")
        else:
            st.success("Lineup Source: Custom Source Loaded")

        st.caption(
            f"Active Lineup Source: {active_lineup_source}"
        )

        if (
            "lineup_date_warning" in lineups_df.columns
            and lineups_df["lineup_date_warning"].astype(str).str.contains("Stale").any()
        ):

            st.warning(
                "Lineup Warning: No lineup file was found for today. "
                "Using the most recent available lineup date."
            )

    else:

        st.warning("Lineup Source: No Lineup File Found")

        st.caption(
                f"Requested Lineup Source: {active_lineup_source}"
            )

else:

    if show_operations:

        st.warning("Lineup Source: No Lineup File Found")

        st.caption(
            f"Requested Lineup Source: {active_lineup_source}"
        )
 
if not lineups_df.empty:

    invalid_team_rows = lineups_df[
        ~lineups_df["team"].isin(VALID_NBA_TEAMS)
    ]

    if not invalid_team_rows.empty:

        st.error(
            "Invalid NBA team abbreviations detected in lineup data."
        )

        st.dataframe(
            invalid_team_rows,
            width="stretch"
        )

    active_game_teams = []

    for game in games:
        active_game_teams.append(game["away"])
        active_game_teams.append(game["home"])

if show_operations:

    with st.expander("Schedule Team Validation", expanded=False):

        st.write(
            ", ".join(active_game_teams)
        )
        
        teams_not_playing = lineups_df[
            ~lineups_df["team"].isin(active_game_teams)
        ]

    if not teams_not_playing.empty:

        st.warning(
            "Lineup source contains teams not present in today's loaded matchups."
        )

        st.dataframe(
            teams_not_playing,
            width="stretch"
        )
    team_validation_issue_count = (
        len(invalid_team_rows)
        +
        len(teams_not_playing)
    )

   
    if team_validation_issue_count == 0:

        st.success(
            "Team validation passed: all lineup teams are valid for today."
        )
        
    duplicate_players = lineups_df.copy()

    duplicate_players["player_normalized"] = duplicate_players["player"].apply(
        lambda x: x.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
    )

    duplicate_players = duplicate_players[
        duplicate_players.duplicated(
            subset=["player_normalized"],
            keep=False
        )
    ]

    if not duplicate_players.empty:
        st.error(
            "Duplicate players detected in lineup data."
        )

        st.dataframe(
            duplicate_players,
            width="stretch"
        )

# ---------------------------------
# BET TRACKING
# ---------------------------------

if show_operations:

    with st.expander("Lineup Diagnostics", expanded=False):

        st.dataframe(
            lineups_df,
            width="stretch"
        )
        
    st.subheader("Bet Tracking")

    matchup_options = [
        f"{game['away']} vs {game['home']}"
        for game in games
    ]

    bet_matchup = st.selectbox(
        "Matchup",
        matchup_options,
        key="actual_bet_matchup"
    )

    selected_matchup_teams = bet_matchup.split(" vs ")

    bet_team = st.selectbox(
        "Team",
        selected_matchup_teams,
        key="actual_bet_team"
    )
    
    selected_team_players = []

    if not lineups_df.empty:

        selected_team_players = lineups_df[
            lineups_df["team"].astype(str).str.strip() == str(bet_team).strip()
        ]["player"].drop_duplicates().tolist()

    if len(selected_team_players) == 0 and players_df is not None:

        selected_team_players = players_df[
            players_df["team"].astype(str).str.strip() == str(bet_team).strip()
        ].sort_values(
            ["minutes", "fga"],
            ascending=False
        )["player"].head(10).drop_duplicates().tolist()

    if len(selected_team_players) > 0:

        bet_player = st.selectbox(
            "Player",
            selected_team_players,
            key="actual_bet_player"
        )
        
    else:

        bet_player = st.text_input(
            "Player",
            key="actual_bet_player_manual"
        )

        st.warning(
            "No players found for selected team. Enter player manually if needed."
        )
    
    with st.form("actual_bet_form"):

        bet_date = st.date_input("Bet Date")
        
        bet_type = st.selectbox(
            "Bet Tracking",
            [
                "First Basket",
                "Other"
            ]
        )

        bet_odds = st.number_input("Odds", value=100, step=1)
        bet_units = st.number_input("Units", value=1.0, step=0.25)
        bet_unit_size = st.number_input("Unit Size ($)", value=20.0, step=1.0)
        
        bet_result = st.selectbox(
            "Result",
            [
                "Pending",
                "Win",
                "Loss",
                "Push"
            ]
        )

        total_bet_amount = bet_units * bet_unit_size
        
        st.caption(
            f"Total Bet Amount: ${round(total_bet_amount, 2)}"
        )

        bet_notes = st.text_input("Notes")

        submitted_bet = st.form_submit_button("Save Bet")

        if submitted_bet:

            if bet_result == "Win":

                profit_units = (
                    bet_odds / 100
                    if bet_odds > 0
                    else 100 / abs(bet_odds)
                ) * bet_units

                cash_profit_loss = profit_units * bet_unit_size

            elif bet_result == "Loss":

                profit_units = -bet_units
                cash_profit_loss = -total_bet_amount

            else:

                profit_units = 0
                cash_profit_loss = 0

            new_bet_row = pd.DataFrame([{
                "date_bet": str(bet_date),
                "matchup": bet_matchup,
                "player": bet_player,
                "team": bet_team,
                "bet_type": bet_type,
                "odds": bet_odds,
                "units": bet_units,
                "unit_size": bet_unit_size,
                "total_bet_amount": total_bet_amount,
                "result": bet_result,
                "profit_loss": profit_units,
                "cash_profit_loss": cash_profit_loss,
                "notes": bet_notes
            }])

            if os.path.exists(bets_path):

                existing_bets_df = pd.read_csv(bets_path)

                duplicate_bet = existing_bets_df[
                    (existing_bets_df["date_bet"].astype(str) == str(bet_date))
                    &
                    (existing_bets_df["matchup"].astype(str) == str(bet_matchup))
                    &
                    (existing_bets_df["player"].astype(str) == str(bet_player))
                    &
                    (existing_bets_df["bet_type"].astype(str) == str(bet_type))
                ]

                if not duplicate_bet.empty:

                    st.warning(
                        "Duplicate bet detected. Bet was not saved."
                    )

                    st.stop()

                updated_bets_df = pd.concat(
                    [existing_bets_df, new_bet_row],
                    ignore_index=True
                )

            else:

                updated_bets_df = new_bet_row

            updated_bets_df.to_csv(
                bets_path,
                index=False
            )

            st.success("Bet recorded successfully.")
            st.rerun()

if not lineups_df.empty and players_df is not None:

    normalized_players_df = players_df.copy()

    normalized_players_df["player_normalized"] = normalized_players_df["player"].apply(
        lambda x: x.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
    )

    lineups_df["player_normalized"] = lineups_df["player"].apply(
        lambda x: x.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
    )

    missing_lineup_players = lineups_df[
        ~lineups_df["player_normalized"].isin(
            normalized_players_df["player_normalized"]
        )
    ]

    if not missing_lineup_players.empty:

        st.warning(
            "Some lineup players were not found in NBA stats."
        )

        st.dataframe(
            missing_lineup_players,
            width="stretch"
        )
        
        if lineup_provider_mode == "External CSV URL" and external_lineup_url:

            update_source_grading(
                source_name=external_lineup_url,
                success=True,
                player_count=len(lineups_df),
                duplicate_count=0,
                missing_players=len(missing_lineup_players)
            )
    

# ---------------------------------
# MODEL TRACKING
# ---------------------------------

# ---------------------------------
# PENDING PICKS
# ---------------------------------
if os.path.exists(results_path):

    pending_df = results_df[
        results_df["correct_pick"].isna()
        |
        (results_df["correct_pick"] == "")
    ].copy()

    pending_df = pending_df[
        pending_df["model_decision"] != "Unknown"
    ]

    stale_pending = pd.DataFrame()

    if show_operations and not pending_df.empty:

        if "model_version" in pending_df.columns:

            stale_pending = pending_df[
                pending_df["model_version"] != MODEL_VERSION
            ]

        if (
            "schedule_source" not in pending_df.columns
            or
            "schedule_trust_score" not in pending_df.columns
        ):

            st.warning(
                "Some pending picks were created before schedule trust tracking was available."
            )

        if not stale_pending.empty:

            st.warning(
                "Some pending picks were created under older model versions and may not match current model logic."
            )

        with st.expander("Pending Model Picks", expanded=False):

            st.dataframe(

                pending_df[[

                    "date_saved",
                    "model_version",
                    "schedule_source",
                    "schedule_trust_score",
                    "slate_verified",
                    "matchup",
                    "player",
                    "team",
                    "probability",
                    "odds",
                    "confidence",
                    "edge_tier",
                    "model_decision"

                ]],

                width="stretch"

            )    

# ---------------------------------
# MANUAL FIRST POINT GRADING
# ---------------------------------
if os.path.exists(results_path):

    grading_df = pd.read_csv(results_path)

    grading_df["actual_first_basket"] = grading_df["actual_first_basket"].astype("object")
    grading_df["correct_pick"] = grading_df["correct_pick"].astype("object")
    grading_df["date_completed"] = grading_df["date_completed"].astype("object")
    grading_df["profit_loss"] = grading_df["profit_loss"].astype("object")
    
    pending_to_grade = grading_df[
        grading_df["correct_pick"].isna()
        |
        (grading_df["correct_pick"] == "")
    ]

    if show_operations and not pending_to_grade.empty:

        st.subheader("Grade Pending Picks")

        pick_options = pending_to_grade.index.tolist()

        selected_index = st.selectbox(
            "Select Pending Pick",
            pick_options,
            format_func=lambda i: (
                f"{grading_df.loc[i, 'matchup']} - "
                f"{grading_df.loc[i, 'player']}"
            )
        )

        actual_first_scorer = st.text_input(
            "Actual First Scorer"
        )

        if st.button("Save Pick Result"):

            projected_player = grading_df.loc[selected_index, "player"]

            is_correct = (
                actual_first_scorer.strip().lower()
                ==
                str(projected_player).strip().lower()
            )

            grading_df.loc[selected_index, "actual_first_basket"] = actual_first_scorer
            grading_df.loc[selected_index, "correct_pick"] = "Yes" if is_correct else "No"
            grading_df.loc[selected_index, "date_completed"] = pd.Timestamp.now().strftime("%Y-%m-%d")

            if is_correct:
                odds = grading_df.loc[selected_index, "odds"]
                grading_df.loc[selected_index, "profit_loss"] = round(odds / 100, 2)
            else:
                grading_df.loc[selected_index, "profit_loss"] = -1

            grading_df.to_csv(results_path, index=False)

            st.success("Pick result recorded successfully.")
            st.rerun()

# ---------------------------------
# PROVIDER DIAGNOSTICS
# ---------------------------------

# ---------------------------------
# SOURCE GRADING DASHBOARD
# ---------------------------------
source_grades_path = "results/source_grades.json"

if show_operations and os.path.exists(source_grades_path):

    with st.expander("Provider:", expanded=False):

        st.subheader("Provider:")

        source_grades_df = pd.read_json(source_grades_path).T.reset_index()

        source_grades_df = source_grades_df.rename(
            columns={
                "index": "source_name"
            }
        )

    source_grades_df["average_player_count"] = source_grades_df[
        "avg_player_count"
    ].apply(
        lambda x: round(sum(x) / len(x), 1) if len(x) > 0 else 0
    )

    
    source_grades_df["success_rate"] = (
        (
            source_grades_df["successful_refreshes"]
            / source_grades_df["total_refreshes"]
        ) * 100
    ).round(1)
    
    source_grades_df["reliability_score"] = (
        source_grades_df["success_rate"]
        -
        (source_grades_df["duplicate_issues"] * 5)
        -
        (source_grades_df["missing_players"] * 3)
    ).clip(lower=0, upper=100).round(1)
    
    def source_quality_label(score):

        if score >= 90:
            return "🔥 Excellent"

        elif score >= 75:
            return "✅ Reliable"

        elif score >= 50:
            return "⚠️ Monitor"

        return "❌ Reject"


    source_grades_df["source_quality"] = source_grades_df[
        "reliability_score"
    ].apply(source_quality_label)
    
    def provider_recommendation(score):

        if score >= 90:
            return "🔥 Preferred"

        elif score >= 75:
            return "✅ Usable"

        elif score >= 50:
            return "⚠️ Monitor"

        return "❌ Reject"

    source_grades_df["provider_recommendation"] = source_grades_df[
        "reliability_score"
    ].apply(provider_recommendation)
    
    source_grades_df["provider_status"] = source_grades_df[
        "reliability_score"
    ].apply(
        lambda score: "Rejected" if score < 50 else "Active"
    )
    
    source_grades_df["automation_ready"] = source_grades_df[
        "reliability_score"
    ].apply(
        lambda score: "Yes" if score >= 75 else "No"
    )
    
    active_providers_df = source_grades_df[
        source_grades_df["provider_status"] == "Active"
    ]

    if not active_providers_df.empty:

        best_provider = active_providers_df.sort_values(
            "reliability_score",
            ascending=False
        ).iloc[0]

        st.success(
            f"🔥 Best Provider: {best_provider['source_name']} "
            f"({best_provider['provider_recommendation']})"
        )

        recommended_provider_url = best_provider["source_name"]

        st.session_state["recommended_provider_url"] = recommended_provider_url

        st.caption(
            f"Rotation Candidate: {recommended_provider_url}"
        )

        if best_provider["reliability_score"] >= 75:

            st.success(
                "Rotation Status: Ready"
            )

        else:

            st.warning(
                "Rotation Status: Manual Review Recommended"
            )

        if best_provider["reliability_score"] >= 75:

            if st.button("Use Best Provider"):

                refreshed = refresh_lineups_from_external_csv(
                    recommended_provider_url
                )

                if refreshed:

                    st.session_state["last_lineup_refresh"] = "Success"
                    st.session_state["last_lineup_refresh_time"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["last_lineup_source"] = recommended_provider_url
                    st.session_state["last_lineup_count"] = len(
                        pd.read_csv("data/today_lineups.csv")
                    )

                    st.success(
                        "Best provider refresh completed successfully."
                    )

                    st.rerun()

                else:

                    st.session_state["last_lineup_refresh"] = "Failed"

                    st.error(
                        "Best provider refresh failed. Manual review required."
                    )

    else:

        best_provider = None

        st.error(
            "No active lineup providers available. All tracked providers are rejected."
        )
    
    if (
        best_provider is not None
        and best_provider["reliability_score"] < 50
    ):

        st.warning(
            "⚠️ Current best provider is below safe reliability standards. "
            "Consider replacing lineup source."
        )
                
    rejected_providers = source_grades_df[
        source_grades_df["provider_status"] == "Rejected"
    ]

    if not rejected_providers.empty:

        st.error(
            f"Rejected Providers: {len(rejected_providers)}"
        )

        st.dataframe(
            rejected_providers[[
                "source_name",
                "reliability_score",
                "provider_recommendation",
                "duplicate_issues",
                "missing_players"
            ]],
            width="stretch"
        )
    
    if (
        lineup_provider_mode == "External CSV URL"
        and external_lineup_url
        and external_lineup_url in rejected_providers["source_name"].tolist()
    ):

        st.error(
            "Selected lineup provider is currently rejected. "
            "Do not use this provider until reliability improves."
        )
    
    active_provider_count = len(
        source_grades_df[
            source_grades_df["provider_status"] == "Active"
        ]
    )

    rejected_provider_count = len(
        source_grades_df[
            source_grades_df["provider_status"] == "Rejected"
        ]
    )

    automation_ready_count = len(
        source_grades_df[
            source_grades_df["automation_ready"] == "Yes"
        ]
    )
    
    st.caption(
        f"Provider Summary: {active_provider_count} Active / {rejected_provider_count} Rejected"
    )
    
    st.caption(
        f"Automation Ready Providers: {automation_ready_count}"
    )
    
    automation_ready_df = source_grades_df[
        source_grades_df["automation_ready"] == "Yes"
    ]

    if not automation_ready_df.empty:

        best_automation_provider = automation_ready_df.sort_values(
            "reliability_score",
            ascending=False
        ).iloc[0]

        st.success(
            f"Best Auto Provider: {best_automation_provider['source_name']}"
        )

    else:

        st.warning(
            "No providers are currently automation ready."
        )
    
    if automation_ready_count > 0:

        st.success(
            "Automation Status: Ready"
        )

    else:

        st.warning(
            "Automation Status: Not Ready"
        )
    
    if not automation_ready_df.empty:

        st.dataframe(
            automation_ready_df[[
                "source_name",
                "reliability_score",
                "success_rate",
                "provider_recommendation"
            ]],
            width="stretch"
        )
    
    st.caption(
        f"Tracked Providers: {len(source_grades_df)}"
    )
     
    if best_provider is not None and best_provider["reliability_score"] >= 75:

        st.caption(
            "Provider Status: Healthy"
        )

    else:

        st.caption(
            "Provider Status: Needs Review"
        )
       
    st.dataframe(
        source_grades_df[[
            "source_name",
            "provider_status",
            "automation_ready",
            "total_refreshes",
            "successful_refreshes",
            "failed_refreshes",
            "success_rate",
            "reliability_score",
            "source_quality",
            "provider_recommendation",
            "average_player_count",
            "duplicate_issues",
            "missing_players"
        ]],
        width="stretch"
    )
                       
st.divider()

# ---------------------------------
# PERFORMANCE ANALYTICS
# ---------------------------------

if show_operations:

    with st.expander("Model Performance", expanded=False):
        
        st.markdown("#### Model Decision Performance")
        
        # ---------------------------------
        # MODEL DECISION PERFORMANCE
        # ---------------------------------

        if "model_decision" in results_df.columns:
                    
            results_df["model_decision"] = results_df[
                    "model_decision"
            ].fillna("Unknown")
                        
            completed_decisions = results_df[
                results_df["correct_pick"].isin(["Yes", "No"])
            ]

            if not completed_decisions.empty:

                st.subheader("Model Decision Performance")

                decision_summary = (

                    completed_decisions.groupby("model_decision")

                    .apply(

                        lambda x: pd.Series({

                            "Total Picks": len(x),

                            "Wins": len(
                                x[x["correct_pick"] == "Yes"]
                            ),

                            "Accuracy %": round(
                                (
                                    len(
                                        x[x["correct_pick"] == "Yes"]
                                    ) / len(x)
                                ) * 100,
                                1
                            ),

                            "Profit/Loss": round(
                                pd.to_numeric(
                                    x["profit_loss"],
                                    errors="coerce"
                                ).fillna(0).sum(),
                                2
                            ),

                            "ROI %": round(
                                (
                                    pd.to_numeric(
                                        x["profit_loss"],
                                        errors="coerce"
                                    ).fillna(0).sum()
                                    / len(x)
                                ) * 100,
                                1
                            )

                        })

                    )

                    .reset_index()

                )

                st.dataframe(
                    decision_summary,
                    width="stretch"
                ) 
            
            
        # ---------------------------------
        # CONFIDENCE TIER PERFORMANCE
        # ---------------------------------
        completed_results = results_df[
            results_df["correct_pick"].isin(["Yes", "No"])
        ]

        if not completed_results.empty:

            st.subheader("Confidence Tier Performance")

            tier_summary = (

                completed_results.groupby("confidence")

                .apply(

                    lambda x: pd.Series({

                        "Total Picks": len(x),

                        "Wins": len(
                            x[x["correct_pick"] == "Yes"]
                        ),

                        "Accuracy %": round(
                            (
                                len(
                                    x[x["correct_pick"] == "Yes"]
                                ) / len(x)
                            ) * 100,
                            1
                        ),

                        "Profit/Loss": round(
                            pd.to_numeric(
                                x["profit_loss"],
                                errors="coerce"
                            ).fillna(0).sum(),
                            2
                        ),

                        "ROI %": round(
                            (
                                pd.to_numeric(
                                    x["profit_loss"],
                                    errors="coerce"
                                ).fillna(0).sum()
                                / len(x)
                            ) * 100,
                            1
                        )

                    })

                )

                .reset_index()

            )

            st.dataframe(
                tier_summary,
                width="stretch"
            )
            
        # ---------------------------------
        # EDGE TIER PERFORMANCE
        # ---------------------------------
        if os.path.exists(results_path):

            completed_edge = results_df[
                results_df["correct_pick"].isin(["Yes", "No"])
            ]

            if not completed_edge.empty:

                st.subheader("Edge Tier Performance")

                edge_summary = (

                    completed_edge.groupby("edge_tier")

                    .apply(

                        lambda x: pd.Series({

                            "Total Picks": len(x),

                            "Wins": len(
                                x[x["correct_pick"] == "Yes"]
                            ),

                            "Accuracy %": round(
                                (
                                    len(
                                        x[x["correct_pick"] == "Yes"]
                                    ) / len(x)
                                ) * 100,
                                1
                            ),

                            "Profit/Loss": round(
                                pd.to_numeric(
                                    x["profit_loss"],
                                    errors="coerce"
                                ).fillna(0).sum(),
                                2
                            ),

                            "ROI %": round(
                                (
                                    pd.to_numeric(
                                        x["profit_loss"],
                                        errors="coerce"
                                    ).fillna(0).sum()
                                    / len(x)
                                ) * 100,
                                1
                            )

                        })

                    )

                    .reset_index()

                )

                st.dataframe(
                    edge_summary,
                    width="stretch"
                )    

        # ---------------------------------
        # BEST BET PERFORMANCE
        # ---------------------------------
        if os.path.exists(results_path):

            best_bet_df = results_df[
                results_df["correct_pick"].isin(["Yes", "No"])
            ]

            if not best_bet_df.empty:

                best_bet_wins = len(
                    best_bet_df[
                        best_bet_df["correct_pick"] == "Yes"
                    ]
                )

                best_bet_total = len(best_bet_df)

                best_bet_accuracy = round(
                    (best_bet_wins / best_bet_total) * 100,
                    1
                )

                best_bet_profit = round(
                    pd.to_numeric(
                        best_bet_df["profit_loss"],
                        errors="coerce"
                    ).fillna(0).sum(),
                    2
                )

                best_bet_roi = round(
                    (best_bet_profit / best_bet_total) * 100,
                    1
                )

                st.subheader("Best Bet Performance")

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Best Bet Accuracy",
                    f"{best_bet_accuracy}%"
                )

                col2.metric(
                    "Best Bet Profit/Loss",
                    best_bet_profit
                )

                col3.metric(
                    "Best Bet Total Picks",
                    best_bet_total
                )

                col4.metric(
                    "Best Bet ROI %",
                    f"{best_bet_roi}%"
                )


# ---------------------------------
# CORE SCORING MODEL
# ---------------------------------

# ---------------------------------
# TIP WINNERS
# ---------------------------------
tip_winners = {
    "DET_vs_CLE": "CLE",
    "OKC_vs_LAL": "LAL"
}

# ---------------------------------
# TEAM PACE
# ---------------------------------
team_pace = {

    "IND": 1.08,
    "ATL": 1.06,
    "OKC": 1.05,
    "MIN": 1.04,
    "SAS": 1.03,
    "NYK": 0.98,
    "PHI": 0.97

}

# ---------------------------------
# PROJECTED STARTERS
# ---------------------------------
projected_starters = {

    "PHI": [
        "Tyrese Maxey",
        "Joel Embiid"
    ],

    "NYK": [
        "Jalen Brunson",
        "Karl-Anthony Towns"
    ],

    "MIN": [
        "Anthony Edwards",
        "Julius Randle"
    ],

    "SAS": [
        "Victor Wembanyama",
        "Devin Vassell"
    ]

}


# ---------------------------------
# FALLBACK PLAYER PROFILE
# ---------------------------------
def get_fallback_profile(player):

    high_usage_players = [
        "Anthony Edwards",
        "Julius Randle",
        "Victor Wembanyama",
        "De'Aaron Fox",
        "Devin Vassell"
    ]

    starter_role_players = [
        "Rudy Gobert",
        "Jaden McDaniels",
        "Mike Conley",
        "Keldon Johnson",
        "Jeremy Sochan"
    ]

    if player in high_usage_players:

        return {
            "minutes": 32,
            "fga": 15,
            "points": 22
        }

    if player in starter_role_players:

        return {
            "minutes": 26,
            "fga": 8,
            "points": 11
        }

    return {
        "minutes": 24,
        "fga": 7,
        "points": 10
    }

# ---------------------------------
# DYNAMIC STARTER ESTIMATOR
# ---------------------------------
def get_dynamic_starters(players_df, team):

    if not lineups_df.empty:

        team_lineups = lineups_df[
            lineups_df["team"] == team
        ].copy()

        team_lineups = team_lineups[
            team_lineups["status"].isin(["Projected", "Confirmed"])
        ]

        if not team_lineups.empty:
            return team_lineups["player"].tolist()

    team_players = players_df[
        players_df["team"] == team
    ].copy()

    team_players = team_players.dropna(
        subset=["player", "minutes", "fga"]
    )

    if team_players.empty:
        return projected_starters.get(team, [])

    team_players = team_players.sort_values(
        ["minutes", "fga"],
        ascending=False
    )

    return team_players["player"].head(5).tolist()

# ---------------------------------
# PRIMARY SCORING OPTIONS
# ---------------------------------
primary_options = {

    "PHI": [
        "Tyrese Maxey",
        "Joel Embiid"
    ],

    "NYK": [
        "Jalen Brunson",
        "Karl-Anthony Towns"
    ],

    "MIN": [
        "Anthony Edwards",
        "Julius Randle"
    ],

    "SAS": [
        "De'Aaron Fox",
        "Victor Wembanyama"
    ]

}

# ---------------------------------
# BIG MEN / TIP TARGETS
# ---------------------------------
big_men = {

    "PHI": [
        "Joel Embiid"
    ],

    "NYK": [
        "Karl-Anthony Towns"
    ],

    "MIN": [
        "Julius Randle"
    ],

    "SAS": [
        "Victor Wembanyama"
    ]

}

# ---------------------------------
# FIRST SHOT TEAM BIAS
# ---------------------------------
team_first_shot_bias = {

    "PHI": 1.08,
    "NYK": 1.04,
    "MIN": 1.06,
    "SAS": 1.02

}

# ---------------------------------
# SAFETY CHECK
# ---------------------------------
if players_df is None:

    st.error("Player stats failed to load. Model cannot proceed.")
    st.stop()

st.divider()

if show_operations:

    if data_mode == "LIVE_SCOREBOARD":

        st.success(
            "Matchup projections are using live NBA scoreboard data."
        )

    elif data_mode == "SECONDARY_LIVE_SCHEDULE":

        st.success(
            "Matchup projections are using secondary live schedule data."
        )

        st.caption(
            "Primary scoreboard was unavailable, but fallback schedule was not needed."
        )

    else:

        st.warning(
            "Matchup projections are using fallback schedule data. Verify today’s slate before placing bets."
        )

slate_verified_label = (
    "✅ Passed"
    if slate_verified
    else "⚠️ Needs Review"
)

# ---------------------------------
# LIVE MATCHUP ENGINE
# ---------------------------------

st.header("Today's Matchups")

# ---------------------------------
# DISPLAY GAMES
# ---------------------------------
for game in games:

    away = game["away"]
    home = game["home"]
    game_id = game.get("game_id")
    matchup_key = f"{away}_vs_{home}"

    projected_tip = tip_winners.get(
        matchup_key,
        away
    )

    with st.expander(
        f"{away} vs {home}",
        expanded=False
    ):

        st.caption(
            f"Projected Tip Winner: {projected_tip}"
    )

        if game_id:
            st.caption(f"NBA Game ID: {game_id}")
        else:
            st.caption("Game ID: Unavailable")

        # ---------------------------------
        # FILTER PLAYERS
        # ---------------------------------
        game_players = players_df[
            players_df["team"].isin([away, home])
        ].copy()
        
        game_players["data_source"] = "Real Stats"
        
        game_players["lineup_status"] = "Stat Derived"
        
        game_players = game_players.dropna(
            subset=["player", "team"]
        )

        game_players = game_players.drop_duplicates(
            subset=["player"]
        )

        game_players["player_normalized"] = game_players["player"].apply(
            lambda x: str(x).strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
        )
        
        if lineups_df.empty:

            game_players = game_players[
                game_players["minutes"] >= 20
            ]

        if not lineups_df.empty:

            active_lineups = lineups_df[
                lineups_df["team"].isin([away, home])
            ].copy()

            active_lineups["player_normalized"] = active_lineups["player"].apply(
                lambda x: x.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
            )

            game_players["player_normalized"] = game_players["player"].apply(
                lambda x: x.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
            )

            active_lineup_players = active_lineups["player_normalized"].tolist()

            game_players = game_players[
                game_players["player_normalized"].isin(active_lineup_players)
            ].copy()

            missing_players = active_lineups[
                ~active_lineups["player_normalized"].isin(
                    game_players["player_normalized"]
                )
            ].copy()

            if not missing_players.empty:

                fallback_rows = []

                for _, missing_player in missing_players.iterrows():

                    profile = get_fallback_profile(
                        missing_player["player"]
                    )

                    fallback_rows.append({

                        "player": missing_player["player"],
                        "team": missing_player["team"],
                        "minutes": profile["minutes"],
                        "fga": profile["fga"],
                        "points": profile["points"],
                        "data_source": "Fallback Stats",
                        "lineup_status": missing_player["status"]
                        
                    })


                fallback_df = pd.DataFrame(fallback_rows)

                game_players = pd.concat(
                    [game_players, fallback_df],
                    ignore_index=True
                )

        if game_players.empty:

            st.warning("No players found.")
            continue

        # ---------------------------------
        # DYNAMIC PLAYER POOL FILTER
        # ---------------------------------
        game_players["usage_score"] = (
            game_players["fga"]
            +
            (game_players["points"] * 0.5)
        ) / game_players["minutes"]

        team_pool_cutoff = game_players.groupby("team")["minutes"].transform(
            lambda x: x.quantile(0.55)
        )

        game_players = game_players[

            (
                game_players["minutes"] >= team_pool_cutoff
            )

            |

            (
                game_players["usage_score"] >= game_players["usage_score"].quantile(0.65)
            )

            |

            (
                game_players["player_normalized"].isin(active_lineup_players)
                if not lineups_df.empty
                else False
            )

        ].copy()
            
        # ---------------------------------
        # NORMALIZE STATS
        # ---------------------------------
        game_players["minutes_norm"] = (
            game_players["minutes"]
            / game_players["minutes"].max()
        )

        game_players["fga_norm"] = (
            game_players["fga"]
            / game_players["fga"].max()
        )

        game_players["points_norm"] = (
            game_players["points"]
            / game_players["points"].max()
        )
        
        # ---------------------------------
        # USAGE CREATION
        # ---------------------------------
        game_players["usage_creation"] = (

            game_players["fga"]

            +

            (game_players["points"] * 0.5)

        ) / game_players["minutes"]

        game_players["usage_creation_norm"] = (

            game_players["usage_creation"]

            /

            game_players["usage_creation"].max()

        )
        
        # ---------------------------------
        # SHOOTING EFFICIENCY
        # ---------------------------------
        game_players["fg_pct"] = (

            game_players["points"]

            /

            (game_players["fga"] * 2)

        ).clip(lower=0, upper=1)

        game_players["fg_pct_norm"] = (

            game_players["fg_pct"]

            /

            game_players["fg_pct"].max()

        )

        # ---------------------------------
        # TEAM SHARE METRICS
        # ---------------------------------
        game_players["fga_share"] = (
            game_players["fga"]
            / game_players.groupby("team")["fga"].transform("sum")
        )

        game_players["points_share"] = (
            game_players["points"]
            / game_players.groupby("team")["points"].transform("sum")
        )

        # ---------------------------------
        # FIRST SHOT SCORE
        # ---------------------------------
        game_players["first_shot_score"] = (
            (game_players["fga_share"] * 0.7)
            +
            (game_players["fga_norm"] * 0.3)
        )

        # ---------------------------------
        # STAR POWER
        # ---------------------------------
        game_players["star_score"] = (
            (game_players["points_share"] * 0.6)
            +
            (game_players["fga_share"] * 0.4)
        )

        # ---------------------------------
        # EARLY GAME AGGRESSION
        # ---------------------------------
        game_players["early_game_boost"] = (

            game_players["points"]
            /
            game_players["minutes"]

        ).fillna(0)
        
        # ---------------------------------
        # BOOSTS
        # ---------------------------------
        game_players["home_boost"] = game_players["team"].apply(
            lambda x: 1 if x == home else 0
        )

        game_players["tip_boost"] = game_players["team"].apply(
            lambda x: 1 if x == projected_tip else 0
        )

        # ---------------------------------
        # FIRST POSSESSION PRIORITY
        # ---------------------------------
        game_players["first_possession_boost"] = game_players.apply(

            lambda row:

            1.25

            if (
                row["team"] == projected_tip
                and row["player_normalized"] in [
                    option.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
                    for option in primary_options.get(row["team"], [])
                ]
            )

            else 1,

            axis=1

        )
                
        game_players["pace_boost"] = game_players["team"].map(
            team_pace
        ).fillna(1.0)

        game_players["starter_boost"] = game_players.apply(
            lambda row: 1
            if row["player_normalized"] in [
                starter.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
                for starter in get_dynamic_starters(players_df, row["team"])
            ]
            else 0,
            axis=1
        )

        # ---------------------------------
        # PRIMARY OPTION BOOST
        # ---------------------------------
        game_players["primary_option_boost"] = game_players.apply(

            lambda row: 1

            if row["player_normalized"] in [
                option.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
                for option in primary_options.get(row["team"], [])
            ]

            else 0,

            axis=1

        )
        
        # ---------------------------------
        # BIG MAN FIRST POSSESSION BOOST
        # ---------------------------------
        game_players["big_man_boost"] = game_players.apply(

            lambda row: 1

            if row["player_normalized"] in [
                big.strip().lower().replace("'", "").replace("’", "").replace("-", " ").replace(".", "").replace(",", "")
                for big in big_men.get(row["team"], [])
            ]

            else 0,

            axis=1

        )
        
        game_players["team_first_shot_boost"] = game_players["team"].map(
            team_first_shot_bias
        ).fillna(1.0)

        # ---------------------------------
        # FINAL MODEL SCORE
        # ---------------------------------
        game_players["score"] = (

            (game_players["minutes_norm"] * 0.10)

            +

            (game_players["fga_norm"] * 0.28)

            +

            (game_players["points_norm"] * 0.08)

            +

            (game_players["first_shot_score"] * 0.40)

            +

            (game_players["star_score"] * 0.26)
            
            +

            (game_players["early_game_boost"] * 0.12)
            
            +

            (game_players["usage_creation_norm"] * 0.14)
            
            +

            (game_players["fg_pct_norm"] * 0.08)

            +

            (game_players["home_boost"] * 0.03)

            +

            (game_players["tip_boost"] * 0.015)
            
            +

            (game_players["first_possession_boost"] * 0.06)

            +

            (game_players["pace_boost"] * 0.02)

            +

            (game_players["starter_boost"] * 0.04)
            
            +

            (game_players["primary_option_boost"] * 0.08)
            
            +

            (game_players["big_man_boost"] * 0.07)

            +

            (game_players["team_first_shot_boost"] * 0.02)

        )

        # ---------------------------------
        # ADJUSTED SCORE
        # ---------------------------------
        game_players["adjusted_score"] = (
            game_players["score"] ** 1.50
        )

        total_score = game_players["adjusted_score"].sum()

        game_players["probability"] = (
            game_players["adjusted_score"]
            / total_score
        ) * 100

        game_players["probability"] = (
            game_players["probability"]
        ).round(1)

        # ---------------------------------
        # ODDS
        # ---------------------------------
        game_players["odds"] = game_players["probability"].apply(
            probability_to_american
        )

        game_players["decimal_odds"] = (

            (game_players["odds"] / 100) + 1

        ).round(2)
        
        # ---------------------------------
        # IMPLIED PROBABILITY
        # ---------------------------------
        game_players["implied_probability"] = game_players["odds"].apply(
            lambda x:
            american_to_probability(x)
            if pd.notnull(x)
            else None
        )

        # ---------------------------------
        # EDGE
        # ---------------------------------
        game_players["edge"] = (
            (game_players["probability"] / 100)
            -
            game_players["implied_probability"]
        )

        game_players["implied_probability"] = (
            game_players["implied_probability"] * 100
        ).round(1)

        game_players["edge"] = (
            game_players["edge"] * 100
        ).round(1)
        
        # ---------------------------------
        # EDGE TIER
        # ---------------------------------
        def edge_label(edge):

            if edge >= 3:
                return "🔥 High Value"

            elif edge >= 1.5:
                return "✅ Solid"

            elif edge >= 0.5:
                return "⚠️ Thin"

            return "❌ No Edge"


        game_players["edge_tier"] = game_players["edge"].apply(
            edge_label
        )

        # ---------------------------------
        # CONFIDENCE
        # ---------------------------------

        game_players["confidence_score"] = (

            (game_players["probability"] * 0.65)

            +

            (game_players["first_shot_score"] * 100 * 0.20)

            +

            (game_players["tip_boost"] * 8)

            +

            (game_players["starter_boost"] * 6)

            +

            (game_players["pace_boost"] * 4)

        )

        schedule_confidence_multiplier = max(
            0.65,
            schedule_trust_score / 100
        )

        game_players["confidence_score"] = (
            game_players["confidence_score"]
            * schedule_confidence_multiplier
        ).round(1)


        game_players["schedule_risk_flag"] = game_players["confidence_score"].apply(
            lambda x: "⚠️ Schedule Risk"
            if schedule_confidence_multiplier < 0.85
            else "Normal"
        )

        def confidence_label(score):

            if score >= 38:
                return "🔥 Elite"

            elif score >= 32:
                return "✅ Strong"

            elif score >= 25:
                return "⚠️ Decent"

            return "❌ Fade"


        game_players["confidence"] = game_players["confidence_score"].apply(
            confidence_label
        )

        def recommended_units(score):

            if score >= 38:
                return "2 Units"

            elif score >= 32:
                return "1.5 Units"

            elif score >= 25:
                return "1 Unit"

            return "0.5 Unit"


        game_players["recommended_units"] = game_players[
            "confidence_score"
        ].apply(recommended_units)
        
        # ---------------------------------
        # MODEL DECISION FILTER
        # ---------------------------------
        def model_decision(row):

            if (
                row["confidence_score"] >= 38
                and row["edge"] >= 1.5
            ):
                return "🔥 PLAY"

            elif (
                row["confidence_score"] >= 32
                and row["edge"] >= 0.5
            ):
                return "✅ LEAN"

            return "⛔ PASS"


        game_players["model_decision"] = game_players.apply(
            model_decision,
            axis=1
        )
        
        # ---------------------------------
        # SORT
        # ---------------------------------
        game_players = game_players.sort_values(
            "confidence_score",
            ascending=False
        )

        # ---------------------------------
        # BEST BET
        # ---------------------------------
        best_bet = game_players.iloc[0]       

        # ---------------------------------
        # SAVE PREDICTION
        # ---------------------------------
        prediction_row = pd.DataFrame([{

            "date_saved": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "model_version": MODEL_VERSION,
            "schedule_source": data_mode,
            "schedule_trust_score": schedule_trust_score,
            "slate_verified": slate_verified,
            "matchup": f"{away} vs {home}",
            "projected_tip_winner": projected_tip,
            "player": best_bet["player"],
            "team": best_bet["team"],
            "probability": best_bet["probability"],
            "odds": best_bet["odds"],
            "confidence_score": best_bet["confidence_score"],
            "confidence": best_bet["confidence"],
            "edge_tier": best_bet["edge_tier"],
            "model_decision": best_bet["model_decision"],
            
            "actual_first_basket": "",
            "correct_pick": "",
            "profit_loss": "",
            "date_completed": ""

        }])

        results_path = "results/first_basket_results.csv"

        if os.path.exists(results_path):

            existing_df = pd.read_csv(results_path)

            existing_df["date_saved"] = existing_df["date_saved"].astype(str)
            existing_df["matchup"] = existing_df["matchup"].astype(str)

            today_str = pd.Timestamp.now().strftime("%Y-%m-%d")

            already_saved = (
                (existing_df["matchup"] == f"{away} vs {home}")
                &
                (existing_df["date_saved"] == today_str)
            ).any()

            if not already_saved:

                prediction_row.to_csv(
                    results_path,
                    mode="a",
                    header=False,
                    index=False
                )

        else:

            prediction_row.to_csv(
                results_path,
                index=False
            )
                
        # ---------------------------------
        # DISPLAY BEST BET
        # ---------------------------------
        st.markdown(f"""

        ### 🏀 Best Model Play

        | Metric | Value |
        |---|---|
        | Model Version | {MODEL_VERSION} |
        | Player | **{best_bet['player']}** |
        | Team | {best_bet['team']} |
        | Probability | {best_bet['probability']}% |
        | Odds | +{int(best_bet['odds'])} |
        | Decimal Odds | {best_bet['decimal_odds']} |
        | Edge | {best_bet['edge']}% |
        | Edge Tier | {best_bet['edge_tier']} |
        | Confidence Score | {best_bet['confidence_score']} |
        | Schedule Trust Multiplier | {round(schedule_confidence_multiplier, 2)} |
        | Daily Slate Verified | {slate_verified_label} |
        | Confidence Tier | {best_bet['confidence']} |
        | Recommended Units | {best_bet['recommended_units']} |
        | Model Decision | {best_bet['model_decision']} |
        | Schedule Risk | {best_bet['schedule_risk_flag']} |

        """)


        # ---------------------------------
        # AWAY TEAM TOP 2
        # ---------------------------------
        with st.expander(f"{away} Top 2 Candidates", expanded=False):

            away_players = game_players[
                game_players["team"] == away
                ].sort_values(
                    "probability",
                    ascending=False
                ).head(2)

            st.dataframe(

                away_players[[

                    "player",
                    "data_source",
                    "lineup_status",
                    "probability",
                    "odds",
                    "decimal_odds",
                    "confidence_score",
                    "confidence",
                    "edge_tier",
                    "model_decision",
                    "schedule_risk_flag"

                ]],

                width="stretch"

            )

        # ---------------------------------
        # HOME TEAM TOP 2
        # ---------------------------------
        with st.expander(f"{home} Top 2 Candidates", expanded=False):

            home_players = game_players[
                game_players["team"] == home
                ].sort_values(
                    "probability",
                    ascending=False
                ).head(2)

            st.dataframe(

                home_players[[

                    "player",
                    "data_source",
                    "lineup_status",
                    "probability",
                    "odds",
                    "decimal_odds",
                    "confidence_score",
                    "confidence",
                    "edge_tier",
                    "model_decision",
                    "schedule_risk_flag"
                    
                ]],

                width="stretch"

            )
        
        # ---------------------------------
        # FULL MATCHUP RANKINGS
        # ---------------------------------
        with st.expander("Full Matchup Rankings", expanded=False):

            st.dataframe(

                game_players[[

                    "player",
                    "team",
                    "data_source",
                    "lineup_status",
                    "probability",
                    "odds",
                    "decimal_odds",
                    "confidence_score",
                    "confidence",
                    "edge_tier",
                    "model_decision",
                    "schedule_risk_flag"
                    
                ]],

                width="stretch"
            )
                
        st.divider()
