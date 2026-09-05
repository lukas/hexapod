import base64
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import hashlib
from html import escape
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Literal, Mapping, Optional
from urllib.parse import urlsplit
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .auth import Principal, TokenAuth
from .calibrations import (
    CALIBRATION_DETAIL_OPENAPI,
    CALIBRATION_LIST_OPENAPI,
    CALIBRATION_REQUEST_OPENAPI,
    CalibrationArchive,
    CalibrationConflict,
    CalibrationError,
    CalibrationIntegrityError,
    CalibrationNotFound,
    CalibrationTooLarge,
    MAX_CALIBRATION_BYTES,
)
from .config import Settings
from .db import Store
from .layout_history import (
    LayoutHistoryConflict,
    LayoutHistoryError,
    LayoutHistoryIntegrityError,
    LayoutHistoryNotFound,
    LayoutHistoryUnavailable,
    TagLayoutHistory,
)
from .layout_history_page import layout_history_page
from .mobile import action_openapi, fetch_rl_doc_path, fetch_rl_document
from .runner import ExperimentRunner
from .tag_scan import (
    TagScanError,
    TagScanForbidden,
    TagScanNotFound,
    TagScanService,
)
from .tag_scan_page import tag_scan_page


class ExperimentSpec(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    duration_seconds: float = Field(gt=0)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ExperimentIn(ExperimentSpec):
    execution_mode: Literal["builtin", "external_guarded"] = "builtin"


class CompletedResultIn(ExperimentSpec):
    status: Literal["succeeded", "failed", "cancelled"] = "succeeded"
    error: str = Field(default="", max_length=4000)
    summary_markdown: str = Field(min_length=1, max_length=262_144)
    recorded_at: Optional[datetime] = None
    tag_layout_revision_id: Optional[str] = Field(
        default=None, min_length=1, max_length=160
    )


class TagLayoutActivationIn(BaseModel):
    expected_parent_revision_id: str = Field(min_length=1, max_length=160)
    expected_layout_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective_from: Optional[datetime] = None
    note: str = Field(default="", max_length=2000)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    auth = TokenAuth(settings.api_keys)
    if not auth.configured:
        raise RuntimeError("HEXAPOD_API_KEYS must configure at least one bearer token")
    store = Store(settings.data_dir / "lab.sqlite3")
    layout_history = TagLayoutHistory(
        store,
        settings.data_dir,
        layout_path=settings.tag_layout_path,
        pose_template_path=settings.tag_pose_template_path,
        floor_map_path=settings.tag_floor_map_path,
        part_map_path=settings.tag_part_map_path,
    )
    backfilled = layout_history.initialize()
    calibrations = CalibrationArchive(
        store,
        layout_provider=layout_history.resolve,
    )
    enabled_history = layout_history if layout_history.available else None
    runner = ExperimentRunner(store, settings, enabled_history)
    scan_layout = (
        layout_history.active_layout_path
        if layout_history.available else settings.tag_layout_path
    )
    scan_floor = (
        layout_history.active_floor_map_path
        if layout_history.available else settings.tag_floor_map_path
    )
    scan_parts = (
        layout_history.active_part_map_path
        if layout_history.available else settings.tag_part_map_path
    )
    tag_scans = TagScanService(
        settings.data_dir,
        audit_command=settings.tag_audit_command,
        layout_path=scan_layout,
        floor_map_path=scan_floor,
        part_map_path=scan_parts,
        max_photo_bytes=settings.max_tag_photo_bytes,
        max_photos=settings.max_tag_photos,
        baseline_provider=(
            layout_history.baseline_for_scan if layout_history.available else None
        ),
    )
    for experiment_id in backfilled:
        run_dir = settings.data_dir / "experiments" / experiment_id
        if run_dir.is_dir():
            runner._write_manifest(run_dir)
    viewer = auth.dependency("viewer")
    operator = auth.dependency("operator")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.auto_worker:
            runner.start()
        yield
        runner.stop()

    app = FastAPI(title="Hexapod Lab", version="0.1.0", lifespan=lifespan)
    app.state.store, app.state.runner, app.state.auth = store, runner, auth
    app.state.tag_scans = tag_scans
    app.state.layout_history = layout_history
    app.state.calibrations = calibrations

    def require_same_origin_action(
        request: Request, *, header: str, label: str
    ) -> None:
        """Block cross-origin writes against browser-cached Basic auth."""
        if request.headers.get(header) != "1":
            raise HTTPException(403, f"{label} request header is required")
        if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
            raise HTTPException(403, f"Cross-origin {label.lower()} request rejected")
        origin = request.headers.get("origin")
        if not origin:
            return
        allowed = {
            f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
        }
        if settings.public_base_url:
            parsed = urlsplit(settings.public_base_url)
            allowed.add(f"{parsed.scheme}://{parsed.netloc}")
        if origin.rstrip("/") not in allowed:
            raise HTTPException(403, f"Cross-origin {label.lower()} request rejected")

    def require_scan_request(request: Request) -> None:
        require_same_origin_action(
            request, header="x-hexapod-scan", label="Tag scan"
        )

    def require_layout_action(request: Request) -> None:
        require_same_origin_action(
            request, header="x-hexapod-lab", label="Layout activation"
        )

    def raise_scan_error(error: TagScanError) -> None:
        if isinstance(error, TagScanNotFound):
            raise HTTPException(404, str(error)) from error
        if isinstance(error, TagScanForbidden):
            raise HTTPException(403, str(error)) from error
        raise HTTPException(409, str(error)) from error

    def raise_layout_error(error: LayoutHistoryError) -> None:
        if isinstance(error, LayoutHistoryNotFound):
            raise HTTPException(404, str(error)) from error
        if isinstance(error, LayoutHistoryUnavailable):
            raise HTTPException(503, str(error)) from error
        if isinstance(error, LayoutHistoryIntegrityError):
            raise HTTPException(500, str(error)) from error
        if isinstance(error, LayoutHistoryConflict):
            raise HTTPException(409, str(error)) from error
        raise HTTPException(422, str(error)) from error

    def raise_calibration_error(error: CalibrationError) -> None:
        if isinstance(error, CalibrationNotFound):
            raise HTTPException(404, str(error)) from error
        if isinstance(error, CalibrationTooLarge):
            raise HTTPException(413, str(error)) from error
        if isinstance(error, CalibrationConflict):
            raise HTTPException(409, str(error)) from error
        if isinstance(error, CalibrationIntegrityError):
            raise HTTPException(500, str(error)) from error
        raise HTTPException(422, str(error)) from error

    def require_experiment(experiment_id: str):
        item = store.get(experiment_id)
        if not item:
            raise HTTPException(404, "Experiment not found")
        return item

    def artifact_path(experiment_id: str, filename: str) -> Path:
        require_experiment(experiment_id)
        if Path(filename).name != filename:
            raise HTTPException(400, "Invalid artifact name")
        path = settings.data_dir / "experiments" / experiment_id / filename
        if not path.is_file():
            raise HTTPException(404, "Artifact not found")
        return path

    def artifact_destination(experiment_id: str, filename: str) -> Path:
        item = require_experiment(experiment_id)
        if item["status"] not in {"succeeded", "failed", "cancelled"}:
            raise HTTPException(409, "Artifacts may only be attached to a completed result")
        reserved = {
            "manifest.json",
            "experiment.json",
            "vision-context.json",
            "apriltag-layout.snapshot.json",
            "apriltag-pose-config.snapshot.json",
            "floor-tag-map.snapshot.json",
            "hexapod-tag-map.snapshot.json",
        }
        if Path(filename).name != filename or filename in reserved:
            raise HTTPException(400, "Invalid artifact name")
        return settings.data_dir / "experiments" / experiment_id / filename

    def enrich(item):
        run_dir = settings.data_dir / "experiments" / item["id"]
        item = dict(item)
        artifacts = []
        if run_dir.exists():
            for path in sorted(run_dir.iterdir()):
                if not path.is_file():
                    continue
                relative_url = f"/api/experiments/{item['id']}/artifacts/{path.name}"
                artifacts.append({
                    "name": path.name,
                    "size": path.stat().st_size,
                    "content_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                    "url": relative_url,
                    "download_url": (
                        f"{settings.public_base_url}{relative_url}"
                        if settings.public_base_url else relative_url
                    ),
                })
        item["artifacts"] = artifacts
        item["events"] = store.events(item["id"])
        item["tag_layout_revision"] = (
            layout_history.experiment_revision(item["id"])
            if layout_history.available else None
        )
        item["tag_layout_candidate"] = None
        if (
            layout_history.available
            and item.get("parameters", {}).get("kind")
            == "apriltag_orientation_audit"
        ):
            item["tag_layout_candidate"] = next(
                (
                    revision
                    for revision in layout_history.list_revisions()
                    if revision.get("source_experiment_id") == item["id"]
                ),
                None,
            )
        return item

    def register_result(
        spec: CompletedResultIn,
        principal: Principal,
        experiment_id: Optional[str] = None,
        *,
        pinned_revision_id: Optional[str] = None,
        pinned_recorded_at: Optional[str] = None,
        pin_basis: Optional[str] = None,
    ):
        completion_sha256 = hashlib.sha256(
            json.dumps(
                spec.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        recorded_at = pinned_recorded_at
        revision_id = pinned_revision_id
        resolved_basis = pin_basis
        completion_time = datetime.now(timezone.utc)
        if layout_history.available:
            if pinned_recorded_at is None and spec.recorded_at is None:
                raise HTTPException(
                    422,
                    "recorded_at with a timezone is required for external evidence",
                )
            if spec.recorded_at and spec.recorded_at.tzinfo is None:
                raise HTTPException(422, "recorded_at must include a timezone")
            if (
                spec.recorded_at
                and spec.recorded_at.astimezone(timezone.utc)
                > completion_time
            ):
                raise HTTPException(422, "recorded_at cannot be in the future")
            if recorded_at is None:
                recorded_at = (
                    spec.recorded_at.astimezone(timezone.utc).isoformat()
                    if spec.recorded_at else completion_time.isoformat()
                )
            recording_start = datetime.fromisoformat(recorded_at)
            if (
                recording_start + timedelta(seconds=spec.duration_seconds)
                > completion_time
            ):
                raise HTTPException(
                    422,
                    "recorded_at plus duration_seconds cannot extend into the future",
                )
            if revision_id is None and spec.tag_layout_revision_id:
                try:
                    selected = layout_history.get_revision(
                        spec.tag_layout_revision_id, include_documents=False
                    )
                except LayoutHistoryError as error:
                    raise_layout_error(error)
                if not selected.get("effective_from"):
                    raise HTTPException(409, "Selected tag layout revision is not active")
                revision_id = selected["id"]
                resolved_basis = "explicit_revision"
            if revision_id is None:
                try:
                    selected = layout_history.resolve(recorded_at)
                except LayoutHistoryError as error:
                    raise_layout_error(error)
                if selected is None:
                    raise HTTPException(
                        409,
                        "No verified AprilTag layout exists for recorded_at; "
                        "select an explicit historical revision",
                    )
                revision_id = selected["id"]
                resolved_basis = (
                    "recorded_at" if spec.recorded_at else "registration_time_fallback"
                )
            if pinned_revision_id is None:
                boundary = selected.get("effective_to")
                if boundary:
                    start = datetime.fromisoformat(recorded_at)
                    end = start + timedelta(seconds=spec.duration_seconds)
                    if start < datetime.fromisoformat(boundary) < end:
                        raise HTTPException(
                            409,
                            "This recording spans an AprilTag layout change; "
                            "split it into separately pinned evidence segments",
                        )
        try:
            item = store.import_result(
                spec.model_dump(exclude={
                    "status", "error", "summary_markdown", "recorded_at",
                    "tag_layout_revision_id",
                }),
                principal.name,
                spec.status,
                spec.error or None,
                experiment_id=experiment_id,
                tag_layout_revision_id=revision_id,
                tag_layout_recorded_at=recorded_at,
                tag_layout_pin_basis=resolved_basis or "unavailable",
                completion_sha256=completion_sha256,
            )
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        run_dir = settings.data_dir / "experiments" / item["id"]
        run_dir.mkdir(parents=True, exist_ok=experiment_id is not None)
        if layout_history.available:
            try:
                layout_history.materialize_experiment(run_dir, item["id"])
            except LayoutHistoryError as error:
                raise_layout_error(error)
        recorded_item = dict(item)
        recorded_item["tag_layout_revision"] = (
            layout_history.experiment_revision(item["id"])
            if layout_history.available else None
        )
        (run_dir / "experiment.json").write_text(
            json.dumps(recorded_item, indent=2) + "\n", encoding="utf-8"
        )
        (run_dir / "summary.md").write_text(spec.summary_markdown, encoding="utf-8")
        runner._write_manifest(run_dir)
        return enrich(item)

    @app.get("/healthz")
    def health():
        return {"ok": True, "driver": settings.driver}

    @app.get("/api/experiments")
    def list_experiments(_: Principal = Depends(viewer)):
        return [enrich(item) for item in store.list()]

    @app.post("/api/experiments", status_code=202)
    def submit(spec: ExperimentIn, principal: Principal = Depends(operator)):
        if spec.duration_seconds > settings.max_duration_seconds:
            raise HTTPException(422, f"duration_seconds exceeds limit of {settings.max_duration_seconds}")
        item = store.create(spec.model_dump(), principal.name)
        if spec.execution_mode == "builtin":
            runner.wake()
        return enrich(item)

    @app.post("/api/results", status_code=201)
    def import_result(spec: CompletedResultIn, principal: Principal = Depends(operator)):
        return register_result(spec, principal)

    @app.post("/api/experiments/{experiment_id}/result")
    def complete_external_experiment(
        experiment_id: str,
        spec: CompletedResultIn,
        principal: Principal = Depends(operator),
    ):
        """Attach a guarded runner's terminal result to its waiting queue record."""
        require_experiment(experiment_id)
        return register_result(spec, principal, experiment_id=experiment_id)

    @app.get("/api/calibrations", openapi_extra=CALIBRATION_LIST_OPENAPI)
    def list_calibrations(
        limit: int = Query(default=100, ge=1, le=100),
        _: Principal = Depends(viewer),
    ):
        try:
            return calibrations.list(limit)
        except CalibrationError as error:
            raise_calibration_error(error)

    @app.get(
        "/api/calibrations/{calibration_id}",
        openapi_extra=CALIBRATION_DETAIL_OPENAPI,
    )
    def get_calibration(
        calibration_id: str,
        _: Principal = Depends(viewer),
    ):
        try:
            return calibrations.get(calibration_id)
        except CalibrationError as error:
            raise_calibration_error(error)

    @app.post(
        "/api/calibrations",
        status_code=201,
        openapi_extra=CALIBRATION_REQUEST_OPENAPI,
    )
    @app.post(
        "/api/calibrations/import",
        status_code=201,
        openapi_extra=CALIBRATION_REQUEST_OPENAPI,
    )
    async def import_calibration(
        request: Request,
        principal: Principal = Depends(operator),
    ):
        media_type = request.headers.get("content-type", "").partition(";")[0]
        if media_type.strip().casefold() != "application/json":
            raise HTTPException(415, "Calibration request must use application/json")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                announced_size = int(content_length)
            except ValueError as exc:
                raise HTTPException(400, "Invalid Content-Length") from exc
            if announced_size < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if announced_size > MAX_CALIBRATION_BYTES:
                raise HTTPException(413, "Calibration request exceeds the 2 MiB limit")
        chunks = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > MAX_CALIBRATION_BYTES:
                raise HTTPException(
                    413, "Calibration request exceeds the 2 MiB limit"
                )
            chunks.append(chunk)
        body = b"".join(chunks)
        try:
            return calibrations.import_bytes(
                body,
                created_by=principal.name,
                idempotency_key=request.headers.get("idempotency-key"),
            )
        except CalibrationError as error:
            raise_calibration_error(error)

    @app.get("/api/experiments/{experiment_id}")
    def get_experiment(experiment_id: str, _: Principal = Depends(viewer)):
        return enrich(require_experiment(experiment_id))

    @app.get("/api/tag-layout-revisions")
    def list_tag_layout_revisions(_: Principal = Depends(viewer)):
        return (
            layout_history.list_revisions()
            if layout_history.available else []
        )

    @app.get("/api/tag-layout-revisions/{revision_id}")
    def get_tag_layout_revision(
        revision_id: str, _: Principal = Depends(viewer)
    ):
        try:
            return layout_history.get_revision(revision_id)
        except LayoutHistoryError as error:
            raise_layout_error(error)

    @app.get("/api/tag-layout-at")
    def get_tag_layout_at(
        at_time: datetime = Query(alias="at"),
        _: Principal = Depends(viewer),
    ):
        if at_time.tzinfo is None:
            raise HTTPException(422, "at must include a timezone")
        try:
            revision = layout_history.resolve(at_time.astimezone(timezone.utc))
        except LayoutHistoryError as error:
            raise_layout_error(error)
        if revision is None:
            raise HTTPException(404, "No verified AprilTag layout exists at that time")
        try:
            return layout_history.get_revision(revision["id"])
        except LayoutHistoryError as error:
            raise_layout_error(error)

    @app.post("/api/tag-layout-revisions/{revision_id}/activate")
    def activate_tag_layout_revision(
        revision_id: str,
        spec: TagLayoutActivationIn,
        request: Request,
        principal: Principal = Depends(operator),
    ):
        require_layout_action(request)
        idempotency_key = request.headers.get("idempotency-key", "").strip()
        if not idempotency_key or len(idempotency_key) > 200:
            raise HTTPException(400, "A valid Idempotency-Key header is required")
        if spec.effective_from and spec.effective_from.tzinfo is None:
            raise HTTPException(422, "effective_from must include a timezone")
        try:
            return layout_history.activate(
                revision_id,
                activated_by=principal.name,
                expected_parent_revision_id=spec.expected_parent_revision_id,
                expected_layout_sha256=spec.expected_layout_sha256,
                idempotency_key=idempotency_key,
                effective_from=(
                    spec.effective_from.astimezone(timezone.utc).isoformat()
                    if spec.effective_from else None
                ),
                note=spec.note,
            )
        except LayoutHistoryError as error:
            raise_layout_error(error)

    @app.post("/api/experiments/{experiment_id}/cancel")
    def cancel(experiment_id: str, _: Principal = Depends(operator)):
        item = store.cancel(experiment_id)
        if not item:
            raise HTTPException(404, "Experiment not found")
        return enrich(item)

    @app.get("/api/experiments/{experiment_id}/artifacts/{filename}")
    def artifact(experiment_id: str, filename: str, _: Principal = Depends(viewer)):
        path = artifact_path(experiment_id, filename)
        return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0])

    @app.get("/api/mobile/openapi.json", include_in_schema=False)
    def mobile_openapi():
        return action_openapi(settings.public_base_url)

    @app.get("/api/mobile/overview")
    def mobile_overview(_: Principal = Depends(viewer)):
        return {
            "rl_brief_markdown": fetch_rl_document("brief"),
            "robot_lab_experiments": [enrich(item) for item in store.list()[:25]],
            "read_only": True,
        }

    @app.get("/api/mobile/rl/{document}")
    def mobile_rl_document(document: str, _: Principal = Depends(viewer)):
        return {"document": document, "markdown": fetch_rl_document(document)}

    @app.get("/api/mobile/rl/doc/{path:path}")
    def mobile_rl_detailed_document(path: str, _: Principal = Depends(viewer)):
        return {"path": path, "markdown": fetch_rl_doc_path(path)}

    @app.get("/api/mobile/experiments")
    def mobile_experiments(_: Principal = Depends(viewer)):
        return [enrich(item) for item in store.list()]

    @app.get("/api/mobile/experiments/{experiment_id}")
    def mobile_experiment(experiment_id: str, _: Principal = Depends(viewer)):
        return enrich(require_experiment(experiment_id))

    @app.put("/api/experiments/{experiment_id}/artifacts/{filename}", status_code=201)
    async def upload_artifact(
        experiment_id: str,
        filename: str,
        request: Request,
        _: Principal = Depends(operator),
    ):
        destination = artifact_destination(experiment_id, filename)
        if destination.exists():
            raise HTTPException(409, "Artifact already exists")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                announced_size = int(content_length)
            except ValueError as exc:
                raise HTTPException(400, "Invalid Content-Length") from exc
            if announced_size < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if announced_size > settings.max_artifact_bytes:
                raise HTTPException(413, "Artifact exceeds configured size limit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.upload")
        written = 0
        try:
            with temporary.open("xb") as output:
                async for chunk in request.stream():
                    written += len(chunk)
                    if written > settings.max_artifact_bytes:
                        raise HTTPException(413, "Artifact exceeds configured size limit")
                    output.write(chunk)
            try:
                # Linking a fully written temporary file is atomic and, unlike
                # Path.replace(), cannot overwrite a racing upload.
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise HTTPException(409, "Artifact already exists") from exc
        finally:
            temporary.unlink(missing_ok=True)
        runner._write_manifest(destination.parent)
        return next(
            artifact for artifact in enrich(require_experiment(experiment_id))["artifacts"]
            if artifact["name"] == filename
        )

    @app.get("/api/tag-scans/{scan_id}")
    def tag_scan_state(scan_id: str, principal: Principal = Depends(viewer)):
        try:
            return tag_scans.get(scan_id, principal.name, principal.role)
        except TagScanError as error:
            raise_scan_error(error)

    @app.post("/api/tag-scans", status_code=201)
    def start_tag_scan(
        request: Request,
        principal: Principal = Depends(viewer),
    ):
        require_scan_request(request)
        try:
            return tag_scans.create(principal.name)
        except TagScanError as error:
            raise_scan_error(error)

    @app.post("/api/tag-scans/{scan_id}/photos")
    async def add_tag_scan_photo(
        scan_id: str,
        request: Request,
        principal: Principal = Depends(viewer),
    ):
        require_scan_request(request)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                announced_size = int(content_length)
            except ValueError as exc:
                raise HTTPException(400, "Invalid Content-Length") from exc
            if announced_size < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if announced_size > settings.max_tag_photo_bytes:
                raise HTTPException(413, "Tag photo exceeds the configured size limit")
        chunks = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > settings.max_tag_photo_bytes:
                raise HTTPException(413, "Tag photo exceeds the configured size limit")
            chunks.append(chunk)
        content = b"".join(chunks)
        try:
            return await run_in_threadpool(
                tag_scans.add_photo,
                scan_id,
                principal.name,
                principal.role,
                content,
                request.headers.get("content-type", ""),
            )
        except TagScanError as error:
            raise_scan_error(error)

    @app.post("/api/tag-scans/{scan_id}/finish")
    async def finish_tag_scan(
        scan_id: str,
        request: Request,
        principal: Principal = Depends(viewer),
    ):
        require_scan_request(request)
        try:
            completed = await run_in_threadpool(
                tag_scans.finalize, scan_id, principal.name, principal.role
            )
            existing_id = completed["state"].get("experiment_id")
            if existing_id:
                if layout_history.available:
                    try:
                        layout_history.record_candidate(
                            existing_id,
                            completed["proposal"],
                            completed["candidate"],
                            principal.name,
                            observed_at=completed["proposal"].get("created_at"),
                        )
                        run_dir = settings.data_dir / "experiments" / existing_id
                        layout_history.materialize_experiment(run_dir, existing_id)
                        runner._write_manifest(run_dir)
                    except LayoutHistoryError as error:
                        raise_layout_error(error)
                return {
                    "scan": completed["state"],
                    "experiment": enrich(require_experiment(existing_id)),
                }
            proposal = completed["proposal"]
            spec = CompletedResultIn(
                name="AprilTag orientation walk-around",
                description=(
                    "Phone-camera audit of Hexapod 1 tag identity and mount "
                    "orientation; advisory evidence only."
                ),
                duration_seconds=completed["duration_seconds"],
                parameters={
                    "kind": "apriltag_orientation_audit",
                    "scan_id": scan_id,
                    "apply_state": "proposed",
                    "ready_for_human_review": proposal["ready_for_human_review"],
                    "changed_tag_ids": proposal["changed_tag_ids"],
                    "unresolved_tag_ids": proposal["unresolved_tag_ids"],
                    "robot_motion": False,
                    "servo_zeros_changed": False,
                    "canonical_configuration_changed": False,
                    "baseline_revision_id": completed["state"].get(
                        "baseline_revision_id"
                    ),
                },
                summary_markdown=completed["summary_markdown"],
            )
            # Reuse the scan UUID for the Lab result. Finish is then idempotent
            # across double taps, network retries, and process restarts.
            item = register_result(
                spec,
                principal,
                experiment_id=scan_id,
                pinned_revision_id=completed["state"].get(
                    "baseline_revision_id"
                ),
                pinned_recorded_at=completed["state"]["created_at"],
                pin_basis="tag_scan_start",
            )
            run_dir = settings.data_dir / "experiments" / item["id"]
            scan_state = await run_in_threadpool(
                tag_scans.attach_to_experiment,
                scan_id,
                principal.name,
                principal.role,
                item["id"],
                run_dir,
            )
            if layout_history.available:
                try:
                    layout_history.record_candidate(
                        item["id"],
                        completed["proposal"],
                        completed["candidate"],
                        principal.name,
                        observed_at=completed["proposal"].get("created_at"),
                    )
                except LayoutHistoryError as error:
                    raise_layout_error(error)
            runner._write_manifest(run_dir)
            return {
                "scan": scan_state,
                "experiment": enrich(require_experiment(item["id"])),
            }
        except TagScanError as error:
            raise_scan_error(error)

    @app.post("/mcp")
    async def mcp(request: Request, principal: Principal = Depends(viewer)):
        try:
            message = await request.json()
        except (UnicodeDecodeError, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                },
            )
        if not isinstance(message, Mapping):
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid Request"},
                },
            )
        rpc_id, method = message.get("id"), message.get("method")
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hexapod-lab", "version": "0.1.0"}}}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
        if method == "notifications/initialized":
            return JSONResponse(status_code=202, content={})
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": mcp_tools()}}
        if method == "tools/call":
            params = message.get("params", {})
            try:
                if not isinstance(params, Mapping):
                    raise ValueError("Tool params must be an object")
                result = call_mcp_tool(params.get("name", ""), params.get("arguments", {}), principal,
                                       store, runner, settings, enrich, artifact_path,
                                       register_result, layout_history, calibrations)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": result}
            except (ValueError, HTTPException) as exc:
                detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {"isError": True,
                        "content": [{"type": "text", "text": str(detail)}]}}
        return JSONResponse(status_code=400, content={"jsonrpc": "2.0", "id": rpc_id,
                            "error": {"code": -32601, "message": "Method not found"}})

    @app.get("/", response_class=HTMLResponse)
    def dashboard(_: Principal = Depends(viewer)):
        cards = "".join(experiment_card(item) for item in store.list()) or "<p>No experiments yet.</p>"
        tools = (
            "<div class='tool-links'>"
            "<a class='tool-link' href='/tag-scan'>Scan AprilTags <span>→</span></a>"
            "<a class='tool-link' href='/tag-layout-history'>Tag history <span>→</span></a>"
            "</div>"
        )
        return page("Hexapod Lab", f"<div class='dashboard-head'><div><h1>Hexapod Lab</h1><p class='lede'>Experiment queue and durable run evidence</p></div>{tools}</div><main>{cards}</main>")

    @app.get("/tag-scan", response_class=HTMLResponse)
    def tag_scan_site(_: Principal = Depends(viewer)):
        return tag_scan_page(
            available=tag_scans.available,
            message="The camera page is installed, but its AprilTag analyzer is offline.",
        )

    @app.get("/tag-layout-history", response_class=HTMLResponse)
    def tag_layout_history_site(_: Principal = Depends(viewer)):
        revisions = (
            layout_history.list_revisions() if layout_history.available else []
        )
        return page(
            "AprilTag layout history",
            layout_history_page(revisions, available=layout_history.available),
        )

    @app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
    def result_page(
        experiment_id: str, principal: Principal = Depends(viewer)
    ):
        item = enrich(require_experiment(experiment_id))
        run_dir = settings.data_dir / "experiments" / experiment_id
        summary_path = run_dir / "summary.md"
        summary = escape(summary_path.read_text()) if summary_path.exists() else "Run summary is not available yet."
        video = next((a for a in item["artifacts"] if a["content_type"].startswith("video/")), None)
        video_html = f"<video controls preload='metadata' src='{escape(video['url'])}'></video>" if video else ""
        artifacts = "".join(f"<li><a href='{escape(a['url'])}'>{escape(a['name'])}</a> ({a['size']} bytes)</li>" for a in item["artifacts"])
        revision = item.get("tag_layout_revision")
        if revision:
            revision_html = (
                "<section class='context'><h2>Vision context</h2>"
                "<p>This evidence is permanently pinned to "
                f"<code>{escape(str(revision.get('id', 'unknown')))}</code> "
                f"(effective {escape(str(revision.get('effective_from', 'unknown')))}). "
                "Later tag changes cannot reinterpret this recording. "
                "<a href='/tag-layout-history'>View the timeline.</a></p></section>"
            )
        else:
            revision_html = ""

        candidate = item.get("tag_layout_candidate")
        review_html = ""
        if candidate:
            changes = candidate.get("changed_tag_ids") or []
            chips = " ".join(
                f"<code>#{escape(str(tag_id))}</code>" for tag_id in changes
            ) or "none"
            review_ready = bool(candidate.get("review_ready"))
            active = bool(candidate.get("effective_from"))
            candidate_status = str(candidate.get("status") or "")
            actionable = review_ready and candidate_status == "ready_for_review"
            state = (
                "active" if active else
                "ready to activate" if actionable else
                "stale—rescan against the current layout"
                if candidate_status == "stale" else "incomplete"
            )
            diffs = ""
            proposal_path = run_dir / "tag-orientation-proposal.json"
            if proposal_path.is_file():
                try:
                    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                    rows = []
                    for orientation in proposal.get("orientations", []):
                        if orientation.get("status") != "change":
                            continue
                        rows.append(
                            "<tr>"
                            f"<td>#{escape(str(orientation.get('id')))}</td>"
                            f"<td><code>{escape(json.dumps(orientation.get('previous_frame_from_tag'), sort_keys=True))}</code></td>"
                            f"<td><code>{escape(json.dumps(orientation.get('proposed_frame_from_tag'), sort_keys=True))}</code></td>"
                            f"<td>{escape(str(orientation.get('confidence', '')))}</td>"
                            "</tr>"
                        )
                    if rows:
                        diffs = (
                            "<div class='table-wrap'><table><thead><tr><th>Tag</th>"
                            "<th>Before</th><th>Proposed</th><th>Evidence</th>"
                            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
                        )
                except (OSError, json.JSONDecodeError):
                    diffs = "<p>Proposal detail could not be read.</p>"
            controls = ""
            if actionable and not active and principal.role in {"operator", "admin"}:
                revision_id_js = json.dumps(str(candidate["id"])).replace("<", "\\u003c")
                parent_id_js = json.dumps(
                    str(candidate.get("parent_revision_id") or "")
                ).replace("<", "\\u003c")
                sha_js = json.dumps(str(candidate["layout_sha256"])).replace(
                    "<", "\\u003c"
                )
                controls = f"""
                <div class='activation'>
                  <label><input id='confirm-layout' type='checkbox'> I checked the proposed rotations against the photos.</label>
                  <label for='activation-note'>Note (optional)</label>
                  <textarea id='activation-note' maxlength='2000' placeholder='Repair or tag-placement note'></textarea>
                  <button id='activate-layout' type='button'>Activate now</button>
                  <p id='activation-result' role='status'></p>
                </div>
                <script>
                (()=>{{const button=document.getElementById('activate-layout');button.addEventListener('click',async()=>{{
                  const result=document.getElementById('activation-result');
                  if(!document.getElementById('confirm-layout').checked){{result.textContent='Check the review box first.';return}}
                  button.disabled=true;result.textContent='Activating…';
                  try{{const response=await fetch('/api/tag-layout-revisions/'+{revision_id_js}+'/activate',{{
                    method:'POST',headers:{{'Content-Type':'application/json','X-Hexapod-Lab':'1','Idempotency-Key':crypto.randomUUID()}},
                    body:JSON.stringify({{expected_parent_revision_id:{parent_id_js},expected_layout_sha256:{sha_js},note:document.getElementById('activation-note').value}})
                  }});const payload=await response.json();if(!response.ok)throw new Error(payload.detail||'Activation failed');
                  result.textContent='Active. Future recordings now use this revision.';setTimeout(()=>location.reload(),700)
                  }}catch(error){{result.textContent=error.message;button.disabled=false}}
                }})}})();
                </script>"""
            review_html = (
                "<section class='review'><h2>AprilTag orientation proposal</h2>"
                f"<p>Status: <strong>{escape(state)}</strong> · changed tags: {chips}</p>"
                f"{diffs}{controls}</section>"
            )
        status_label = escape(item["status"].replace("_", " "))
        body = f"<a href='/'>← Queue</a><h1>{escape(item['name'])}</h1><span class='status {item['status']}'>{status_label}</span>{video_html}{revision_html}{review_html}<h2>Summary</h2><pre>{summary}</pre><h2>Artifacts</h2><ul>{artifacts}</ul>"
        return page(item["name"], body)

    default_openapi = app.openapi

    def documented_openapi():
        schema = default_openapi()
        security_schemes = schema.setdefault("components", {}).setdefault(
            "securitySchemes", {}
        )
        security_schemes.update({
            "BearerAuth": {"type": "http", "scheme": "bearer"},
            "BasicAuth": {"type": "http", "scheme": "basic"},
        })
        calibration_operations = (
            ("/api/calibrations", "get"),
            ("/api/calibrations", "post"),
            ("/api/calibrations/import", "post"),
            ("/api/calibrations/{calibration_id}", "get"),
        )
        for path, method in calibration_operations:
            operation = schema["paths"][path][method]
            operation["parameters"] = [
                parameter
                for parameter in operation.get("parameters", [])
                if not (
                    parameter.get("in") == "header"
                    and parameter.get("name", "").casefold() == "authorization"
                )
            ]
        return schema

    app.openapi = documented_openapi
    return app


