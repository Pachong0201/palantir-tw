from datetime import datetime, date

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Entity(Base):
    """本体对象：人物/政党/组织/选区/选举/事件/文档。"""

    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("type", "external_id", name="uq_entity_external"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    props: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Assertion(Base):
    """断言：subject -[predicate]-> object，带证据等级与来源文档。"""

    __tablename__ = "assertions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    predicate: Mapped[str] = mapped_column(String(64), index=True)
    object_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True, index=True)
    object_text: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    grade: Mapped[str] = mapped_column(String(1), default="E")
    document_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="asserted", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subject = relationship("Entity", foreign_keys=[subject_id])
    object = relationship("Entity", foreign_keys=[object_id])
    document = relationship("Entity", foreign_keys=[document_id])


class Candidacy(Base):
    """参选记录（结构化选务数据，证据 A 级）。"""

    __tablename__ = "candidacies"
    __table_args__ = (
        UniqueConstraint("person_id", "election_id", "district_id", name="uq_candidacy"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    election_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("entities.id"), index=True)
    party_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id"), nullable=True)
    office: Mapped[str] = mapped_column(String(64))  # 直轄市長 / 縣市長 / ...
    ballot_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    votes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vote_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    elected: Mapped[bool] = mapped_column(default=False)
    incumbent: Mapped[bool] = mapped_column(default=False)
    sex: Mapped[str | None] = mapped_column(String(8), nullable=True)
    birth_roc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    education: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    person = relationship("Entity", foreign_keys=[person_id])
    election = relationship("Entity", foreign_keys=[election_id])
    district = relationship("Entity", foreign_keys=[district_id])
    party = relationship("Entity", foreign_keys=[party_id])


class RawItem(Base):
    """采集暂存：原样存档 + 指纹去重，重放成本为零。"""

    __tablename__ = "raw_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(128), index=True)
    external_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="staged", index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
