import json
from pathlib import Path


def write_call_artifacts(root, call_id, metadata, transcript, analysis):
    call_dir = Path(root) / "calls" / call_id
    call_dir.mkdir(parents=True, exist_ok=True)
    (call_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    (call_dir / "transcript.txt").write_text(transcript)
    (call_dir / "analysis.md").write_text(analysis)
    return call_dir


def write_bug_report(root, issues):
    path = Path(root) / "bug_report.md"
    path.write_text(bug_report_markdown(issues))
    return path


def bug_report_markdown(issues):
    lines = ["# Bug Report", ""]
    for issue in issues:
        lines.extend(
            [
                f"## {issue['severity']} - {issue['title']}",
                "",
                f"Call: {issue['call']}",
                f"Evidence: {issue['evidence']}",
                f"Expected: {issue['expected']}",
                "",
            ]
        )
    return "\n".join(lines)
