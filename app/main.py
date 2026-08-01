"""
fistrek-doc-filler
-------------------
Microservicio (FastAPI) que rellena las plantillas Word del proceso
"En firma" de Fistrek y devuelve el PDF resultante.

NO SE HA DESPLEGADO NI PROBADO EN EASYPANEL TODAVÍA. Esto es un primer
esqueleto funcional probado solo en local (ver README.md), pendiente de:
  - decidir si la conversión a PDF la hace este mismo contenedor
    (LibreOffice instalado dentro) o se delega a Stirling PDF vía HTTP
  - contenerizar y desplegar
  - añadir autenticación (de momento no tiene ninguna)

Endpoint principal:
  POST /v1/fill/{document_key}
  body: JSON con los campos que requiera esa plantilla (ver fillers.py)
  respuesta: application/pdf (bytes)

document_key válidos: retribucion_flexible, confidencialidad,
consentimiento_empleados, rml, acuse_acoso
(el "contrato de trabajo" NO está incluido todavía — pendiente)
"""

import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from fillers import DOCUMENT_FILLERS, FillError

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="fistrek-doc-filler")


class FillRequest(BaseModel):
    # Campos comunes más habituales. FastAPI/Pydantic permitirá pasar
    # solo los que necesite cada plantilla; el resto se ignoran.
    nombre: str | None = None
    dni: str | None = None
    puesto: str | None = None
    empresa: str | None = None
    fecha_dia: str | None = None
    fecha_mes: str | None = None
    fecha_anio: str | None = None
    fecha: str | None = None          # para plantillas que ya usan fecha "d de mes de aaaa" en un solo campo
    fecha_lugar: str | None = None
    consentimiento_si: bool = True    # solo aplica a "rml"


def _zip_dir(src_dir: Path, out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in src_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(src_dir))


def _docx_to_pdf(docx_path: Path, out_dir: Path) -> Path:
    """
    Conversión vía LibreOffice headless. Requiere `soffice` instalado en
    el contenedor. Si se decide usar Stirling PDF en su lugar, sustituir
    esta función por una llamada HTTP a su endpoint de conversión.
    """
    result = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Fallo en conversión a PDF: {result.stderr}")
    pdf_path = out_dir / (docx_path.stem + ".pdf")
    if not pdf_path.exists():
        raise HTTPException(status_code=500, detail="LibreOffice no generó el PDF esperado")
    return pdf_path


@app.post("/v1/fill/{document_key}")
def fill_document(document_key: str, req: FillRequest):
    if document_key not in DOCUMENT_FILLERS:
        raise HTTPException(status_code=404, detail=f"documento desconocido: {document_key}")

    template_unpacked = TEMPLATES_DIR / document_key / "unpacked"
    if not template_unpacked.exists():
        raise HTTPException(status_code=500, detail=f"plantilla no encontrada en disco: {document_key}")

    filler_fn = DOCUMENT_FILLERS[document_key]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        work_dir = tmp_path / "unpacked"
        shutil.copytree(template_unpacked, work_dir)

        doc_xml_path = work_dir / "word" / "document.xml"
        xml = doc_xml_path.read_text(encoding="utf-8")

        # Solo pasamos los kwargs que la función de relleno realmente acepta
        import inspect
        params = inspect.signature(filler_fn).parameters
        kwargs = {k: v for k, v in req.model_dump().items() if k in params and v is not None}

        try:
            xml = filler_fn(xml, **kwargs)
        except FillError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except TypeError as e:
            raise HTTPException(status_code=422, detail=f"faltan campos para '{document_key}': {e}")

        doc_xml_path.write_text(xml, encoding="utf-8")

        docx_path = tmp_path / f"{document_key}_{uuid.uuid4().hex}.docx"
        _zip_dir(work_dir, docx_path)

        pdf_path = _docx_to_pdf(docx_path, tmp_path)
        pdf_bytes = pdf_path.read_bytes()

    return Response(content=pdf_bytes, media_type="application/pdf")


@app.get("/health")
def health():
    return {"status": "ok", "documentos_disponibles": list(DOCUMENT_FILLERS.keys())}