def mcp_tools():
    return [
        {"name": "list_experiments", "description": "List recent robot experiments and their status.",
         "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}}},
        {"name": "get_experiment", "description": "Get one experiment, events, and artifact links.",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}}, "required": ["experiment_id"]}},
        {"name": "queue_experiment", "description": "Queue a bounded experiment. Use execution_mode=external_guarded for physical hardware work that must wait for an operator and an independent safety-guarded runner; the built-in worker will never claim it (operator role required).",
         "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"},
          "duration_seconds": {"type": "number", "exclusiveMinimum": 0}, "parameters": {"type": "object"},
          "execution_mode": {"type": "string", "enum": ["builtin", "external_guarded"], "default": "builtin"}},
          "required": ["name", "duration_seconds"]}},
        {"name": "cancel_experiment", "description": "Cancel a queued, waiting-for-operator, or running experiment (operator role required).",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}}, "required": ["experiment_id"]}},
        {"name": "register_result", "description": "Register a completed run from an external guarded robot runner; upload large artifacts through the returned authenticated HTTP API URLs (operator role required).",
         "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"},
          "duration_seconds": {"type": "number", "exclusiveMinimum": 0}, "parameters": {"type": "object"},
          "status": {"type": "string", "enum": ["succeeded", "failed", "cancelled"]}, "error": {"type": "string"},
          "summary_markdown": {"type": "string"},
          "recorded_at": {"type": "string", "format": "date-time", "description": "Original evidence capture time; include its timezone."},
          "tag_layout_revision_id": {"type": "string", "description": "Optional explicit active revision for ambiguous historical evidence."}}, "required": ["name", "duration_seconds", "summary_markdown", "recorded_at"]}},
        {"name": "complete_external_experiment", "description": "Attach a terminal result from an independent safety-guarded runner to an existing waiting-for-operator experiment, preserving its exact ID. Exact retries are idempotent; mismatched specs or results are rejected (operator role required).",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"},
          "name": {"type": "string"}, "description": {"type": "string"},
          "duration_seconds": {"type": "number", "exclusiveMinimum": 0}, "parameters": {"type": "object"},
          "status": {"type": "string", "enum": ["succeeded", "failed", "cancelled"]}, "error": {"type": "string"},
          "summary_markdown": {"type": "string"},
          "recorded_at": {"type": "string", "format": "date-time", "description": "Original evidence capture time; include its timezone."},
          "tag_layout_revision_id": {"type": "string", "description": "Optional explicit active revision for ambiguous historical evidence."}},
          "required": ["experiment_id", "name", "duration_seconds", "summary_markdown", "recorded_at"]}},
        {"name": "read_artifact", "description": "Read a text artifact, or a small binary artifact as base64.",
         "inputSchema": {"type": "object", "properties": {"experiment_id": {"type": "string"}, "filename": {"type": "string"}},
          "required": ["experiment_id", "filename"]}},
        {"name": "list_tag_layout_revisions", "description": "List immutable AprilTag layout revisions and their effective intervals.",
         "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}}}},
        {"name": "get_tag_layout", "description": "Read the exact AprilTag layout by revision, experiment pin, or historical timestamp.",
         "inputSchema": {"type": "object", "properties": {
             "revision_id": {"type": "string"},
             "experiment_id": {"type": "string"},
             "at": {"type": "string", "format": "date-time"}
         }, "minProperties": 1, "maxProperties": 1}},
        {"name": "list_calibrations", "description": "List immutable calibration records, newest first.",
         "inputSchema": {"type": "object", "properties": {
             "limit": {"type": "integer", "minimum": 1, "maximum": 100}
         }}},
        {"name": "get_calibration", "description": "Read one immutable calibration report and its optional archived pose config.",
         "inputSchema": {"type": "object", "properties": {
             "calibration_id": {"type": "string"}
         }, "required": ["calibration_id"]}},
    ]


