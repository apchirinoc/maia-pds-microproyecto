"""Modelos ORM que espejan el esquema de `model/scripts/ddl/`.

Los tipos enumerados se declaran con `create_type=False`: los crea el DDL, y
SQLAlchemy sólo los usa. Duplicar su creación aquí produciría un conflicto en
el arranque.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CHAR,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

CLASES_TUMOR = ("glioma", "meningioma", "pituitary", "healthy")

TumorClass = Enum(*CLASES_TUMOR, name="tumor_class", create_type=False)
UploadStatus = Enum("validated", "pending", "discarded", name="upload_status", create_type=False)
GroundTruthSource = Enum(
    "specialist_review", "radiology_report", "follow_up_imaging", "histopathology",
    name="ground_truth_source", create_type=False,
)
ModelStatus = Enum(
    "production", "archived", "validation", "baseline", name="model_status", create_type=False
)
DeploymentEvent = Enum(
    "trainingCompleted", "validated", "deployedToProduction", "reverted", "archived",
    name="deployment_event", create_type=False,
)
DatasetSplit = Enum("train", "test", name="dataset_split", create_type=False)
DatasetImageSource = Enum(
    "kaggle", "user_upload", name="dataset_image_source", create_type=False
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(Text)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped[Role] = relationship(lazy="joined")


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(CHAR(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    name_es: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))
    longitude: Mapped[Decimal] = mapped_column(Numeric(8, 5))


class TumorClassCatalog(Base):
    __tablename__ = "tumor_classes"

    code: Mapped[str] = mapped_column(TumorClass, primary_key=True)
    label_es: Mapped[str] = mapped_column(String(60))
    label_en: Mapped[str] = mapped_column(String(60))
    color_hex: Mapped[str] = mapped_column(CHAR(7))
    display_order: Mapped[int] = mapped_column(SmallInteger)
    is_tumor: Mapped[bool] = mapped_column(Boolean)


class Model(Base):
    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(20))
    architecture: Mapped[str] = mapped_column(String(80))
    accuracy: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    f1_macro: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    precision_macro: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    recall_macro: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    auc: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    size_mb: Mapped[Decimal] = mapped_column(Numeric(9, 2))
    status: Mapped[str] = mapped_column(ModelStatus)
    weights_file_name: Mapped[str] = mapped_column(String(160))
    weights_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    training_images: Mapped[int | None] = mapped_column(Integer)
    test_images: Mapped[int | None] = mapped_column(Integer)
    active_since: Mapped[date | None] = mapped_column(Date)
    target_draft_version: Mapped[str | None] = mapped_column(String(20))
    previous_model_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("models.id"))
    mlflow_model_name: Mapped[str | None] = mapped_column(String(120))
    mlflow_model_version: Mapped[int | None] = mapped_column(Integer)
    mlflow_run_id: Mapped[str | None] = mapped_column(CHAR(32))
    mlflow_artifact_uri: Mapped[str | None] = mapped_column(Text)
    dataset_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    previous_model: Mapped["Model | None"] = relationship(remote_side=[id], lazy="selectin")
    class_metrics: Mapped[list["ModelClassMetric"]] = relationship(
        back_populates="model", lazy="selectin"
    )
    confusion_cells: Mapped[list["ModelConfusionCell"]] = relationship(
        back_populates="model", lazy="selectin"
    )
    deployments: Mapped[list["ModelDeployment"]] = relationship(
        back_populates="model", lazy="selectin"
    )


class ModelClassMetric(Base):
    __tablename__ = "model_class_metrics"

    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"), primary_key=True)
    class_code: Mapped[str] = mapped_column(TumorClass, primary_key=True)
    f1: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    precision: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    recall: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    support: Mapped[int | None] = mapped_column(Integer)

    model: Mapped[Model] = relationship(back_populates="class_metrics")


class ModelConfusionCell(Base):
    __tablename__ = "model_confusion_cells"

    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"), primary_key=True)
    actual_class: Mapped[str] = mapped_column(TumorClass, primary_key=True)
    predicted_class: Mapped[str] = mapped_column(TumorClass, primary_key=True)
    cell_count: Mapped[int] = mapped_column(Integer)

    model: Mapped[Model] = relationship(back_populates="confusion_cells")


class ModelDeployment(Base):
    __tablename__ = "model_deployments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"))
    event_type: Mapped[str] = mapped_column(DeploymentEvent)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_label: Mapped[str] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)

    model: Mapped[Model] = relationship(back_populates="deployments")


class DatasetImage(Base):
    __tablename__ = "dataset_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    stable_id: Mapped[str] = mapped_column(String(80), unique=True)
    class_code: Mapped[str] = mapped_column(TumorClass)
    split: Mapped[str] = mapped_column(DatasetSplit)
    file_name: Mapped[str] = mapped_column(String(160))
    storage_path: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    source: Mapped[str] = mapped_column(DatasetImageSource)
    origin_upload_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("uploads.id"))
    is_showcase: Mapped[bool] = mapped_column(Boolean)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DatasetSnapshot(Base):
    __tablename__ = "dataset_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    snapshot_code: Mapped[str] = mapped_column(String(40), unique=True)
    fingerprint: Mapped[str] = mapped_column(CHAR(64))
    split_salt: Mapped[str] = mapped_column(String(80))
    train_fraction: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    total_images: Mapped[int] = mapped_column(Integer)
    train_images: Mapped[int] = mapped_column(Integer)
    test_images: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    public_id: Mapped[str] = mapped_column(String(24), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(Text)
    checksum_sha256: Mapped[str] = mapped_column(CHAR(64), unique=True)
    country_code: Mapped[str] = mapped_column(ForeignKey("countries.code"))
    status: Mapped[str] = mapped_column(UploadStatus)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    added_to_dataset: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    country: Mapped[Country] = relationship(lazy="joined")
    prediction: Mapped["Prediction | None"] = relationship(
        back_populates="upload", lazy="selectin", uselist=False
    )
    ground_truths: Mapped[list["GroundTruthDiagnosis"]] = relationship(
        back_populates="upload", lazy="selectin"
    )

    @property
    def ground_truth_vigente(self) -> "GroundTruthDiagnosis | None":
        """Confirmación vigente. El DDL garantiza que hay como mucho una."""
        return next((g for g in self.ground_truths if g.deleted_at is None), None)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id"))
    model_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("models.id"))
    predicted_class: Mapped[str] = mapped_column(TumorClass)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    preprocess_label: Mapped[str] = mapped_column(String(80))
    preprocess_fingerprint: Mapped[str | None] = mapped_column(String(32))
    is_simulated: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    upload: Mapped[Upload] = relationship(back_populates="prediction")
    scores: Mapped[list["PredictionScore"]] = relationship(
        back_populates="prediction", lazy="selectin"
    )


class PredictionScore(Base):
    __tablename__ = "prediction_scores"

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("predictions.id"), primary_key=True
    )
    class_code: Mapped[str] = mapped_column(TumorClass, primary_key=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    prediction: Mapped[Prediction] = relationship(back_populates="scores")


class GroundTruthDiagnosis(Base):
    __tablename__ = "ground_truth_diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("uploads.id"))
    diagnosis: Mapped[str] = mapped_column(TumorClass)
    source: Mapped[str] = mapped_column(GroundTruthSource)
    confirmed_by: Mapped[str] = mapped_column(String(160))
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    upload: Mapped[Upload] = relationship(back_populates="ground_truths")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    actor_label: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
