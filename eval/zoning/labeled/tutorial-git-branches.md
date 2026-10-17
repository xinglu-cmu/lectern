# Working with Git Branches: A Hands-On Tutorial

This tutorial takes about twenty minutes. You will create a branch, make a change on it, and merge it back, and along the way see what Git is actually doing with the files in `.git`. It assumes you have Git installed and have made at least one commit before.

## Why branches exist

A branch is nothing more than a file containing the hash of a commit. When you commit on a branch, Git writes the new commit and moves that one file to point at it. That is why creating a branch is instant and why having a hundred of them costs nothing: there is no copy of the project anywhere, only a hundred forty-character pointers. Everything that feels heavy about branches comes from merging, not from branching.

## Step 1: Create a branch

Run the following in a repository with at least one commit. Use a name that says what the branch is for.

```
git switch -c add-readme
cat .git/HEAD
cat .git/refs/heads/add-readme
```

The first `cat` shows that HEAD now names your new branch. The second shows the branch file itself: one commit hash, the same one `main` points at.

## Step 2: Commit on the branch

Create a file and commit it. Then look at the branch file again and compare it with `main`.

```
echo "# My project" > README.md
git add README.md
git commit -m "Add a README"
cat .git/refs/heads/add-readme
cat .git/refs/heads/main
```

The two hashes now differ. Your branch moved; `main` did not.

## Step 3: Merge it back

Switch to `main` and merge. Because `main` has not moved since you branched, Git performs a fast-forward: it moves the `main` pointer to your commit and writes no merge commit at all.

```
git switch main
git merge add-readme
git log --oneline -3
```

## What to try next

Make a commit on `main` before merging, so the branches diverge, and repeat Step 3. Read the output carefully: this time Git creates a merge commit with two parents. Then read the chapter on rebasing in Pro Git, which is free online, and try `git rebase main` from the branch as an alternative.

---

Part of the Harbor Learning series · [Previous: Your first commit](https://example.org/git-1) · [Next: Rebasing](https://example.org/git-3) · Comments are moderated.
