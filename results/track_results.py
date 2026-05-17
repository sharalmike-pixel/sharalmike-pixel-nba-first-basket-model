import pandas as pd

# LOAD CSV
df = pd.read_csv(
    "results/first_basket_results.csv",
    dtype=str
)

# FILL EMPTY VALUES
df = df.fillna("")

# LOOP THROUGH PREDICTIONS
for idx, row in df.iterrows():

    # SKIP COMPLETED ROWS
    if row["correct_pick"] in ["Yes", "No"]:
        continue

    print("\n-------------------------")
    print(f"Game: {row['matchup']}")
    print(f"Predicted: {row['predicted_player']} ({row['predicted_team']})")

    actual = input("Actual first basket scorer: ")

    # SAVE RESULT
    df.at[idx, "actual_first_basket"] = actual

    if actual.lower() == row["predicted_player"].lower():

        df.at[idx, "correct_pick"] = "Yes"

        print("✅ CORRECT PICK")

    else:

        df.at[idx, "correct_pick"] = "No"

        print("❌ WRONG PICK")

    # SAVE UPDATED CSV
df.to_csv("results/first_basket_results.csv", index=False)

# -------------------------
# PERFORMANCE SUMMARY
# -------------------------

total_tracked = len(

    df[df["correct_pick"].isin(["Yes", "No"])]

)

wins = len(

    df[df["correct_pick"] == "Yes"]

)

losses = len(

    df[df["correct_pick"] == "No"]

)

if total_tracked > 0:

    accuracy = round(

        (wins / total_tracked) * 100,
        1

    )

else:

    accuracy = 0

print("\n=========================")
print("MODEL PERFORMANCE")
print("=========================")

print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Accuracy: {accuracy}%")

print("\nResults updated successfully.")