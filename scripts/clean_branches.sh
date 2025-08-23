#!/bin/bash

# Script to clean up local and remote branches except main and origin/main

# Check if running in bash, if not re-execute with bash
if [ -z "$BASH_VERSION" ]; then
    exec /bin/bash "$0" "$@"
fi

# Parse command line arguments
DRY_RUN=false
if [ "$1" = "-d" ] || [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "DRY RUN MODE: Showing what branches would be deleted without actually deleting them"
fi

# Safety check - ensure we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

echo "Cleaning up branches..."

# Delete all local branches except main
echo "Local branches to be processed:"
if $DRY_RUN; then
    for branch in $(git branch | grep -v "main" | tr -d '* '); do
        if [ -n "$branch" ]; then
            echo "Would delete local branch: $branch"
        fi
    done
else
    echo "Deleting local branches..."
    for branch in $(git branch | grep -v "main" | tr -d '* '); do
        if [ -n "$branch" ]; then
            echo "Deleting local branch: $branch"
            git branch -D "$branch"
        fi
    done
fi

# Delete all remote branches on origin except main
echo "Remote branches to be processed:"
if $DRY_RUN; then
    for branch in $(git branch -r | grep "origin/" | grep -v "origin/main" | grep -v "origin/HEAD"); do
        # Extract branch name without origin/ prefix
        branch_name=$(echo "$branch" | sed 's/origin\///')
        if [ -n "$branch_name" ] && [ "$branch_name" != "main" ] && [ "$branch_name" != "HEAD" ]; then
            echo "Would delete remote branch: $branch_name"
        fi
    done
else
    echo "Deleting remote branches..."
    for branch in $(git branch -r | grep "origin/" | grep -v "origin/main" | grep -v "origin/HEAD"); do
        # Extract branch name without origin/ prefix
        branch_name=$(echo "$branch" | sed 's/origin\///')
        if [ -n "$branch_name" ] && [ "$branch_name" != "main" ] && [ "$branch_name" != "HEAD" ]; then
            echo "Deleting remote branch: $branch_name"
            git push origin --delete "$branch_name"
        fi
    done
fi

echo "Branch cleanup complete!"
