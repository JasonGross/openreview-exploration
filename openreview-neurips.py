# %%
from functools import cache
from pathlib import Path

import openreview
import pandas as pd
import numpy as np
from tqdm import tqdm

from memoshelve import memoshelve

# %%
cache_dir = Path(".cache")
cache_dir.mkdir(exist_ok=True)
# %%


def fetch_neurips_papers(year=2023):
    # Initialize the client
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")

    with memoshelve(
        client.get_notes,
        filename=cache_dir / "openreview.api.OpenReviewClient.get_notes",
    )() as get_notes:
        client.get_notes = get_notes
        # Search for NeurIPS 2023 submissions
        submissions = list(
            openreview.tools.iterget_notes(
                client,
                invitation=f"NeurIPS.cc/{year}/Conference/-/Submission",
                details="original",
            )
        )

        papers = []
        found = 0
        found_oral = 0
        found_spotlight = 0
        avg_scores = {"Oral": [], "Spotlight": [], "Poster": []}
        with tqdm(submissions, desc="Fetching papers") as pbar:
            for submission in pbar:
                postfix = {
                    "Found": found,
                    "Oral": found_oral,
                    "Spotlight": found_spotlight,
                    "submission #": submission.number,
                }
                for key, avg_scores_here in avg_scores.items():
                    if avg_scores_here:
                        postfix |= {
                            f"{key} Avg Avg Score": sum(avg_scores_here)
                            / len(avg_scores_here),
                            f"{key} Min Avg Score": min(avg_scores_here),
                            f"{key} Max Avg Score": max(avg_scores_here),
                        }
                pbar.set_postfix(postfix)
                # Check if the paper was accepted
                decision_note = client.get_notes(
                    invitation=f"NeurIPS.cc/{year}/Conference/Submission{submission.number}/-/Decision",
                    limit=1,
                )

                if decision_note and "Accept" in decision_note[0].content.get(
                    "decision", {}
                ).get("value", ""):
                    found += 1
                    # Fetch review scores
                    reviews = client.get_notes(
                        invitation=f"NeurIPS.cc/{year}/Conference/Submission{submission.number}/-/Official_Review"
                    )

                    scores = [
                        int(
                            review.content.get("rating", {})
                            .get("value", "0")
                            .split(":")[0]
                        )
                        for review in reviews
                        if "rating" in review.content
                    ]
                    min_score = min(scores) if scores else None
                    avg_score = sum(scores) / len(scores) if scores else None
                    max_score = max(scores) if scores else None
                    median_score = np.median(scores) if scores else None

                    # Determine presentation type
                    decision = (
                        decision_note[0]
                        .content.get("decision", {})
                        .get("value", "Accept (Poster)")
                    )
                    if decision.startswith("Accept ("):
                        decision = decision[len("Accept (") :]
                    if decision.endswith(")"):
                        decision = decision[: -len(")")]
                    if "oral" in decision.lower():
                        found_oral += 1
                        avg_scores["Oral"].append(avg_score)
                    elif "spotlight" in decision.lower():
                        found_spotlight += 1
                        avg_scores["Spotlight"].append(avg_score)
                    else:
                        avg_scores["Poster"].append(avg_score)

                    papers.append(
                        {
                            "Title": submission.content.get("title", {}).get(
                                "value", "N/A"
                            ),
                            "Authors": ", ".join(submission.content.get("authors", [])),
                            "Average Review Score": avg_score,
                            "Min Review Score": min_score,
                            "Max Review Score": max_score,
                            "Median Review Score": median_score,
                            "Presentation Type": decision,
                            "Submission #": submission.number,
                            "id": submission.id,
                        }
                    )

        return pd.DataFrame(papers)


# Run the function and save to CSV
df = fetch_neurips_papers(2023)
df.to_csv("neurips_2023_papers_openreview_v2.csv", index=False)
print(df.head())
print(f"Total papers fetched: {len(df)}")
# %%
# df = fetch_neurips_papers(2022)
# df.to_csv("neurips_2022_papers_openreview_v2.csv", index=False)
# print(df.head())
# print(f"Total papers fetched: {len(df)}")

# %%
orals = df[df["Presentation Type"] == "oral"]
spotlights = df[df["Presentation Type"] == "spotlight"]
posters = df[df["Presentation Type"] == "poster"]
spotlights.sort_values(by="Average Review Score", ascending=False)
# %%
