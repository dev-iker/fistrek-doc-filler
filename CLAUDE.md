# fistrek-doc-filler

Microservicio (FastAPI) que rellena plantillas Word (.docx) del proceso
"En firma" de Fistrek/Onestawave y devuelve el PDF resultante. Lo orquesta
un workflow de n8n que se dispara cuando un candidato llega a la fase
"En firma" en TeamTailor (TT).

## Antes de tocar nada: comprobar herramientas disponibles

Todo el desarrollo de este proyecto depende de poder **verificar
visualmente** cada cambio, no solo confiar en que el código "debería"
funcionar. Comprueba si estas herramientas están disponibles en este
entorno, y si no, dilo explícitamente antes de continuar:

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

| document_key               | Estado                                                                      |
| -------------------------- | --------------------------------------------------------------------------- |
| `retribucion_flexible`     | ✅ Funciona en producción                                                    |
| `confidencialidad`         | ✅ Funciona en producción                                                    |
| `consentimiento_empleados` | ✅ Funciona en producción                                                    |
| `rml`                      | ✅ Funciona en producción                                                    |
| `acuse_acoso`              | ✅ Funciona en producción                                                    |
| `contrato_trabajo_150`     | ✅ Activo — INDEFINIDO BONIFICADO (código 150)                               |
| `contrato_trabajo`         | ⛔ DESACTIVADO (31/08/2026) — INDEFINIDO ORDINARIO. Ver más abajo             |

**NUNCA toques las plantillas ni las funciones de los documentos que ya
funcionan salvo que el usuario te pida explícitamente algo sobre ellos.**
Son plantillas de referencia del cliente — no se modifican, solo se
rellenan los huecos.

### `contrato_trabajo` está desactivado, no borrado

El 31/08/2026 la gestoría cambió el modelo de contrato: del **INDEFINIDO
ORDINARIO** (código SEPE 100) al **INDEFINIDO BONIFICADO** (código 150).
No son el mismo documento con retoques, son dos modalidades distintas:

- El 150 no tiene campo `funciones` ni casilla "Trabajo a distancia".
- El 150 incorpora la cláusula adicional SÉPTIMA de I+D+i.
- El 150 tiene 4 páginas; el ordinario, 7.

`fill_contrato_trabajo` y `templates/contrato_trabajo/` **se conservan
intactas**. Solo está comentada su entrada en `DOCUMENT_FILLERS`. Para
reactivarlo basta descomentar esa línea.

**Consecuencia pendiente**: el anexo de teletrabajo que estaba pendiente
con Jorge dependía de la casilla "Trabajo a distancia", que existe en el
modelo ordinario y NO en el 150. Si vuelve a hacer falta, hay que decidir
si va como anexo separado.

## Cómo está hecho el mecanismo de relleno (importante)

Cada función `fill_X` recibe el XML completo de `word/document.xml` como
string y hace sustituciones de texto **exactas** (`str.replace`, no
regex salvo casos puntuales), verificando SIEMPRE que el patrón aparece
el número de veces esperado antes de sustituir (función `_repl_once`,
que lanza `FillError` si no). Esto es deliberado: es mejor que falle con
un error claro ("aparece 0 veces, se esperaba 1") que rellenar a medias
en silencio.

### Fillers que necesitan tocar más de un fichero del .docx

Por defecto una función de relleno recibe un `str` (el `document.xml`) y
devuelve otro `str`. Pero algunas plantillas tienen huecos **fuera** de
`document.xml`: el contrato 150 lleva la fecha de firma en el pie
(`word/footer1.xml`), porque el documento original tiene 3 secciones con
pies distintos.

Convenio (introducido 31/08/2026, retrocompatible):

- Si la función de relleno **declara el parámetro `partes`**, `main.py` le
  entrega un `dict {ruta_relativa: xml}` con todas las partes XML de
  `word/`, y espera de vuelta otro dict con las que haya modificado. El
  dict devuelto **debe** incluir `word/document.xml`.
- Si **no lo declara**, recibe y devuelve solo el `str` de
  `document.xml`, exactamente igual que antes. Los 5 fillers antiguos
  están en este caso y su ejecución no cambia.

`main.py` valida cada ruta devuelta: tiene que caer dentro del directorio
de trabajo y el fichero tiene que existir ya. Sin eso, un `../` en una
clave permitiría escribir fuera del paquete.

### Mecanismos de "hueco" según la plantilla

Los documentos antiguos mezclan hasta 4 mecanismos distintos, aprendidos a
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
   etiqueta.

