"""Top14 points-by-season app.

How it works
------------
- Expects a local file named `data.csv` at the project root.
- The CSV/TSV must contain at least these columns:
    - season (e.g. "2005-2006")
    - home_team
    - away_team
    - home_score
    - away_score

This app computes, for each season, the team that scored the most TOTAL points
(sum of scores across all matches in that season).

Run locally:
    pip install -r requirements.txt
    streamlit run main.py
"""

from __future__ import annotations

import pathlib
from typing import Tuple

import pandas as pd
import streamlit as st


DATA_PATH = pathlib.Path(__file__).with_name("data.csv")


def _read_matches(path: pathlib.Path) -> pd.DataFrame:
    """Read the dataset (handles both comma and tab separated)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Could not find {path.name} next to main.py. "
            "Place your data.csv file in the repository root (same folder as main.py)."
        )

    # Your sample looks tab-separated, but the file is called data.csv.
    # We try to auto-detect the delimiter.
    df = pd.read_csv(path, sep="\t")

    required = {"season", "home_team", "away_team", "home_score", "away_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            "data.csv is missing required columns: "
            f"{', '.join(sorted(missing))}. Found columns: {', '.join(df.columns)}"
        )

    # Ensure numeric scores
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")

    # Drop rows where we can't compute points
    df = df.dropna(subset=["season", "home_team", "away_team", "home_score", "away_score"])

    return df


def _season_team_points(matches: pd.DataFrame) -> pd.DataFrame:
    """Return points scored per team per season."""
    home = matches[["season", "home_team", "home_score"]].rename(
        columns={"home_team": "team", "home_score": "points"}
    )
    away = matches[["season", "away_team", "away_score"]].rename(
        columns={"away_team": "team", "away_score": "points"}
    )

    points = pd.concat([home, away], ignore_index=True)
    points = (
        points.groupby(["season", "team"], as_index=False)["points"]
        .sum()
        .sort_values(["season", "points", "team"], ascending=[True, False, True])
    )
    return points


def _season_winners(points: pd.DataFrame) -> pd.DataFrame:
    """Return the top-scoring team(s) per season.

    If there's a tie for a season, multiple rows will be returned.
    """
    max_by_season = points.groupby("season")["points"].transform("max")
    winners = points.loc[points["points"].eq(max_by_season)].copy()
    winners = winners.sort_values(["season", "team"], ascending=[True, True])
    return winners


def _pick_single_winner(winners_for_season: pd.DataFrame) -> Tuple[str, float, int]:
    """Pick a display winner for the selected season.

    Returns: (team, points, tie_count)
    """
    if winners_for_season.empty:
        return "", 0.0, 0

    team = str(winners_for_season.iloc[0]["team"])
    points = float(winners_for_season.iloc[0]["points"])
    tie_count = int(len(winners_for_season))
    return team, points, tie_count


st.set_page_config(page_title="Top14 - Points per season", layout="wide")

st.title("Top14: team with the most points scored each season (2005–2023)")
st.caption(
    "This app computes (A) total points scored across all matches in each season."
)

try:
    matches_df = _read_matches(DATA_PATH)
    points_df = _season_team_points(matches_df)
    winners_df = _season_winners(points_df)
except Exception as e:
    st.error(str(e))
    st.stop()

seasons = sorted(winners_df["season"].unique().tolist())

left, right = st.columns([1, 2])

with left:
    season = st.selectbox("Season", seasons, index=len(seasons) - 1 if seasons else 0)

with right:
    season_winners = winners_df[winners_df["season"] == season]
    team, pts, tie_count = _pick_single_winner(season_winners)

    if tie_count <= 1:
        st.metric(label=f"Top scoring team in {season}", value=team, delta=f"{int(pts)} points")
    else:
        st.metric(
            label=f"Top scoring teams in {season} (tie)",
            value=team,
            delta=f"{int(pts)} points (tied with {tie_count - 1} other team(s))",
        )
        st.write("Tied teams:")
        st.dataframe(season_winners[["team", "points"]], use_container_width=True)

st.subheader("Winners by season")
st.dataframe(winners_df, use_container_width=True)

with st.expander("Show points table (all teams)"):
    st.dataframe(points_df, use_container_width=True)
