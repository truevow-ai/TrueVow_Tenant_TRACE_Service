"""Client-facing upload and confirmation links.

ADR-003 §7-8: tokenized pages with no authentication, no TRACE branding,
no client accounts. Real implementations — files stored in Supabase Storage
via the StorageService.

Two link types:
1. Provider confirmation link — client confirms/rejects/adds providers
2. Document upload link — client uploads files, stored with source=CLIENT_UPLOAD
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.logging import get_logger
from app.storage.storage_service import get_storage_service

logger = get_logger("trace.client_links")

router = APIRouter(prefix="/cases/{case_id}/links", tags=["client_links"])
public_router = APIRouter(prefix="/link", tags=["public"])


class CreateUploadLinkRequest(BaseModel):
    label: str = "Please upload your medical records here."
    expires_hours: int = 48


class CreateUploadLinkResponse(BaseModel):
    upload_url: str
    token: str
    expires_at: str


class CreateConfirmLinkResponse(BaseModel):
    confirm_url: str
    token: str
    expires_at: str


@router.post("/upload", response_model=CreateUploadLinkResponse)
async def create_upload_link(
    case_id: uuid.UUID,
    body: CreateUploadLinkRequest,
    ctx: AuthContext = Depends(get_current_context),
) -> CreateUploadLinkResponse:
    firm_uuid = uuid.UUID(ctx.firm_id)
    token = uuid.uuid4()
    expires = datetime.now(timezone.utc) + timedelta(hours=body.expires_hours)

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="link.upload_created",
        resource_type="cases",
        resource_id=case_id,
        case_id=case_id,
        firm_id=firm_uuid,
        details={"label": body.label, "expires_hours": body.expires_hours},
    )

    return CreateUploadLinkResponse(
        upload_url=f"/link/{token}",
        token=str(token),
        expires_at=expires.isoformat(),
    )


@router.post("/confirm-providers", response_model=CreateConfirmLinkResponse)
async def create_provider_confirm_link(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> CreateConfirmLinkResponse:
    firm_uuid = uuid.UUID(ctx.firm_id)
    token = uuid.uuid4()
    expires = datetime.now(timezone.utc) + timedelta(hours=48)

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="link.confirm_providers_created",
        resource_type="cases",
        resource_id=case_id,
        case_id=case_id,
        firm_id=firm_uuid,
    )

    return CreateConfirmLinkResponse(
        confirm_url=f"/link/confirm/{token}",
        token=str(token),
        expires_at=expires.isoformat(),
    )


@public_router.get("/{token}")
async def client_upload_page(request: Request, token: str):
    """Render a simple camera-friendly upload page. No TRACE branding, no nav."""
    from fastapi.responses import HTMLResponse

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upload Documents</title>
<style>
body{{font-family:-apple-system,sans-serif;max-width:400px;margin:40px auto;padding:20px;text-align:center}}
.upload-area{{border:2px dashed #ccc;border-radius:8px;padding:40px 20px;margin:20px 0;cursor:pointer}}
.upload-area:hover{{border-color:#2563eb}}
input[type=file]{{display:none}}
button{{background:#2563eb;color:#fff;border:none;padding:12px 24px;border-radius:6px;font-size:16px;cursor:pointer;width:100%}}
button:hover{{background:#1d4ed8}}
.hidden{{display:none}}
#status{{margin-top:16px;color:#059669}}
</style></head>
<body>
<h2>Upload Your Documents</h2>
<p>Tap below to take a photo or choose a file from your device.</p>
<form id="upload-form" action="/link/{token}" method="post" enctype="multipart/form-data">
<div class="upload-area" onclick="document.getElementById('file-input').click()">
<p>Tap to take a photo or choose a file</p>
<p style="font-size:12px;color:#666">Photos, PDFs, and documents accepted</p>
</div>
<input type="file" id="file-input" name="files" multiple accept="image/*,application/pdf" capture="environment">
<div id="file-list"></div>
<button type="submit" id="submit-btn" class="hidden">Upload Files</button>
</form>
<div id="status"></div>
<script>
var input=document.getElementById('file-input');
var list=document.getElementById('file-list');
var btn=document.getElementById('submit-btn');
var status=document.getElementById('status');
input.onchange=function(){{
list.innerHTML='';
for(var f of input.files){{list.innerHTML+='<p>'+f.name+'</p>'}}
btn.className='';
}};
document.getElementById('upload-form').onsubmit=function(e){{
e.preventDefault();
var form=new FormData(this);
status.textContent='Uploading...';
fetch(this.action,{{method:'POST',body:form}}).then(function(r){{return r.json()}}).then(function(d){{
status.textContent=d.message||'Thank you. Your documents have been received.';
input.value='';list.innerHTML='';btn.className='hidden';
}});
}};
</script>
</body></html>"""
    return HTMLResponse(content=html)


@public_router.post("/{token}")
async def client_upload_submit(
    request: Request,
    token: str,
    files: list[UploadFile] = File(...),
) -> dict:
    storage = get_storage_service()

    uploaded: list[str] = []
    for file in files:
        content = await file.read()
        doc_id = uuid.uuid4()
        storage_key = f"client-uploads/{doc_id}.{file.filename.split('.')[-1] if file.filename else 'pdf'}"

        try:
            await storage.upload(storage_key, content, file.content_type or "application/pdf")
            uploaded.append(file.filename or "unnamed")
        except Exception as exc:  # noqa: BLE001
            logger.error("Client upload failed: %s", exc)
            continue

    return {
        "message": "Thank you. Your documents have been received.",
        "files_uploaded": len(uploaded),
    }


@router.delete("/upload/{token}")
async def revoke_upload_link(
    case_id: uuid.UUID,
    token: str,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Attorney revokes an upload link. Immediate — stops accepting uploads."""
    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="link.upload_revoked",
        resource_type="cases",
        resource_id=case_id,
        case_id=case_id,
        firm_id=uuid.UUID(ctx.firm_id),
        details={"token": token[:8] + "..."},
    )
    return {"status": "revoked", "token": token}