def call_mcp_tool(
    name, args, principal, store, runner, settings, enrich, artifact_path,
    register_result, layout_history, calibrations,
):
    if not isinstance(args, Mapping):
        raise ValueError("Tool arguments must be an object")
    if name == "list_experiments":
        limit = min(max(int(args.get("limit", 25)), 1), 100)
        data = [enrich(i) for i in store.list(limit)]
    elif name == "get_experiment":
        item = store.get(args["experiment_id"])
        if not item:
            raise ValueError("Experiment not found")
        data = enrich(item)
    elif name == "queue_experiment":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        spec = ExperimentIn(**args)
        if spec.duration_seconds > settings.max_duration_seconds:
            raise ValueError("Experiment duration exceeds configured maximum")
        data = enrich(store.create(spec.model_dump(), principal.name))
        if spec.execution_mode == "builtin":
            runner.wake()
    elif name == "cancel_experiment":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        data = store.cancel(args["experiment_id"])
        if not data:
            raise ValueError("Experiment not found")
        data = enrich(data)
    elif name == "register_result":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        data = register_result(CompletedResultIn(**args), principal)
    elif name == "complete_external_experiment":
        if principal.role == "viewer":
            raise ValueError("Operator role required")
        completion_args = dict(args)
        experiment_id = completion_args.pop("experiment_id")
        if not store.get(experiment_id):
            raise ValueError("Experiment not found")
        data = register_result(
            CompletedResultIn(**completion_args), principal, experiment_id=experiment_id
        )
    elif name == "read_artifact":
        path = artifact_path(args["experiment_id"], args["filename"])
        if path.stat().st_size > 1024 * 1024:
            item = enrich(store.get(args["experiment_id"]))
            artifact = next(a for a in item["artifacts"] if a["name"] == path.name)
            data = {"name": path.name, "size": path.stat().st_size,
                    "url": artifact["download_url"],
                    "message": "Artifact is larger than 1 MiB; use its authenticated HTTP API URL."}
        elif (mimetypes.guess_type(path.name)[0] or "").startswith(("text/", "application/json")) or path.suffix in {".md", ".jsonl", ".log"}:
            data = {"name": path.name, "encoding": "utf-8", "data": path.read_text(errors="replace")}
        else:
            data = {"name": path.name, "encoding": "base64", "data": base64.b64encode(path.read_bytes()).decode()}
    elif name == "list_tag_layout_revisions":
        data = (
            layout_history.list_revisions(
                min(max(int(args.get("limit", 25)), 1), 100)
            )
            if layout_history.available else []
        )
    elif name == "get_tag_layout":
        selectors = [
            key for key in ("revision_id", "experiment_id", "at")
            if args.get(key)
        ]
        if len(selectors) != 1:
            raise ValueError(
                "Provide exactly one of revision_id, experiment_id, or at"
            )
        try:
            if selectors[0] == "revision_id":
                data = layout_history.get_revision(args["revision_id"])
            elif selectors[0] == "experiment_id":
                pinned = layout_history.experiment_revision(args["experiment_id"])
                if not pinned:
                    raise ValueError("Experiment has no verified layout pin")
                data = layout_history.get_revision(pinned["id"])
            else:
                raw_time = str(args["at"])
                try:
                    parsed_time = datetime.fromisoformat(
                        raw_time[:-1] + "+00:00"
                        if raw_time.endswith("Z") else raw_time
                    )
                except ValueError as exc:
                    raise ValueError("at must be an RFC 3339 timestamp") from exc
                if parsed_time.tzinfo is None:
                    raise ValueError("at must include a timezone")
                resolved = layout_history.resolve(parsed_time)
                if resolved is None:
                    raise ValueError("No verified layout exists at that time")
                data = layout_history.get_revision(resolved["id"])
        except LayoutHistoryError as exc:
            raise ValueError(str(exc)) from exc
    elif name == "list_calibrations":
        try:
            limit = int(args.get("limit", 25))
            data = calibrations.list(
                min(max(limit, 1), 100)
            )
        except (TypeError, ValueError, CalibrationError) as exc:
            raise ValueError(str(exc)) from exc
    elif name == "get_calibration":
        calibration_id = args.get("calibration_id")
        if (
            not isinstance(calibration_id, str)
            or not calibration_id.strip()
            or len(calibration_id) > 200
        ):
            raise ValueError("calibration_id must be a non-empty string")
        try:
            data = calibrations.get(calibration_id)
        except CalibrationError as exc:
            raise ValueError(str(exc)) from exc
    else:
        raise ValueError("Unknown tool")
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "structuredContent": data}


