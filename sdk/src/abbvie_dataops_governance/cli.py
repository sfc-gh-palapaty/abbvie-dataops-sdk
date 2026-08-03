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
from abbvie_dataops_governance.ontology.pipeline import build_ontology
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


@cli.command("ontology")
@click.option("--erd", "erd_source", default="data/ontology/pharma_erd.md", show_default=True)
@click.option("--rules", "business_rules_source", default="data/ontology/business_rules.md", show_default=True)
@click.option("--mapping", "source_to_target_source", default="data/ontology/source_to_target.csv", show_default=True)
@click.option("--output-dir", default="outputs/ontology", show_default=True)
@click.option("--model-name", default="abbvie_pharma_intelligence", show_default=True)
@click.option("--version", "ontology_version", default="2.1.0", show_default=True)
@click.option("--database", "target_database", default="ABBVIE_DATAOPS_DEV", show_default=True)
@click.option("--schema", "target_schema", default="CURATED", show_default=True)
@click.option("--repo-root", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--s3-bucket", default=None, help="S3 bucket (SharePoint stand-in for demo)")
@click.option("--s3-prefix", default=None, help="S3 prefix containing the three ontology documents")
@click.option("--evidence-out", type=click.Path(dir_okay=False, path_type=Path), default=None)
def ontology_cmd(
    erd_source: str,
    business_rules_source: str,
    source_to_target_source: str,
    output_dir: str,
    model_name: str,
    ontology_version: str,
    target_database: str,
    target_schema: str,
    repo_root: Path | None,
    s3_bucket: str | None,
    s3_prefix: str | None,
    evidence_out: Path | None,
) -> None:
    """Build OSI-compliant ontology YAML from business documents (S3 or local)."""
    root = repo_root or Path.cwd()
    result = build_ontology(
        erd_source=erd_source,
        business_rules_source=business_rules_source,
        source_to_target_source=source_to_target_source,
        output_dir=output_dir,
        model_name=model_name,
        ontology_version=ontology_version,
        target_database=target_database,
        target_schema=target_schema,
        repo_root=root,
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
    )
    click.echo(f"OSI model written: {result.output_path}")
    click.echo(f"  datasets={result.datasets} relationships={result.relationships} metrics={result.metrics}")
    click.echo(f"  hash={result.content_hash}")
    if evidence_out:
        from abbvie_dataops_governance.runner import CheckOutcome, EvidenceBundle

        bundle = EvidenceBundle(
            service=model_name,
            adapter="ontology",
            profile="build",
            classification="internal",
            passed=True,
            outcomes=[
                CheckOutcome(
                    name="ontology_build",
                    passed=True,
                    detail=f"{result.datasets} datasets, {result.relationships} relationships",
                    data=result.to_dict(),
                )
            ],
            adapter_facts=result.to_dict(),
        )
        write_evidence(bundle, evidence_out)
        click.echo(f"  evidence written to {evidence_out}")
    sys.exit(0)


def main(argv: list[str] | None = None) -> int:
    cli.main(args=argv, standalone_mode=False, prog_name="abbvie-dataops")
    return 0


if __name__ == "__main__":
    main()
