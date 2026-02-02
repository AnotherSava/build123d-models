---
name: commit
description: Group all changes logically and generate Conventional Commit messages
disable-model-invocation: true
allowed-tools: Read, Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*)
---
1. Optimize imports in modified files.
2. Run `git status` and `git diff` to analyze all changes (staged and unstaged).
3. Group into atomic commits by feature/fix/refactor, make sure that each element can be committed independently. Put model file (.stl and .3mf) changes into the same group as code changes for that model.
4. For each group: list files, count total number of lines changed, generate Conventional Commit message (type: subject\n\nbody bullets).
5. Confirm before committing. Stage files for each group before committing. Use recent commit history for style.
6. Do NOT include Co-Authored-By or any AI/Claude mentions in commit messages.