def experiment_card(item):
    status_label = escape(item["status"].replace("_", " "))
    return f"<article><div><span class='status {item['status']}'>{status_label}</span><h2><a href='/experiments/{item['id']}'>{escape(item['name'])}</a></h2><p>{escape(item['description'])}</p></div><small>{escape(item['created_at'])} · {item['duration_seconds']}s</small></article>"


def page(title, body):
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>%s</title><style>
    :root{color-scheme:dark;--bg:#0c1110;--panel:#141c19;--ink:#e8f1ec;--muted:#94a69d;--lime:#b7f34a;--line:#2a3932}*{box-sizing:border-box}body{max-width:980px;margin:0 auto;padding:48px 24px;background:var(--bg);color:var(--ink);font:16px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}h1{font-size:clamp(2rem,7vw,4.8rem);letter-spacing:-.06em;line-height:.95;margin:.5em 0}.lede{color:var(--muted);font-size:1.1rem;margin:0}.dashboard-head{display:flex;align-items:end;justify-content:space-between;gap:2rem;margin-bottom:3rem}.tool-links{display:grid;gap:.6rem}.tool-link{display:flex;align-items:center;justify-content:space-between;gap:.8rem;text-decoration:none;border:1px solid var(--line);border-radius:14px;padding:.75rem 1rem;background:var(--panel);white-space:nowrap}.tool-link span{font-size:1.4rem}a{color:var(--lime)}article{display:flex;align-items:start;justify-content:space-between;gap:2rem;border-top:1px solid var(--line);padding:1.5rem 0}article h2{margin:.4rem 0;font-size:1.25rem}article p,small{color:var(--muted)}.status{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:.15rem .55rem;font-size:.72rem;text-transform:uppercase}.succeeded{color:var(--lime)}.failed{color:#ff756b}.running{color:#71caff}.queued{color:#ffd56a}.waiting_for_operator{color:#e6a8ff;border-color:#70477f}video{display:block;width:100%%;margin:2rem 0;border:1px solid var(--line);background:#000}pre{white-space:pre-wrap;background:var(--panel);padding:1.2rem;border:1px solid var(--line);overflow:auto}ul{line-height:2}.context,.review{margin:2rem 0;padding:1.2rem;border:1px solid var(--line);border-radius:16px;background:var(--panel)}.context h2,.review h2{margin-top:0}.table-wrap{overflow:auto}table{width:100%%;border-collapse:collapse;font-size:.76rem}th,td{padding:.65rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}td code{white-space:normal}.activation{display:grid;gap:.7rem;margin-top:1.2rem;padding-top:1.2rem;border-top:1px solid var(--line)}textarea{min-height:76px;padding:.7rem;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink);font:inherit}button{padding:.8rem 1rem;border:0;border-radius:10px;background:var(--lime);color:#142006;font:inherit;font-weight:800;cursor:pointer}button:disabled{opacity:.55}@media(max-width:650px){article{display:block}small{display:block;margin-top:1rem}.dashboard-head{display:block}.tool-links{margin-top:1.5rem}.tool-link{justify-content:space-between}}
    </style></head><body>%s</body></html>""" % (escape(title), body)


def run():
    import uvicorn
    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.bind, port=settings.port)
