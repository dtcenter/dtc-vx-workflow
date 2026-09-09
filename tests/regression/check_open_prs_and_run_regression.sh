#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

REPO="dtcenter/dtc-vx-workflow"
ACCOUNT=dtc
MACHINE=ursa

# flag to pass to gh commands to specify the repository
REPO_FLAG="-R $REPO"

# label that must be present on PR to trigger run
LABEL="run regression"

echo "--------------------------------------------------"
echo "Start of script at $(date)"
echo "--------------------------------------------------"

echo "Fetching open pull requests..."
echo ""

# Get open PRs as JSON containing PR number, author, and title
gh pr list $REPO_FLAG --state open --json number,author,title | jq -c '.[]' | while read -r pr; do
  pr_number=$(echo "$pr" | jq -r '.number')
  author=$(echo "$pr" | jq -r '.author.login')
  title=$(echo "$pr" | jq -r '.title')

  echo "PR #$pr_number"
  echo "Title: $title"
  echo "Author: @$author"

  if gh pr view $REPO_FLAG "$pr_number" --json labels --jq ".labels[].name | select(. == \"$LABEL\")" | grep -q "$LABEL"; then
    echo "Label '$LABEL' is present on PR #$pr_number."
    echo ""
    cmd="python3 ${SCRIPT_DIR}/run_regression.py --pr $pr_number --account ${ACCOUNT} --machine ${MACHINE}"
    echo "RUNNING: $cmd"
    $cmd
  else
    echo "Label '$LABEL' is NOT present on PR #$pr_number. Skipping"
  fi
  echo ""
done

echo "--------------------------------------------------"
echo "End of script at $(date)"
echo "--------------------------------------------------"
