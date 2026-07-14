# Reviewer Head-to-Head Comparison

Sergeant can compare its review with another reviewer on the same frozen pull-request head.

The comparison is intentionally conservative:

- both reports remain separate evidence sources;
- equivalent findings are matched by changed path, nearby line, category and textual evidence;
- unmatched findings remain visible on the correct side;
- walkthroughs, summaries and nitpicks do not count as actionable defects;
- comment volume does not determine reviewer quality;
- no winner is declared without repository-backed adjudication.

## File comparison

Export the external reviewer comments through Sergeant's existing ingestion format, then run:

```text
sergeant-compare \
  --sergeant-packet build/sergeant-review.json \
  --reference-review build/reference-review.json \
  --reference-name "Reference reviewer" \
  --output build/reviewer-comparison.json \
  --markdown-output build/reviewer-comparison.md \
  --pretty
```

## Live pull-request comparison

The live mode uses Sergeant's existing GET-only, host-validated GitHub evidence boundary:

```text
sergeant-compare \
  --sergeant-packet build/sergeant-review.json \
  --live-repository owner/repository \
  --live-pr 123 \
  --reference-name "Reference reviewer" \
  --reference-author reviewer-login \
  --expected-head-sha <frozen-head-sha> \
  --output build/reviewer-comparison.json \
  --markdown-output build/reviewer-comparison.md \
  --pretty
```

`--expected-head-sha` blocks the comparison when the pull request changes after either review was captured.

The optional GitHub token is read from `GITHUB_TOKEN` by default. The token is not placed in the comparison artifact.

## Side-by-side output

The report contains:

- actionable finding count per reviewer;
- matched findings shown side by side;
- findings unique to Sergeant;
- findings unique to the reference reviewer;
- overlap rate;
- source and frozen-head metadata;
- optional adjudication summaries.

A match means only that both reviewers appear to describe the same issue. It does not establish that the issue is valid.

## Adjudication

An optional adjudication file can classify findings as:

- `confirmed`;
- `suggestion`;
- `false_positive`;
- `duplicate`;
- `uncertain`.

Example:

```json
{
  "decisions": [
    {
      "reviewer": "Sergeant",
      "finding_id": "sergeant-1",
      "status": "confirmed"
    },
    {
      "reviewer": "Reference reviewer",
      "finding_id": "reference-1",
      "status": "false_positive"
    }
  ]
}
```

The comparator can report verified precision for adjudicated findings. Recall remains undefined until the complete verified defect set is known.

## Trust boundary

The external report does not enter Sergeant's verdict consensus during blind review. It is introduced only after Sergeant's packet has been frozen.

Verified external findings may later enter the governed learning process through the existing review-ingestion and decision-workspace controls. Unverified reviewer opinions do not become permanent knowledge.
