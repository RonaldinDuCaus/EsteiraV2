from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..config import settings
from ..database import db
from .auth import current_user, same_origin
from .images import image_url, save_image, validate_image

router = APIRouter(prefix="/api/v1", tags=["Catálogo e histórico"], dependencies=[Depends(current_user)])


@router.get("/components")
def list_components():
    with db.connection() as conn:
        rows = conn.execute("""SELECT c.id,c.name,c.category,c.code,c.active,c.created_at,
            (SELECT ci.filename FROM component_images ci WHERE ci.component_id=c.id ORDER BY ci.id LIMIT 1) AS image_filename,
            (SELECT COUNT(*) FROM component_images ci WHERE ci.component_id=c.id) AS image_count
            FROM components c ORDER BY c.created_at DESC""").fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["image_url"] = image_url(item.pop("image_filename"))
        result.append(item)
    return result


@router.post("/components", status_code=201, dependencies=[Depends(same_origin)])
async def create_component(name: str = Form(...), category: str = Form(""), code: str = Form(""),
                           images: list[UploadFile] = File(...)):
    clean_name = name.strip()
    if not clean_name or len(clean_name) > 160 or len(category) > 100 or len(code) > 100:
        raise HTTPException(400, "Confira nome, categoria e código do componente.")
    if not images or len(images) > 10:
        raise HTTPException(400, "Envie entre 1 e 10 imagens.")
    saved = []
    try:
        for upload in images:
            data = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
            filename = save_image(data, validate_image(data))
            saved.append((filename, upload.filename, upload.content_type))
        with db.connection() as conn:
            component = conn.execute("INSERT INTO components(name,category,code) VALUES (%s,%s,%s) RETURNING id,name",
                                     (clean_name, category.strip() or None, code.strip() or None)).fetchone()
            for filename, original_name, content_type in saved:
                conn.execute("""INSERT INTO component_images(component_id,filename,original_name,content_type)
                    VALUES (%s,%s,%s,%s)""", (component["id"], filename, original_name, content_type))
        return {"id": component["id"], "name": component["name"], "images": len(saved)}
    except Exception:
        for filename, _, _ in saved:
            (settings.upload_dir / filename).unlink(missing_ok=True)
        raise


@router.patch("/components/{component_id}/status", dependencies=[Depends(same_origin)])
def change_component_status(component_id: int, active: bool):
    with db.connection() as conn:
        row = conn.execute("UPDATE components SET active=%s WHERE id=%s RETURNING id,active", (active, component_id)).fetchone()
    if not row:
        raise HTTPException(404, "Componente não encontrado.")
    return row


@router.get("/events")
def list_events(limit: int = 50):
    safe_limit = min(max(limit, 1), 200)
    with db.connection() as conn:
        rows = conn.execute("""SELECT id,component_id,detected_name,confidence,status,image_filename,device_id,created_at
            FROM recognition_events ORDER BY created_at DESC LIMIT %s""", (safe_limit,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["image_url"] = image_url(item.pop("image_filename"))
        result.append(item)
    return result
