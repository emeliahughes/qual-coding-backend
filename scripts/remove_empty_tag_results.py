"""
One-time script: Remove submitted (non-excluded) results with no tags
from the winter boots 2025-2026 project, then recalculate progress_index
for all coders in that project.

Usage (from qual-coding-backend directory):
  python scripts/remove_empty_tag_results.py [--dry-run]

  --dry-run  Print which rows would be deleted and count; do not delete or commit.
"""

import argparse
import json
import sys
import os

# Ensure backend root is on path when run as script from repo or backend dir
_script_dir = os.path.dirname(os.path.abspath(__file__))
_backend_root = os.path.dirname(_script_dir)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app import app
from models import db, Project, Result, Coder

PROJECT_SLUG = "winter-boots-2025-2026"


def has_no_tags(categories_raw):
    """True if categories is null, empty, or JSON with no non-empty tag lists."""
    if not categories_raw:
        return True
    try:
        data = json.loads(categories_raw)
        if not isinstance(data, dict):
            return True
        return not any(tags for tags in data.values())
    except (TypeError, json.JSONDecodeError):
        return True


def run(dry_run=False):
    with app.app_context():
        project = Project.query.filter_by(slug=PROJECT_SLUG).first()
        if not project:
            print(f"Project with slug '{PROJECT_SLUG}' not found. Exiting.")
            return 1

        # Submitted, non-excluded results only
        candidates = Result.query.filter_by(
            project_id=project.id,
            status="submitted",
            excluded=False,
        ).all()

        to_delete = [r for r in candidates if has_no_tags(r.categories)]
        count = len(to_delete)

        if count == 0:
            print("No submitted results with empty tags found. Nothing to do.")
            return 0

        print(f"Found {count} result(s) with no tags (project: {project.name}):")
        for r in to_delete:
            coder_name = r.coder.name if r.coder else "(unknown)"
            print(f"  id={r.id} coder={coder_name} video_id={r.video_id}")

        if dry_run:
            print("--dry-run: no changes made.")
            return 0

        for r in to_delete:
            db.session.delete(r)
        db.session.commit()
        print(f"Deleted {count} result(s).")

        # Recalculate progress_index for every coder in this project
        for coder in project.coders:
            completed = Result.query.filter_by(
                project_id=project.id,
                coder_id=coder.id,
            ).filter(
                (Result.status == "submitted") | (Result.excluded == True),
            ).count()
            coder.progress_index = completed
        db.session.commit()
        print("Recalculated progress_index for all coders in the project.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Remove empty-tag submitted results for winter boots project.")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be deleted; do not commit.")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
