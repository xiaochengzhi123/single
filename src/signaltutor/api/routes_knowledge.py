from __future__ import annotations

import json
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from signaltutor.api.auth_dependencies import AdminAccess, CurrentUser
from signaltutor.api.dependencies import Services, get_services
from signaltutor.schemas.knowledge import (
    KnowledgeEntry,
    KnowledgeEntryCreate,
    KnowledgeEntryUpdate,
    KnowledgeImportResponse,
    KnowledgeKind,
)

router = APIRouter(prefix="/api/v1", tags=["knowledge"])
MAX_KNOWLEDGE_FILE_BYTES = 20 * 1024 * 1024


def _topics(value: str) -> list[str]:
    return list(
        dict.fromkeys(
            part.strip()
            for part in value.replace("，", ",").replace("、", ",").split(",")
            if part.strip()
        )
    )[:20]


def _chunks(value: str, limit: int = 2400) -> list[str]:
    paragraphs = [part.strip() for part in value.replace("\r\n", "\n").split("\n\n")]
    chunks: list[str] = []
    current = ""
    for paragraph in (part for part in paragraphs if part):
        pieces = [paragraph[index : index + limit] for index in range(0, len(paragraph), limit)]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip()
            if current and len(candidate) > limit:
                chunks.append(current)
                current = piece
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def _structured_entries(raw: bytes, suffix: str) -> list[KnowledgeEntryCreate]:
    text = raw.decode("utf-8-sig")
    if suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        data = json.loads(text)
        rows = data.get("entries", []) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("JSON 顶层必须是数组，或包含 entries 数组")
    return [KnowledgeEntryCreate.model_validate(row) for row in rows]


@router.get("/knowledge/schools", response_model=list[str])
async def knowledge_schools(
    _user: CurrentUser,
    service: Services = Depends(get_services),
) -> list[str]:
    return await service.knowledge.schools()


@router.get("/knowledge/search", response_model=list[KnowledgeEntry])
async def search_knowledge(
    _user: CurrentUser,
    query: str = Query(default="", max_length=20000),
    school: str | None = Query(default=None, max_length=120),
    chapter: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=10, ge=1, le=50),
    service: Services = Depends(get_services),
) -> list[KnowledgeEntry]:
    return await service.knowledge.search(
        query,
        school=school,
        chapter=chapter,
        top_k=limit,
    )


@router.get("/knowledge/{entry_id}", response_model=KnowledgeEntry)
async def get_knowledge_entry(
    entry_id: str,
    _user: CurrentUser,
    service: Services = Depends(get_services),
) -> KnowledgeEntry:
    entry = await service.knowledge.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail={"message": "知识条目不存在"})
    return entry


@router.get("/admin/knowledge", response_model=list[KnowledgeEntry])
async def list_knowledge_entries(
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> list[KnowledgeEntry]:
    return await service.knowledge.list_entries(include_unpublished=True)


@router.post("/admin/knowledge", response_model=KnowledgeEntry, status_code=201)
async def create_knowledge_entry(
    request: KnowledgeEntryCreate,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> KnowledgeEntry:
    return await service.knowledge.create(request)


@router.patch("/admin/knowledge/{entry_id}", response_model=KnowledgeEntry)
async def update_knowledge_entry(
    entry_id: str,
    request: KnowledgeEntryUpdate,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> KnowledgeEntry:
    entry = await service.knowledge.update(entry_id, request)
    if not entry:
        raise HTTPException(status_code=404, detail={"message": "知识条目不存在"})
    return entry


@router.delete("/admin/knowledge/{entry_id}", status_code=204)
async def delete_knowledge_entry(
    entry_id: str,
    _admin: AdminAccess,
    service: Services = Depends(get_services),
) -> None:
    if not await service.knowledge.delete(entry_id):
        raise HTTPException(status_code=404, detail={"message": "知识条目不存在"})


@router.post("/admin/knowledge/import", response_model=KnowledgeImportResponse)
async def import_knowledge_file(
    _admin: AdminAccess,
    file: UploadFile = File(...),
    title: str = Form(default="导入资料", min_length=1, max_length=240),
    kind: KnowledgeKind = Form(default="other"),
    school: str | None = Form(default=None, max_length=120),
    year: int | None = Form(default=None),
    chapter: str = Form(default="signals", min_length=1, max_length=80),
    topics: str = Form(default=""),
    difficulty: int | None = Form(default=None),
    source_url: str | None = Form(default=None, max_length=2000),
    service: Services = Depends(get_services),
) -> KnowledgeImportResponse:
    raw = await file.read(MAX_KNOWLEDGE_FILE_BYTES + 1)
    if len(raw) > MAX_KNOWLEDGE_FILE_BYTES:
        raise HTTPException(status_code=413, detail={"message": "资料文件不能超过 20MB"})
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    try:
        if suffix in {".json", ".jsonl"}:
            requests = _structured_entries(raw, suffix)
        else:
            base = {
                "title": title.strip(),
                "kind": kind,
                "school": school.strip() if school else None,
                "year": year,
                "chapter": chapter.strip(),
                "topics": _topics(topics),
                "difficulty": difficulty,
                "source_url": source_url.strip() if source_url else None,
            }
            requests = []
            if suffix == ".pdf":
                reader = PdfReader(BytesIO(raw))
                for page_number, page in enumerate(reader.pages, start=1):
                    for content in _chunks(page.extract_text() or ""):
                        requests.append(
                            KnowledgeEntryCreate(
                                **base,
                                content=content,
                                source_page=page_number,
                            )
                        )
            elif suffix in {".md", ".markdown", ".txt"}:
                text = raw.decode("utf-8-sig")
                requests = [
                    KnowledgeEntryCreate(**base, content=content) for content in _chunks(text)
                ]
            else:
                raise ValueError("只支持 PDF、Markdown、TXT、JSON 和 JSONL 文件")
        if not requests:
            raise ValueError("资料中没有提取到可用文字，请先进行 OCR 或上传文字版 PDF")
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        PdfReadError,
        ValidationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc

    entries = await service.knowledge.create_many(requests)
    return KnowledgeImportResponse(imported=len(entries), entries=entries)
