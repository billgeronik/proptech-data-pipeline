# Verification record — 23 November 2026

## What was inspected

The live GitHub default branch at commit `4efd10f696d44eb5119a70b98d6f498ee2cf67c7` and the previously supplied `proptech-milestone-1.zip` were read before editing. The earlier archive already provided an indentation fix, model, parser, report writer, sample and three tests. This revision retains that structure, activates configuration, tightens parsing and validation, supplies expected output and expands tests.

The GitHub connection is read-only. The archive and patch are the completed deliverables; the online repository was not changed.

## What actually ran

- Verified the five baseline files against their GitHub blob hashes.
- Created a separate clean directory containing those exact upstream files.
- Ran `git apply --check` and `git apply` with the supplied milestone patch successfully.
- Created a fresh virtual environment there using **Python 3.12.14 on Linux**.
- Ran `python -m pip install --no-index -r requirements.txt` successfully. No third-party packages are required.
- Ran `python main.py`: **8 rows, 2 OK, 6 WARNING**; exit code 0.
- Ran `python -m unittest discover -s tests -v`: **55 tests passed**, no failures, errors or skipped tests; exit code 0.
- Compared the generated CSV with `fixtures/expected_report.csv`: **byte-for-byte match**.
- Independently checked both valid sample rows using `decimal.Decimal`: all displayed metrics matched.
- Checked the separate scenario proposal using `decimal.Decimal`: both base cases and all five single-input sensitivity cases matched their stated results. The proposal is documentation only.

The captured test output is in `test-run.txt`. Test times vary by machine. Python 3.10 is the documented minimum for the syntax used; execution was verified on 3.12.14, not every supported Python release. macOS and Windows instructions are supplied but were not run on those operating systems here.

## Boundaries

All fixtures are synthetic. No company records, credentials, client data, private plans or financial records were used. No company testing, deployment or adoption is claimed. No Gmail, Sheets, dashboard, structural-analysis or drawing-checking feature is implemented. The checked arithmetic establishes no legal building rights, actual saleable area, formal valuation or investment recommendation.
