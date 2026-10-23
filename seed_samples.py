import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.core.database import SessionLocal, init_db
from app.models.selection import Selection, SelectionNode
from app.models.node import SectionNode
from app.models.qa_artifact import QAArtifact
from app.api.qa import generate_qa_test_ideas
from app.schemas.qa import QAGenerateRequest
from app.staleness.analyzer import StalenessAnalyzer
from app.core.logging import setup_logging, logger

setup_logging()

def seed_sample_records():
    init_db()
    db = SessionLocal()
    try:
        print("==================================================")
        print("🌱 SEEDING SAMPLE DEMO RECORDS INTO DATABASE...")
        print("==================================================")

        # Clear previous demo selections to keep things clean
        db.query(SelectionNode).delete()
        db.query(QAArtifact).delete()
        db.query(Selection).delete()
        db.commit()

        # Sample 1: Safety & Alarms (Stale in v2 due to 2.0s -> 1.5s & E6)
        nodes_s1 = db.query(SectionNode).filter(
            SectionNode.document_version == "v1",
            SectionNode.section_number.in_(["4.1", "4.2"])
        ).order_by(SectionNode.order_index).all()

        sel1 = Selection(
            name="1. Overpressure & Safety Protection Suite",
            document_version="v1",
            description="Covers overpressure safety valve thresholds and pneumatic error code behaviors."
        )
        db.add(sel1)
        db.flush()
        for idx, n in enumerate(nodes_s1):
            db.add(SelectionNode(selection_id=sel1.id, node_id=n.id, order_index=idx))
        db.commit()

        # Generate QA for Selection 1
        art1 = generate_qa_test_ideas(sel1.id, QAGenerateRequest(force_regenerate=True), db)
        print(f"✅ Created Selection 1: '{sel1.name}' (ID: {sel1.id})")
        print(f"   Generated {len(art1.test_cases)} QA test cases (Artifact ID: {art1.id})")

        # Sample 2: Intended Use & Indications (Valid in v2 - Unchanged)
        nodes_s2 = db.query(SectionNode).filter(
            SectionNode.document_version == "v1",
            SectionNode.section_number.in_(["1.1", "1.2"])
        ).order_by(SectionNode.order_index).all()

        sel2 = Selection(
            name="2. Clinical Indications & Contraindications Suite",
            document_version="v1",
            description="Covers patient indications, target population, and clinical contraindications (e.g. mastectomy)."
        )
        db.add(sel2)
        db.flush()
        for idx, n in enumerate(nodes_s2):
            db.add(SelectionNode(selection_id=sel2.id, node_id=n.id, order_index=idx))
        db.commit()

        # Generate QA for Selection 2
        art2 = generate_qa_test_ideas(sel2.id, QAGenerateRequest(force_regenerate=True), db)
        print(f"✅ Created Selection 2: '{sel2.name}' (ID: {sel2.id})")
        print(f"   Generated {len(art2.test_cases)} QA test cases (Artifact ID: {art2.id})")

        # Sample 3: Battery Life & Power Shutoff (Stale in v2 due to 300 -> 250 cycles & 15% -> 10%)
        nodes_s3 = db.query(SectionNode).filter(
            SectionNode.document_version == "v1",
            SectionNode.section_number.in_(["2.1.1.1", "3.4"])
        ).order_by(SectionNode.order_index).all()

        sel3 = Selection(
            name="3. Power Management & Battery Life Suite",
            document_version="v1",
            description="Covers battery longevity expectations, low-battery alerts, and auto-shutoff timer."
        )
        db.add(sel3)
        db.flush()
        for idx, n in enumerate(nodes_s3):
            db.add(SelectionNode(selection_id=sel3.id, node_id=n.id, order_index=idx))
        db.commit()

        # Generate QA for Selection 3
        art3 = generate_qa_test_ideas(sel3.id, QAGenerateRequest(force_regenerate=True), db)
        print(f"✅ Created Selection 3: '{sel3.name}' (ID: {sel3.id})")
        print(f"   Generated {len(art3.test_cases)} QA test cases (Artifact ID: {art3.id})")

        print("\n==================================================")
        print("🔍 EVALUATING STALENESS AGAINST VERSION 2 (v2)...")
        print("==================================================")
        for art in [art1, art2, art3]:
            res = StalenessAnalyzer.evaluate_artifact_staleness(
                db.query(QAArtifact).filter(QAArtifact.id == art.id).first(),
                "v2",
                db
            )
            tag = "❌ [STALE]" if res.is_stale else "✅ [VERIFIED VALID]"
            print(f"{tag} Artifact {res.artifact_id} -> Status: {res.overall_severity.value}")
            print(f"   Recommendation: {res.recommendation}")
            for r in res.reasons:
                print(f"   * {r.drift_type.value}: {r.description}")

        print("\n🎉 Sample records seeded successfully!")
        print("You can now open http://127.0.0.1:8000/dashboard to test and view them in your browser!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_sample_records()
