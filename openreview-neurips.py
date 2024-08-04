# %%
from functools import cache
from pathlib import Path

import openreview
import pandas as pd
from tqdm import tqdm

from memoshelve import memoshelve

# %%
cache_dir = Path(".cache")
cache_dir.mkdir(exist_ok=True)
# %%


def fetch_neurips_2023_papers():
    # Initialize the client
    client = openreview.api.OpenReviewClient(baseurl="https://api2.openreview.net")

    with memoshelve(client.get_notes, filename=cache_dir / "openreview.api.OpenReviewClient.get_notes")() as get_notes:
        client.get_notes = get_notes
        # Search for NeurIPS 2023 submissions
        submissions = list(
            openreview.tools.iterget_notes(
                client,
                invitation="NeurIPS.cc/2023/Conference/-/Submission",
                details="original",
            )
        )

        papers = []
        found = 0
        found_oral = 0
        found_spotlight = 0
        with tqdm(submissions, desc="Fetching papers") as pbar:
            for submission in pbar:
                pbar.set_postfix(
                    {
                        "Found": found,
                        "Oral": found_oral,
                        "Spotlight": found_spotlight,
                        "submission #": submission.number,
                    }
                )
                # Check if the paper was accepted
                decision_note = client.get_notes(
                    invitation=f"NeurIPS.cc/2023/Conference/Submission{submission.number}/-/Decision",
                    limit=1,
                )

                if decision_note and "Accept" in decision_note[0].content.get(
                    "decision", {}
                ).get("value", ""):
                    found += 1
                    # Fetch review scores
                    reviews = client.get_notes(
                        invitation=f"NeurIPS.cc/2023/Conference/Submission{submission.number}/-/Official_Review"
                    )

                    scores = [
                        int(
                            review.content.get("rating", {}).get("value", "0").split(":")[0]
                        )
                        for review in reviews
                        if "rating" in review.content
                    ]
                    avg_score = sum(scores) / len(scores) if scores else None

                    # Determine presentation type
                    decision = (
                        decision_note[0]
                        .content.get("decision", {})
                        .get("value", "Accept (Poster)")
                    )
                    if "Accept (Oral)" in decision:
                        presentation_type = "Oral"
                        found_oral += 1
                    elif "Accept (Spotlight)" in decision:
                        presentation_type = "Spotlight"
                        found_spotlight += 1
                    else:
                        presentation_type = "Poster"

                    papers.append(
                        {
                            "Title": submission.content.get("title", {}).get(
                                "value", "N/A"
                            ),
                            "Authors": ", ".join(submission.content.get("authors", [])),
                            "Average Review Score": avg_score,
                            "Presentation Type": presentation_type,
                        }
                    )

        return pd.DataFrame(papers)


# Run the function and save to CSV
df = fetch_neurips_2023_papers()
df.to_csv("neurips_2023_papers_openreview_v2.csv", index=False)
print(df.head())
print(f"Total papers fetched: {len(df)}")

# %%
