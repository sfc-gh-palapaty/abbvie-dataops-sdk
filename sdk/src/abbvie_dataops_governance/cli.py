"""abbvie-dataops CLI: the single entrypoint every CI workflow calls.

Subcommands:

  abbvie-dataops run --manifest <path> [--profile develop|build|promote]
                     [--repo-root <dir>] [--evidence-out <file>]

  abbvie-dataops gate --changed-files <file>
      Reads newline-delimited paths from <file> (or '-' for stdin) and prints a
      JSON decision: which manifests must run, and whether the PR must fail
      closed because a data-affecting change is missing required artifacts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from abbvie_dataops_governance.change_detector import detect
from abbvie_dataops_governance.runner import run_manifest, write_evidence


@click.group()
def cli() -> None:
    """AbbVie DataOps Governance SDK"""


@cli.command("run")
@click.option("--manifest", "manifest_path", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--profile", type=click.Choice(["develop", "build", "promote"]), default=None)
@click.option("--repo-root", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--evidence-out", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--quiet", is_flag=True, default=False)
def run_cmd(manifest_path: Path, profile: str | None, repo_root: Path | None, evidence_out: Path | None, quiet: bool) -> None:
    bundle = run_manifest(manifest_path, profile=profile, repo_root=repo_root or Path.cwd())

    if not quiet:
        click.echo(f"\n=== {bundle.service} [{bundle.adapter}/{bundle.profile}] ===")
        for o in bundle.outcomes:
            mark = "OK  " if o.passed else "FAIL"
            click.echo(f"  [{mark}] {o.name}: {o.detail}")
        for emitter, info in bundle.emissions.items():
            click.echo(f"  [emit] {emitter}: {info}")
        click.echo(f"  result: {'PASS' if bundle.passed else 'FAIL'}\n")

    if evidence_out:
        write_evidence(bundle, evidence_out)
        if not quiet:
            click.echo(f"  evidence written to {evidence_out}")

    sys.exit(0 if bundle.passed else 1)


@cli.command("gate")
@click.option("--changed-files", "changed_files_path", required=True, type=click.Path(path_type=Path))
@click.option("--out", "out_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--strict", is_flag=True, default=False, help="Exit non-zero when must_fail_closed is true")
def gate_cmd(changed_files_path: Path, out_path: Path | None, strict: bool) -> None:
    if str(changed_files_path) == "-":
        text = sys.stdin.read()
    else:
        text = Path(changed_files_path).read_text(encoding="utf-8")
    paths = [line.strip() for line in text.splitlines() if line.strip()]
    decision = detect(paths)
    payload = {
        "is_data_change": decision.is_data_change,
        "triggered_manifests": decision.triggered_manifests,
        "blockers": decision.blockers,
        "must_fail_closed": decision.must_fail_closed,
    }
    rendered = json.dumps(payload, indent=2)
    click.echo(rendered)
    if out_path:
        Path(out_path).write_text(rendered, encoding="utf-8")
    if strict and decision.must_fail_closed:
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    cli.main(args=argv, standalone_mode=False, prog_name="abbvie-dataops")
    return 0


if __name__ == "__main__":
    main()
