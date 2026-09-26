"""SQLite schema for the repurposing knowledge base (approved drugs, targets, indications)."""
from pathlib import Path

from sqlalchemy import ForeignKey, Index, LargeBinary, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "drugs.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


class Base(DeclarativeBase):
    pass


class Drug(Base):
    __tablename__ = "drugs"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # ChEMBL parent molecule id
    name: Mapped[str | None]
    smiles: Mapped[str]
    fingerprint: Mapped[bytes] = mapped_column(LargeBinary)  # packed 2048-bit Morgan (r=2)
    first_approval: Mapped[int | None]
    targets: Mapped[list["DrugTarget"]] = relationship(back_populates="drug")
    indications: Mapped[list["Indication"]] = relationship(back_populates="drug")


class Target(Base):
    __tablename__ = "targets"
    id: Mapped[str] = mapped_column(String, primary_key=True)  # ChEMBL target id
    name: Mapped[str | None]
    target_type: Mapped[str | None]
    uniprot: Mapped[str | None]  # ';'-separated accessions


class DrugTarget(Base):
    __tablename__ = "drug_targets"
    drug_id: Mapped[str] = mapped_column(ForeignKey("drugs.id"), primary_key=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("targets.id"), primary_key=True)
    action_type: Mapped[str | None]
    mechanism: Mapped[str | None]
    drug: Mapped[Drug] = relationship(back_populates="targets")
    target: Mapped[Target] = relationship()
    __table_args__ = (Index("ix_drug_targets_target", "target_id"),)


class Indication(Base):
    __tablename__ = "indications"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    drug_id: Mapped[str] = mapped_column(ForeignKey("drugs.id"))
    disease: Mapped[str]
    disease_norm: Mapped[str] = mapped_column(index=True)  # lower-cased for matching
    mesh_id: Mapped[str | None]
    drug: Mapped[Drug] = relationship(back_populates="indications")


def get_session() -> Session:
    return Session(engine)
