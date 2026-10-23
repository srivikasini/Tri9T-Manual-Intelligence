"""Command-Line Interface for the Tri9T Manual Intelligence Platform."""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.core.database import SessionLocal, init_db
from app.api.ingest import perform_ingestion
from app.diffing.change_detector import ChangeDetector
from app.models.node import SectionNode
from app.models.qa_artifact import QAArtifact
from app.staleness.analyzer import StalenessAnalyzer
from app.core.logging import setup_logging, logger

setup_logging()

def handle_ingest(args):
    """Ingest a PDF manual into the database."""
    init_db()
    db = SessionLocal()
    try:
        file_path = Path(args.file)
        result = perform_ingestion(
            file_path=file_path,
            version_id=args.version,
            document_id=args.doc_id,
            db=db
        )
        print(f"\n[SUCCESS] Successfully ingested '{result.filename}' as version '{result.version_id}'")
        print(f"  Pages: {result.page_count}")
        print(f"  Nodes Extracted: {result.total_nodes_extracted}")
        print(f"  Top-level Sections: {result.top_level_sections_count}")
        print(f"  Extraction Warnings: {len(result.warnings)}")
        for w in result.warnings:
            print(f"    - {w}")
    finally:
        db.close()

def handle_compare(args):
    """Compare two ingested document versions."""
    db = SessionLocal()
    try:
        base_nodes = db.query(SectionNode).filter(SectionNode.document_version == args.base).order_by(SectionNode.order_index).all()
        target_nodes = db.query(SectionNode).filter(SectionNode.document_version == args.target).order_by(SectionNode.order_index).all()

        if not base_nodes:
            print(f"[ERROR] No nodes found for base version '{args.base}'. Please ingest it first.")
            sys.exit(1)
        if not target_nodes:
            print(f"[ERROR] No nodes found for target version '{args.target}'. Please ingest it first.")
            sys.exit(1)

        result = ChangeDetector.compare_versions(
            base_version=args.base,
            target_version=args.target,
            base_nodes=base_nodes,
            target_nodes=target_nodes
        )

        print(f"\n=== VERSION COMPARISON: {args.base} -> {args.target} ===")
        print(f"Total Base Nodes: {result.total_base_nodes} | Total Target Nodes: {result.total_target_nodes}")
        print("Summary of Changes:")
        for chg_type, count in result.summary.items():
            print(f"  {chg_type}: {count}")

        print("\nNotable Changes & Diffs:")
        for c in result.comparisons:
            if c.change_type.value != "UNCHANGED":
                print(f"\n* [{c.change_type.value}] {c.logical_id} (confidence: {c.matching_confidence})")
                print(f"  {c.explanation}")
                if c.unified_diff:
                    print("  --- Unified Diff ---")
                    for diff_line in c.unified_diff.splitlines()[:10]:
                        print(f"    {diff_line}")
                    if len(c.unified_diff.splitlines()) > 10:
                        print("    ... (truncated)")
    finally:
        db.close()

def handle_staleness(args):
    """Check staleness of generated QA artifacts."""
    db = SessionLocal()
    try:
        artifacts = db.query(QAArtifact).all()
        if not artifacts:
            print("[INFO] No generated QA artifacts found in database.")
            return

        print(f"\n=== EVALUATING STALENESS AGAINST TARGET VERSION: {args.target} ===")
        for art in artifacts:
            res = StalenessAnalyzer.evaluate_artifact_staleness(art, args.target, db)
            status_tag = "[STALE]" if res.is_stale else "[VALID]"
            print(f"\n{status_tag} Artifact ID: {res.artifact_id} (Base: {res.base_version})")
            print(f"  Overall Severity: {res.overall_severity.value}")
            print(f"  Affected Nodes: {res.affected_nodes_count}/{res.total_source_nodes}")
            print(f"  Recommendation: {res.recommendation}")
            for reason in res.reasons:
                print(f"    - [{reason.drift_type.value} | {reason.severity.value}] {reason.description}")
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="Tri9T Manual Intelligence Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest command
    ingest_p = subparsers.add_parser("ingest", help="Ingest a PDF manual")
    ingest_p.add_argument("--version", required=True, help="Version tag (e.g. v1, v2)")
    ingest_p.add_argument("--file", required=True, help="Path to PDF manual file")
    ingest_p.add_argument("--doc-id", default="ct200_manual", help="Parent document ID")
    ingest_p.set_defaults(func=handle_ingest)

    # Compare command
    comp_p = subparsers.add_parser("compare", help="Compare two document versions")
    comp_p.add_argument("--base", default="v1", help="Base version ID (default: v1)")
    comp_p.add_argument("--target", default="v2", help="Target version ID (default: v2)")
    comp_p.set_defaults(func=handle_compare)

    # Staleness command
    stale_p = subparsers.add_parser("staleness", help="Check staleness of QA artifacts")
    stale_p.add_argument("--target", default="v2", help="Target version to check against")
    stale_p.set_defaults(func=handle_staleness)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