**`contrato_trabajo_150` es la excepción y es mucho más simple**: como su
plantilla se limpió de campos de Word (ver más abajo), todo el texto es
plano y solo hay **un** mecanismo de hueco: un `<w:t>` que contiene
únicamente espacios y/o guiones bajos, localizado a partir de un ancla de
texto contiguo que se valida como única (`_rellenar_hueco_150`). La tabla
del trabajador tiene tres variantes de celda, resueltas con un único
helper (`_rellenar_celda_150`): hueco de espacios, run vacío, o solo la
etiqueta (se añade un run nuevo heredando el formato del hermano no
negrita).

Truco útil: cuando dos huecos cuelgan del mismo ancla (los días de jornada,
o día/mes/año de la fecha de firma), se rellenan en orden con **el mismo
ancla**. Al rellenarse, cada hueco deja de ser "solo espacios", así que la
llamada siguiente cae automáticamente en el posterior. Evita tener anclas
frágiles distintas para cada uno.

Antes de escribir cualquier reemplazo nuevo: localiza el contexto XML
exacto con Python (`xml.find(...)`, contar apariciones con
`xml.count(...)`), NUNCA asumas la estructura por cómo se ve el documento
renderizado — el mismo documento puede mezclar varios mecanismos en
distintas secciones.

## Ciclo de prueba recomendado para cualquier cambio

