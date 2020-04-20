#!/usr/bin/env python3
"""This will build the sqllite db"""
from datetime import timezone
import pathlib
import git
import sqlite_utils


def created_changed_times(repo_path, ref="master"):
    """Iterate over commits and create changed times"""
    changed_times = {}
    repo = git.Repo(repo_path, odbt=git.GitDB)
    commits = reversed(list(repo.iter_commits(ref)))
    for commit in commits:
        commit_date = commit.committed_datetime
        affected_files = list(commit.stats.files.keys())
        for filepath in affected_files:
            if filepath not in changed_times:
                changed_times[filepath] = {
                    "created": commit_date.isoformat(),
                    "created_utc": commit_date.astimezone(timezone.utc).isoformat(),
                }
            changed_times[filepath].update(
                {
                    "updated": commit_date.isoformat(),
                    "updated_utc": commit_date.astimezone(timezone.utc).isoformat(),
                }
            )
    return changed_times


def build_database(repo_path):
    """Create the sqlite db with all of the MD files"""
    all_times = created_changed_times(repo_path)
    til_db = sqlite_utils.Database(repo_path / "til.db")
    table = til_db.table("til", pk="path")
    for filepath in repo_path.glob("*/*.md"):
        file_fp = filepath.open()
        title = file_fp.readline().lstrip("#").strip()
        body = file_fp.read().strip()
        path = str(filepath.relative_to(repo_path))
        url = "https://github.com/sleach/til/blob/master/{}".format(path)
        record = {
            "path": path.replace("/", "_"),
            "topic": path.split("/")[0],
            "title": title,
            "url": url,
            "body": body,
        }
        record.update(all_times[path])
        table.insert(record)
    if "til" in til_db.table_names() and "til_fts" not in til_db.table_names():
        table.enable_fts(["title", "body"])


if __name__ == "__main__":
    build_database(pathlib.Path(__file__).parent.resolve())
