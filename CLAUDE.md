# fistrek-doc-filler

Microservicio (FastAPI) que rellena plantillas Word (.docx) del proceso
"En firma" de Fistrek/Onestawave y devuelve el PDF resultante. Lo orquesta
un workflow de n8n que se dispara cuando un candidato llega a la fase
"En firma" en TeamTailor (TT).

## Antes de tocar nada: comprobar herramientas disponibles

Todo el desarrollo de este proyecto depende de poder **verificar visualmente**
cada cambio, no solo confiar en que el código "debería" funcionar. Comprueba
si estas herramientas están disponibles en este entorno, y si no, dilo
explícitamente antes de continuar:

- `soffice` (LibreOffice headless) — para convertir .docx → PDF
- `pdftoppm` (poppler-utils) — para rasterizar páginas del PDF a imagen y
  poder revisarlas
- `pdftotext` (poppler-utils) — para verificar contenido por texto cuando
  no haga falta ver el layout

Si no están instaladas, NO edites el XML a ciegas sin poder comprobar el
resultado — para un documento legal (contrato de trabajo), un error de
formato no detectado es peor que ir más despacio.

## Arquitectura

- `app/main.py` — FastAPI. Endpoint `POST /v1/fill/{document_key}`.
  Recibe JSON, lo valida contra el modelo `FillRequest`, y llama a la
  función de relleno correspondiente en `fillers.py`.
- `app/fillers.py` — una función `fill_<documento>(xml, **kwargs)` por
  cada tipo de documento, registradas en el diccionario `DOCUMENT_FILLERS`.
- `templates/<documento>/unpacked/` — cada plantilla ya descomprimida
  (unzip de un .docx) y con los runs de Word fusionados
  (`merge_runs.py` — fusiona runs de formato idéntico para que el texto
  a buscar no esté fragmentado en trozos impredecibles).

## Documentos existentes

| document_key | Estado |
|---|---|
| `retribucion_flexible` | ✅ Funciona en producción |
| `confidencialidad` | ✅ Funciona en producción |
| `consentimiento_empleados` | ✅ Funciona en producción |
| `rml` | ✅ Funciona en producción |
| `acuse_acoso` | ✅ Funciona en producción |
| `contrato_trabajo` | ✅ Funciona en producción (fallos de formato resueltos, ver historial abajo) |

**NUNCA toques las plantillas ni las funciones de los 6 documentos que ya
funcionan salvo que el usuario te pida explícitamente algo sobre ellos.**
Son plantillas de referencia del cliente — no se modifican, solo se
rellenan los huecos.

## Cómo está hecho el mecanismo de relleno (importante)

Cada función `fill_X` recibe el XML completo de `word/document.xml` como
string y hace sustituciones de texto **exactas** (`str.replace`, no
regex salvo casos puntuales), verificando SIEMPRE que el patrón aparece
el número de veces esperado antes de sustituir (función `_repl_once`,
que lanza `FillError` si no). Esto es deliberado: es mejor que falle con
un error claro ("aparece 0 veces, se esperaba 1") que rellenar a medias
en silencio.

Hay 3 mecanismos distintos de "hueco" según el documento, aprendidos a
base de prueba y error:

1. **Guiones bajos/puntos con color de placeholder** (ej.
   `retribucion_flexible`, `acuse_acoso`): el hueco es un run con texto
   `______` y a veces un color gris (`D0D5DD`) que hay que devolver a
   negro (`1A1A1A`) al rellenar, o el texto quedará gris en el PDF final.