```
# 1. Preparar copia de trabajo desde la plantilla maestra (nunca editar el original)
cp -r templates/contrato_trabajo_150/unpacked /tmp/test_unpacked

# 2. Aplicar el/los cambios (Python, editando /tmp/test_unpacked/word/document.xml)

# 3. Empaquetar
cd /tmp/test_unpacked && zip -Xqr ../test.docx . -x '.*' && cd ..

# 4. Validar que no se ha roto la estructura (comparar párrafos con el original)

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

## Problemas conocidos en `contrato_trabajo_150`

### La plantilla venía dañada de origen — usar `reparar_plantilla.py`

La gestoría entrega el modelo 150 como **`.doc` binario** generado por su
software de nóminas (A3/Sage), no como `.docx`. Ese fichero es un
**artefacto intermedio**, no una plantilla terminada, y tiene varios
defectos que hay que corregir antes de poder usarlo. El script
`reparar_plantilla.py` los arregla todos y es **reejecutable**: si la
gestoría manda una versión nueva del modelo, se le pasa y listo.

Qué arregla, y por qué importa cada cosa:

1. **85 propiedades personalizadas con datos reales del candidato.** Todo
   el documento está construido con campos `DOCPROPERTY` (`T:APELLIDOS-Y-NOMBRE`,
   `T:DNI-14POSIC`, `T:NACIMIENTO`…). Aunque el texto visible se borre, los
   valores siguen ahí. **Riesgo real**: si alguien abre la plantilla en Word y
   pulsa `F9`, los campos se repueblan con los datos del candidato anterior y
   se emite un contrato con el nombre y el NIF de otra persona. El script
   desvincula los ~320 campos (los convierte en texto estático) y vacía
   `docProps/custom.xml`.
2. **Dos campos rotos que imprimen rutas del PC de la gestoría.**
   `INICIO-CLAUSULAS(RTF)` y `FIRMAS` apuntan a ficheros temporales
   (`C:\Users\Laboral\AppData\Local\Temp\...`) que su software inyecta al
   imprimir. Fuera de su máquina se imprime la ruta literal y falta texto
   legal: el título de la cláusula adicional PRIMERA y el bloque de firmas.
   El script los reconstruye.
3. **Códigos residuales del candidato** (`55` nivel formativo, `724`
   nacionalidad) que siguen visibles en la tabla del trabajador.
4. **Casillas SÍ/NO partidas en dos líneas.** La tabla usa
   `tblLayout=fixed`, así que el ancho efectivo lo marca `<w:tblGrid>`, NO
   `<w:tcW>`; además los márgenes internos de celda (108 twips por lado)
   se comen el espacio. Hay que tocar ambos. Las columnas vecinas son los
   propios recuadros de marcar, así que no se les puede robar ancho: la
   tabla es flotante y se deja crecer recalculando `tblW`.
5. **Runs con `<w:rPr/>` vacío** que caen al estilo por defecto (Courier /
   Liberation Mono) y se ven con otra tipografía. Se les copia el formato
   del run hermano más cercano.
6. **El importe del pacto de no competencia** queda como marcador
   `{{COMPENSACION_NO_COMPETENCIA}}` (ver siguiente apartado).

### Los pies por sección se pierden al convertir de .doc

**Esto es lo más importante de todo el documento y no es evidente.**

El original tiene **3 secciones con pies distintos**:

| Sección | Páginas | Cabecera | Pie |
| ------- | ------- | -------- | --- |
| 1 | 1 | (vacía) | ninguno |
| 2 | 2 | (vacía) | "Ver Anexo Cláusulas" + texto + fecha + firmas + notas (1)-(13) |
| 3 | 3-4 | "CLAUSULAS ANEXAS" | solo el bloque de firmas |

Al convertir el `.doc` a `.docx` **con cualquier motor que no sea Word de
escritorio** (LibreOffice, Google Docs, conversores web) sobrevive **una
sola** `footerReference`. Las tres secciones heredan entonces el pie más
largo. Síntomas: "En BARCELONA a __ de __" aparece en páginas donde no
toca, y el pie roba ~55 puntos de cuerpo en cada página, lo que provoca
**una página de más** (5 en vez de 4).

Cómo detectarlo rápido en un `.docx` sospechoso:

```python
import zipfile, re
s = zipfile.ZipFile(f).read('word/document.xml').decode()
print(s.count('<w:sectPr'), re.findall(r'<w:footerReference[^>]*/>', s))
# 3 secciones y 1 sola footerReference => están perdidos
```

Y para saber si un `.docx` viene de Word: mira `docProps/app.xml`. Word
escribe `<Application>Microsoft Office Word</Application>` más páginas,
palabras y caracteres. Si viene casi vacío (`<Template>Normal</Template>`
y poco más), ha pasado por otro conversor.

`reparar_plantilla.py` reconstruye la cabecera y el pie de la sección 3
(`header4.xml` y `footer2.xml`, con sus entradas en
`document.xml.rels` y `[Content_Types].xml`) y repone el texto
"Ver Anexo Cláusulas" que venía de un campo `IF` cuyo resultado se perdió.

### LibreOffice no cambia cabecera/pie en un salto de sección continuo

Al reconstruir la sección 3 las referencias se escribían bien pero
LibreOffice las ignoraba. La causa: **Writer ata las cabeceras y pies a
estilos de página, y un estilo de página nuevo exige un salto de página**.
Con `<w:type w:val="continuous"/>` simplemente no las aplica.

`reparar_plantilla.py` fuerza la sección 3 a `nextPage`. Efecto
secundario aceptado: en el PDF original de la gestoría la página 3 arranca
a mitad de párrafo y el encabezado "CLÁUSULAS ADICIONALES" queda al final
de la página 2; en la plantilla reparada las cláusulas adicionales empiezan
limpias en la página 3. El contenido es idéntico y el total sigue siendo 4
páginas. Los cortes de las páginas 1, 3 y 4 coinciden exactamente con el
original.

Ojo también con el **orden de los hijos de `<w:sectPr>`**: OOXML exige
`headerReference` antes que `footerReference`, y ambos antes que el resto.

El relleno del pie (`RELLENO_PIE3 = 8` párrafos vacíos en `footer2.xml`)
está **calibrado empíricamente** contra el PDF de referencia: con ese valor
el corte de la página 3 cae en la misma frase que el original. Si se cambia,
hay que volver a comparar los cortes de página.

### La fuente NO es el problema en este documento

`contrato_trabajo` pedía **"Arial MT"** (nombre PostScript), fontconfig no
lo reconocía y caía a DejaVu Sans (ver historial más abajo). **El modelo
150 pide "Arial" a secas**, que fontconfig resuelve solo a Liberation Sans.
No hace falta tocar el `Dockerfile` ni instalar `ttf-mscorefonts-installer`.

Si aparece un desajuste de paginación en este documento, **mira primero las
secciones y los pies, no las fuentes**. La deriva por usar Liberation Sans
en lugar de Arial real es de pocos puntos por página y se resincroniza en
cada salto.

La fuente `A3 Lineas` que aparece en `fontTable.xml` y `styles.xml` es del
software de la gestoría, solo se usa en estilos de encabezado que el cuerpo
no utiliza (0 apariciones en `document.xml`). Es ruido, no un problema.

### La compensación por no competencia es un campo CALCULADO

La cláusula adicional QUINTA dice "un 10% (341,67€) de la remuneración fija
bruta mensual". Ese importe **no es un dato de entrada**: es
`salario_anual / 12 × 0,10`. En la plantilla original venía con el valor de
un candidato concreto pegado, lo que habría emitido contratos con un importe
incorrecto en una cláusula con efectos en nómina.

En la plantilla reparada es el marcador `{{COMPENSACION_NO_COMPETENCIA}}` y
lo calcula `calcular_compensacion_no_competencia()`. Se usa `Decimal` con
`ROUND_HALF_UP`, **no `round()` de Python**, que aplica redondeo bancario
(`round(2.675, 2)` da `2.67`) y daría importes incorrectos.

El `10%` y los `6 meses` están escritos en el texto de la cláusula, no son
variables. Si la gestoría los cambia, hay que tocar la plantilla maestra.

### El salario no es un campo de Word

En la cláusula QUINTA el salario está **escrito a mano** en el documento
original, no viene de un `DOCPROPERTY`. En la plantilla limpia el hueco es
un run de espacios entre `"retribución total de "` y `" euros brutos (8)"`.
Es el anclaje más frágil de los 16; si falla, `_repl_once` lo dirá.

## Historial de `contrato_trabajo` (DESACTIVADO, se conserva por si vuelve)

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
Sans. Verificado: el Word original convierte a 7 páginas limpias.
`pdffonts` del PDF final NO debe mostrar DejaVu Sans — si aparece, el
alias no está activo. **Este alias sigue siendo necesario aunque el
documento esté desactivado: no lo quites del Dockerfile.**

**Para probar en sandbox**: replicar el alias antes de convertir:
`~/.config/fontconfig/fonts.conf` con el mismo contenido + `fc-cache -f`.

Moraleja: los glitches que parecían "formas flotantes fantasma" eran
síntoma de métricas de fuente — por eso borrar formas de la plantilla
fue un error. Ante cualquier glitch de layout, comprobar primero
`pdffonts` contra las fuentes que pide `word/fontTable.xml`.

### RESUELTO (12/08/2026): "NIVEL FORMATIVO" con fuente y sangría distintas al resto de la tabla

En `fill_contrato_trabajo`, el hueco de `nivel_formativo` (mecanismo 2,
párrafo de tabla vacío) tenía en la propia plantilla un run placeholder
con `<w:rFonts w:ascii="Times New Roman"/>` harcodeado y sin
`<w:ind w:left="71"/>` en el `<w:pPr>`, a diferencia de sus celdas
hermanas (nombre, DNI, municipio) que no fijan fuente (heredan Arial MT)
y sí llevan esa sangría. Resultado: el valor rellenado salía en Times
New Roman y pegado al borde izquierdo de la celda.

**Fix**: al reemplazar el placeholder, se quita el `w:rFonts` (hereda la
fuente del documento) y se añade `<w:ind w:left="71"/>` al `pPr`.

### RESUELTO (12/08/2026): rayas de subrayado fantasma sobre el texto de "funciones" cuando es largo

Con `funciones` largo (varias líneas), aparecían dos segmentos con
subrayado en mitad del texto que NO correspondían a ningún `<w:u>` real.

Causa: el párrafo de la cláusula PRIMERA (paraId `0C219AA1`) tiene 2
formas flotantes (`mc:AlternateContent`, "Graphic 5" y "Graphic 6")
ancladas con `positionV relativeFrom="paragraph"` y un offset fijo
pequeño. Son rectángulos finos que en la plantilla ORIGINAL sirven para
mostrar visualmente el hueco "______" de "puesto" y "grupo profesional".
Como `fill_contrato_trabajo` ya aplica subrayado real a esos campos,
quedaban redundantes — y al crecer el párrafo, el texto que caía en esa
posición fija heredaba visualmente la rayita.

**Fix**: se eliminaron esos 2 bloques `mc:AlternateContent` de la
plantilla maestra (a diferencia de "Group 27"/"Group 35", que SÍ son
checkboxes reales y no había que tocar).

Moraleja: no todos los `mc:AlternateContent` de este documento son
checkboxes — hay que mirar cada uno con contexto (¿hay ya un `<w:u>`
real cubriendo esa función?) antes de decidir si tocarlo.

## Despliegue

- El microservicio corre en Easypanel, servicio `fistrek-doc-filler`,
  construido desde este mismo repo de GitHub vía Dockerfile.
- Tras cualquier cambio subido a GitHub, hay que darle a "Implementar"
  en Easypanel para reconstruir la imagen — los cambios no se aplican
  solos.
- n8n llama al servicio en
  `http://fistrek-doc-filler:8000/v1/fill/<document_key>` (red interna
  de Easypanel).
- Smoke test tras cada despliegue: `GET /health` devuelve
  `documentos_disponibles`. Si `contrato_trabajo_150` no aparece ahí, la
  imagen no se ha reconstruido.

## Convenciones de nombres de documento

El `document_key` (usado en la URL y en `DOCUMENT_FILLERS`) coincide
con el nombre de archivo final que sube n8n a TeamTailor:
`{document_key}.pdf`. Si renombras un `document_key`, actualiza también
el nodo de n8n que llama a ese endpoint y el filtro de nombres
conocidos en el nodo que detecta documentos de identidad (DNI) del
candidato, que excluye explícitamente los nombres de los 6 documentos
generados para no confundirlos con documentos subidos por el candidato.

**Atención con el cambio del 31/08/2026**: el fichero pasa de llamarse
`contrato_trabajo.pdf` a `contrato_trabajo_150.pdf`. Si no se actualiza
el filtro del nodo de detección de DNI, el contrato generado puede colarse
como documento de identidad del candidato.
