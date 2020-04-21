#!/usr/bin/env python3
"""Manage TIL files"""
import argparse
import re
import sys
from datetime import timezone
import pathlib
import git
import sqlite_utils


def update_readme(repo_path, rewrite):
    """Iterate the MD files and update the main README.md file"""
    index_re = re.compile(
        r"<!\-\- index starts \-\->.*<!\-\- index ends \-\->", re.DOTALL
    )
    til_db = sqlite_utils.Database(repo_path / "til.db")
    by_topic = {}
    for row in til_db["til"].rows_where(order_by="created_utc"):
        by_topic.setdefault(row["topic"], []).append(row)
    index = ["<!-- index starts -->"]
    for topic, rows in by_topic.items():
        index.append("## {}\n".format(topic))
        for row in rows:
            index.append(
                "* [{title}]({url}) - {date}".format(
                    date=row["created"].split("T")[0], **row
                )
            )
        index.append("")
    if index[-1] == "":
        index.pop()
    index.append("<!-- index ends -->")
    if rewrite:
        readme = repo_path / "README.md"
        index_txt = "\n".join(index).strip()
        readme_contents = readme.open().read()
        readme.open("w").write(index_re.sub(index_txt, readme_contents))
    else:
        print("\n".join(index))


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


def main():
    """Main program for managing args etc."""
    repo_path = pathlib.Path(__file__).parent.resolve()
    parser = argparse.ArgumentParser(description="Manage TIL files.")
    parser.add_argument("--build", action="store_true", help="Build database file")
    parser.add_argument("--update", action="store_true", help="Update README file")
    parser.add_argument(
        "--rewrite", action="store_true", help="Rewrite the README in place"
    )
    parser.add_argument("--repo-path", default=repo_path, help="Path to repo directory")

    args = parser.parse_args()
    if args.build:
        build_database(args.repo_path)
    elif args.update:
        update_readme(args.repo_path, args.rewrite)
    else:
        parser.print_help(sys.stderr)


if __name__ == "__main__":
    main()
