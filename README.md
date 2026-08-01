# Fistrek "En firma" — esqueleto (5 documentos cortos)

## Qué está PROBADO hoy

- **`app/fillers.py`**: lógica de relleno de los 5 documentos, extraída
  directamente de las pruebas manuales de esta sesión. Cada función
  verifica que cada hueco aparece exactamente 1 vez antes de sustituir
  (si la plantilla cambia y algún hueco no aparece o aparece más de una
  vez, la función falla explícitamente en lugar de rellenar a medias).
- **`app/main.py`**: microservicio FastAPI que expone
  `POST /v1/fill/{document_key}` y devuelve el PDF. **Probado en local**
  (no en Easypanel) contra los 5 documentos con un candidato de prueba
  distinto (Ana García Soler / DNI 98765432X) — los 5 devuelven HTTP 200
  y el contenido del PDF resultante se verificó por texto.
- Documentos soportados: `retribucion_flexible`, `confidencialidad`,
  `consentimiento_empleados`, `rml`, `acuse_acoso`.

## Qué NO está hecho / probado

- **Contrato de trabajo**: no incluido en este esqueleto (pendiente,
  documento más complejo, se aborda en otra sesión).
- **Despliegue en Easypanel**: el `Dockerfile` no se ha construido ni
  desplegado. Asume LibreOffice instalado en la propia imagen; si se
  prefiere delegar la conversión a Stirling PDF (ya desplegado), hay que
  sustituir la función `_docx_to_pdf` en `main.py` por una llamada HTTP
  al endpoint de conversión de Stirling.
- **Autenticación del microservicio**: no tiene ninguna todavía. Antes
  de exponerlo hay que decidir cómo se protege (API key simple, red
  interna de Easypanel sin exposición pública, etc.).
- **Endpoint real de la "Ficha de contratación" vía API de TT**: el
  workflow de n8n tiene un nodo marcador de posición
  (`GET Ficha de contratación (PENDIENTE endpoint real)`) con una URL
  ficticia. Hay que probarlo contra un candidato real de Fistrek antes
  de que el flujo funcione de verdad.
- **Nombre exacto del campo de stage en el payload del webhook de TT**:
  el nodo IF asume `to_stage_name`, sin confirmar contra un payload real
  (igual que se hizo en su día con Behum).
- **El workflow de n8n (`n8n_workflow_esqueleto.json`) no se ha
  importado ni ejecutado en tu instancia de n8n.** Es un punto de
  partida para importar y ajustar, no un flujo verificado end-to-end.
- Mapeo real de los campos de la ficha de contratación (`dni`,
  `puesto_trabajo`, `fecha_inicio` en el código de ejemplo del nodo
  "Normalizar datos candidato") son nombres de placeholder, no
  confirmados contra la API real.

## Cómo importar el workflow

En tu n8n: menú ⋮ → *Import from File* → seleccionar
`n8n_workflow_esqueleto.json`. Tendrás que:
1. Asignar la credencial `httpHeaderAuth` de TT ya existente a los
   nodos HTTP que la usan.
2. Sustituir la URL del nodo "GET Ficha de contratación" por el
   endpoint real una vez lo confirmemos.
3. Ajustar la URL de los 5 nodos "Rellenar ..." según dónde despliegues
   `fistrek-doc-filler` (nombre de servicio interno en Easypanel o
   dominio público).
4. Configurar el nodo Merge con 5 inputs (uno por documento).

## Cómo probar el microservicio en local

```bash
pip install -r requirements.txt --break-system-packages
cd app && uvicorn main:app --reload --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/v1/fill/retribucion_flexible \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Nombre Prueba","dni":"12345678Z","fecha_dia":"1","fecha_mes":"agosto","fecha_anio":"2026"}' \
  -o test.pdf
```
