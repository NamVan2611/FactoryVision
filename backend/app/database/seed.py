"""Database bootstrap & seed script.

Run once after cloning to create the schema (SQLite dev DB by default) and
populate a small, realistic dataset useful for the dashboard demo.

Usage
-----
    python -m app.database.seed            # create tables + seed if empty
    python -m app.database.seed --reset    # drop everything, recreate, reseed
"""

from __future__ import annotations

import argparse
import random
from datetime import timedelta

from app.database.base import Base
from app.database.session import engine, init_db, session_scope
from app.models import (
    Alarm,
    AlarmSeverity,
    DefectType,
    InspectionHistory,
    InspectionResult,
    Machine,
    MachineLog,
    MachineLogLevel,
    MachineStatus,
    Operator,
    Product,
)
from app.utils import get_logger
from app.utils.time_utils import utcnow

logger = get_logger(__name__)


def _seed_master_data() -> None:
    """Insert machines, products and operators if the tables are empty."""
    with session_scope() as db:
        if db.query(Machine).count() > 0:
            logger.info("Master data already present; skipping seed.")
            return

        machines = [
            Machine(code="M-01", name="Vision Station 1", line="LINE-A",
                    status=MachineStatus.RUNNING, temperature=42.5, speed=120.0, uph=850),
            Machine(code="M-02", name="Vision Station 2", line="LINE-A",
                    status=MachineStatus.IDLE, temperature=30.0, speed=0.0, uph=0),
            Machine(code="M-03", name="Vision Station 3", line="LINE-B",
                    status=MachineStatus.MAINTENANCE, temperature=28.0, speed=0.0, uph=0),
        ]
        products = [
            Product(code="P-1001", name="PCB Board A", description="Main controller board"),
            Product(code="P-1002", name="Housing Cover", description="Plastic top cover"),
        ]
        operators = [
            Operator(employee_id="EMP-001", name="Alice Nguyen", shift="A"),
            Operator(employee_id="EMP-002", name="Bao Tran", shift="B"),
        ]
        db.add_all(machines + products + operators)
        logger.info("Seeded %d machines, %d products, %d operators.",
                    len(machines), len(products), len(operators))


def _seed_transactions(n: int = 50) -> None:
    """Generate sample inspections, logs and alarms for the demo."""
    with session_scope() as db:
        if db.query(InspectionHistory).count() > 0:
            logger.info("Transaction data already present; skipping.")
            return

        machine = db.query(Machine).filter_by(code="M-01").one()
        product = db.query(Product).first()
        operator = db.query(Operator).first()
        now = utcnow()

        defects = [DefectType.COLOR, DefectType.DIMENSION,
                   DefectType.MISSING_PART, DefectType.SCRATCH]
        rng = random.Random(42)

        for i in range(n):
            is_pass = rng.random() > 0.18  # ~82% yield
            result = InspectionResult.PASS if is_pass else InspectionResult.FAIL
            defect = DefectType.NONE if is_pass else rng.choice(defects)
            db.add(InspectionHistory(
                machine_id=machine.id,
                product_id=product.id if product else None,
                operator_id=operator.id if operator else None,
                result=result,
                defect_type=defect,
                confidence=round(rng.uniform(0.80, 0.99), 3),
                processing_ms=round(rng.uniform(15.0, 60.0), 2),
                inspected_at=now - timedelta(minutes=n - i),
            ))

        db.add(MachineLog(machine_id=machine.id, level=MachineLogLevel.INFO,
                          event="MACHINE_START", message="Operator started the line.",
                          logged_at=now - timedelta(minutes=n)))
        db.add(Alarm(machine_id=machine.id, code="TEMP_HIGH",
                     message="Temperature above warning threshold (42.5C).",
                     severity=AlarmSeverity.WARNING, raised_at=now - timedelta(minutes=5)))
        logger.info("Seeded %d inspections + 1 log + 1 alarm.", n)


def reset() -> None:
    """Drop and recreate all tables (DESTRUCTIVE)."""
    import app.models  # noqa: F401 - register tables
    logger.warning("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    init_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialise & seed the database.")
    parser.add_argument("--reset", action="store_true", help="Drop & recreate first.")
    args = parser.parse_args()

    if args.reset:
        reset()
    else:
        init_db()

    _seed_master_data()
    _seed_transactions()
    logger.info("Seed complete.")


if __name__ == "__main__":
    main()
