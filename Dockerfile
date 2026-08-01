# NO PROBADO todavía en Easypanel — pendiente de desplegar y validar.
# Sigue el mismo patrón que cv-redactor (FastAPI + dependencias del sistema).
FROM python:3.11-slim

# LibreOffice headless para la conversión docx -> pdf.
# Si finalmente se decide delegar esta conversión a Stirling PDF (ya
# desplegado en Easypanel), esta imagen se puede simplificar y quitar
# libreoffice de aquí.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "app"]
