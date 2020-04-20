#!/usr/bin/env python3
"Run this after build_database.py - it needs til.db"
import pathlib
import sys
import re
import sqlite_utils


def main(repo_path):
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
    if "--rewrite" in sys.argv:
        readme = repo_path / "README.md"
        index_txt = "\n".join(index).strip()
        readme_contents = readme.open().read()
        readme.open("w").write(index_re.sub(index_txt, readme_contents))
    else:
        print("\n".join(index))


if __name__ == "__main__":
    main(pathlib.Path(__file__).parent.resolve())
