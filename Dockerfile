FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-crosextra-carlito \
    fonts-liberation \
    fonts-crosextra-caladea \
    && rm -rf /var/lib/apt/lists/*

# Alias fontconfig "Arial MT" -> Liberation Sans (ver comentario dentro del
# .conf). Sin esto, contrato_trabajo se renderiza en DejaVu Sans y se
# deforma la paginación (notas al pie, checkboxes, páginas de más).
COPY fonts/99-arial-mt-alias.conf /etc/fonts/conf.d/99-arial-mt-alias.conf
RUN fc-cache -f

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY templates/ ./templates/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "app"]