2. **Párrafo de tabla completamente vacío** (ej. la tabla "DATOS DEL/DE
   LA TRABAJADOR/A" en `contrato_trabajo`): no hay ningún `<w:t>` que
   sustituir, hay que **insertar** un `<w:r><w:t>valor</w:t></w:r>`
   dentro de un `<w:p>` vacío, localizado por su `w14:paraId` (atributo
   único). Ver función `insertar_en_vacio` dentro de `fill_contrato_trabajo`.
3. **Checkbox de tabla simple** (ej. RML, o "INDEFINIDO ORDINARIO" en
   contrato_trabajo): una tabla con una celda vacía; se marca insertando
   `<w:t>X</w:t>` en el run vacío de esa celda.
4. **Checkbox VML dibujado** (ej. "Trabajo a distancia" en
   contrato_trabajo): un cuadrado dibujado con `<v:shape>` (gráfico
   vectorial), NO una tabla. Para marcarlo, se inserta un run de texto
   plano `<w:t>X </w:t>` (con espacio después) justo después del cierre
   `</mc:AlternateContent></w:r>` de esa figura, antes del texto de la
   etiqueta. Esto NO pone la X dentro del dibujo — cae visualmente al
   lado, que es el mismo estilo que ya usa el documento original en
   sus casillas ya marcadas (ej. "TIEMPO COMPLETO").

Antes de escribir cualquier reemplazo nuevo: localiza el contexto XML
exacto con Python (`xml.find(...)`, contar apariciones con
`xml.count(...)`), NUNCA asumas la estructura por cómo se ve el
documento renderizado — el mismo documento puede mezclar varios de los
4 mecanismos de arriba en distintas secciones.

## Ciclo de prueba recomendado para cualquier cambio

```bash
# 1. Preparar copia de trabajo desde la plantilla maestra (nunca editar el original)
cp -r templates/contrato_trabajo/unpacked /tmp/test_unpacked

# 2. Aplicar el/los cambios (Python, editando /tmp/test_unpacked/word/document.xml)

# 3. Empaquetar
cd /tmp/test_unpacked && zip -Xqr ../test.docx . -x '.*' && cd ..

# 4. Validar que no se ha roto la estructura (comparar párrafos con el original)
# (usar el script validate.py del skill de docx si está disponible, o al menos
# confirmar que el docx abre bien)

# 5. Convertir a PDF
soffice --headless --convert-to pdf test.docx

# 6. Rasterizar la página relevante y MIRARLA (no asumir que está bien)
pdftoppm -jpeg -r 130 -f <página> -l <página> test.pdf pagina
```

**Aviso sobre fuentes:** si la conversión a PDF se hace en un entorno
distinto al de producción (Docker en Easypanel), instala los paquetes
`fonts-crosextra-carlito` (clon de Calibri) y `fonts-liberation` (clon
de Arial) — sin ellos, LibreOffice sustituye por fuentes con métricas
distintas y el documento puede paginar diferente o verse distinto que
en producción. Esto ya nos pasó una vez con `--no-install-recommends`
en el Dockerfile, que se comía estos paquetes.

## Problemas conocidos en `contrato_trabajo` (a día de hoy)

### RESUELTO (12/08/2026): fuente "Arial MT" → DejaVu Sans deformaba todo el layout

El estilo por defecto de la plantilla (styles.xml) usa la fuente
**"Arial MT"** (nombre PostScript de Arial). Fontconfig no la reconoce y
caía a **DejaVu Sans**, mucho más ancha que Arial, cambiando todos los
saltos de línea. Consecuencias (todas con esta única causa raíz):

- Páginas de más (10 en vez de 7) con páginas casi vacías.
- Notas al pie desplazadas/duplicadas solapando el encabezado (las
  "notas" de este documento NO son notas al pie de Word: viven en
  textboxes dentro de los footers, uno por sección — el documento tiene
  11 secciones, y al desbordar una sección su footer se repetía).
- "X fantasma" sobre el checkbox de (13) horas complementarias y sobre
  "NOVENA: contrato de relevo", y checkboxes descolocados en la línea
  "A tiempo parcial" (formas VML ancladas que caían en posiciones
  calculadas con las métricas de la fuente equivocada).

**Fix**: alias fontconfig `fonts/99-arial-mt-alias.conf` (copiado a
`/etc/fonts/conf.d/` en el Dockerfile) que mapea Arial MT → Liberation
Sans. Verificado: el Word original convierte a 7 páginas limpias, y el
relleno completo con funciones largas también. `pdffonts` del PDF final
NO debe mostrar DejaVu Sans — si aparece, el alias no está activo.

**Para probar en sandbox**: replicar el alias antes de convertir:
`~/.config/fontconfig/fonts.conf` con el mismo contenido + `fc-cache -f`.

Moraleja: los glitches que parecían "formas flotantes fantasma" eran
síntoma de métricas de fuente — por eso borrar formas de la plantilla
fue un error. Ante cualquier glitch de layout, comprobar primero
`pdffonts` contra las fuentes que pide `word/fontTable.xml`.

## Despliegue

- El microservicio corre en Easypanel, servicio `fistrek-doc-filler`,
  construido desde este mismo repo de GitHub vía Dockerfile.
- Tras cualquier cambio subido a GitHub, hay que darle a "Implementar"
  en Easypanel para reconstruir la imagen — los cambios no se aplican
  solos.
- n8n llama al servicio en `http://fistrek-doc-filler:8000/v1/fill/<document_key>`
  (red interna de Easypanel).

## Convenciones de nombres de documento

El `document_key` (usado en la URL y en `DOCUMENT_FILLERS`) coincide
con el nombre de archivo final que sube n8n a TeamTailor:
`{document_key}.pdf`. Si renombras un `document_key`, actualiza también
el nodo de n8n que llama a ese endpoint y el filtro de nombres
conocidos en el nodo que detecta documentos de identidad (DNI) del
candidato, que excluye explícitamente los nombres de los 6 documentos
generados para no confundirlos con documentos subidos por el candidato.
