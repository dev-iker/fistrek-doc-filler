"""
Lógica de relleno para cada plantilla de Fistrek "En firma".

Cada función recibe el XML (word/document.xml) de una COPIA del template
maestro (nunca se toca el original) y una serie de datos, y devuelve el
XML ya relleno. Cada reemplazo se verifica contando ocurrencias exactas
(assert count == 1) para evitar rellenos silenciosamente incompletos.

IMPORTANTE: estas funciones dependen de que el XML de origen ya haya
pasado por merge_runs.py (fusión de runs contiguos del mismo formato),
que es justamente el estado en el que están guardadas las plantillas en
templates/<doc>/unpacked/word/document.xml. Si alguna plantilla se
reemplaza por una versión nueva del documento, hay que re-generar el
unpacked/ correspondiente (unzip + merge_runs.py) antes de que estas
funciones vuelvan a funcionar, porque los huecos podrían estar
fragmentados de otra manera.

Algunos fillers (ver fill_contrato_trabajo_150) necesitan además tocar
partes del .docx distintas de word/document.xml. Ver el apartado
"Fillers que necesitan tocar más de un fichero" en CLAUDE.md.
"""

import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape as _xml_escape


class FillError(Exception):
    """Se lanza cuando un hueco esperado no aparece exactamente 1 vez."""
    pass


def _repl_once(xml: str, old: str, new: str, label: str) -> str:
    n = xml.count(old)
    if n != 1:
        raise FillError(f"{label}: aparece {n} veces en la plantilla, se esperaba 1")
    return xml.replace(old, new, 1)


def _strip_decorative_marks(value: str) -> str:
    """
    Quita "decoraciones" Unicode que a veces se cuelan en texto libre
    (tachado/subrayado hechos con marcas combinantes tipo U+0336, o
    "zalgo text"), copiadas de un origen con formato enriquecido (p.ej.
    una respuesta de IA generada en n8n) que Word/LibreOffice SÍ sabe
    renderizar aunque no sean tags XML reales — por eso escapar < > &
    (ver `_esc`) no las neutraliza.

    Se normaliza primero a NFC: cualquier acento español legítimo ya
    tiene forma precompuesta (á, é, í, ó, ú, ñ, ü son un único
    codepoint), así que cualquier marca combinante que sobreviva a la
    normalización no es un acento real, es decoración sobrante, y se
    elimina.

    Se quitan las TRES categorías Unicode de "marca" (no solo "Mn"):
      - Mn (Nonspacing Mark): el caso típico de tachado/subrayado hecho
        con una marca que se dibuja sobre el carácter anterior sin
        ocupar espacio propio (p.ej. U+0336 COMBINING LONG STROKE
        OVERLAY, el que se genera con conversores de "texto tachado").
      - Me (Enclosing Mark): variantes que dibujan un trazo o círculo
        "envolviendo" el carácter (p.ej. U+20D2, U+20E5).
      - Mc (Spacing Combining Mark): menos común para esto, pero se
        incluye por seguridad ya que no aparece en ortografía española.

    También se eliminan caracteres de ancho cero (U+200B-U+200D,
    U+FEFF) que a veces acompañan a este tipo de texto "decorado".
    """
    normalized = unicodedata.normalize("NFC", value)
    zero_width = {"\u200b", "\u200c", "\u200d", "\ufeff"}
    return "".join(
        ch for ch in normalized
        if unicodedata.category(ch)[0] != "M" and ch not in zero_width
    )


def _esc(value: str) -> str:
    """Sanea (quita decoraciones Unicode) y escapa (& < >) texto libre
    antes de insertarlo como contenido de un <w:t>."""
    return _xml_escape(_strip_decorative_marks(value))


def fill_retribucion_flexible(xml: str, *, nombre: str, dni: str, fecha_dia: str, fecha_mes: str, fecha_anio: str) -> str:
    # Nombre (declaración inicial, 45 guiones) — el placeholder está en gris (D0D5DD),
    # hay que devolverlo a negro (1A1A1A) al rellenarlo.
    xml = _repl_once(
        xml,
        '<w:r><w:rPr><w:color w:val="D0D5DD"/></w:rPr><w:t>_____________________________________________</w:t></w:r>',
        f'<w:r><w:rPr><w:color w:val="1A1A1A"/></w:rPr><w:t>{nombre}</w:t></w:r>',
        "nombre (45 guiones)",
    )
    # DNI (16 guiones), mismo tratamiento de color
    xml = _repl_once(
        xml,
        '<w:r><w:rPr><w:color w:val="D0D5DD"/></w:rPr><w:t>________________</w:t></w:r>',
        f'<w:r><w:rPr><w:color w:val="1A1A1A"/></w:rPr><w:t>{dni}</w:t></w:r>',
        "DNI (16 guiones)",
    )
    xml = _repl_once(
        xml,
        '<w:t xml:space="preserve">En Sant Cugat del Vallès, a _______ de ________________________ de _____________.</w:t>',
        f'<w:t xml:space="preserve">En Sant Cugat del Vallès, a {fecha_dia} de {fecha_mes} de {fecha_anio}.</w:t>',
        "fecha",
    )
    # Nombre en la firma (23 guiones) — este run además lleva sz/szCs=20
    xml = _repl_once(
        xml,
        '<w:r><w:rPr><w:color w:val="D0D5DD"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t>_______________________</w:t></w:r>',
        f'<w:r><w:rPr><w:color w:val="1A1A1A"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t>{nombre}</w:t></w:r>',
        "nombre firma (23 guiones)",
    )
    return xml


def fill_confidencialidad(xml: str, *, nombre: str, dni: str, fecha: str) -> str:
    old1 = (
        'De una parte Dn./ña. ........................................................... '
        '.......................................................... '
        '.......................................................... '
        'con DNI-NIE ..............................., en adelante '
    )
    new1 = f'De una parte Dn./ña. {nombre} con DNI-NIE {dni}, en adelante '
    xml = _repl_once(xml, old1, new1, "declaración inicial")

    old2 = 'SANT CUGAT DEL VALLES, BARCELONA (ESPAÑA), a ………………………………..'
    new2 = f'SANT CUGAT DEL VALLES, BARCELONA (ESPAÑA), a {fecha}'
    xml = _repl_once(xml, old2, new2, "fecha")

    old3 = (
        'Firmado: ........................................................... '
        '.......................................................... '
        '.......................................................... '
        'con DNI-NIE ...............................'
    )
    new3 = f'Firmado: {nombre} con DNI-NIE {dni}'
    xml = _repl_once(xml, old3, new3, "bloque de firma")
    return xml


def fill_consentimiento_empleados(xml: str, *, nombre: str, dni: str, fecha: str) -> str:
    old1 = (
        'El abajo firmante, D/ña. ........................................................... '
        '.......................................................... '
        '.......................................................... '
        'con DNI-NIE nº ............................... mediante el presente documento,'
    )
    new1 = f'El abajo firmante, D/ña. {nombre} con DNI-NIE nº {dni} mediante el presente documento,'
    xml = _repl_once(xml, old1, new1, "declaración inicial")

    old2 = 'En SANT CUGAT DEL VALLES, BARCELONA (ESPAÑA), a ………………………………..'
    new2 = f'En SANT CUGAT DEL VALLES, BARCELONA (ESPAÑA), a {fecha}'
    xml = _repl_once(xml, old2, new2, "fecha")

    old3 = (
        'Firmado: ........................................................... '
        '.......................................................... '
        '.......................................................... '
        'con DNI-NIE ...............................'
    )
    new3 = f'Firmado: {nombre} con DNI-NIE {dni}'
    xml = _repl_once(xml, old3, new3, "bloque de firma")
    return xml


def fill_rml(xml: str, *, empresa: str, puesto: str, nombre: str, dni: str, fecha_lugar: str,
             fecha_dia: str, fecha_mes: str, fecha_anio: str, consentimiento_si: bool | None = None) -> str:
    xml = _repl_once(
        xml,
        '<w:t xml:space="preserve"> ...............................................................</w:t>',
        f'<w:t xml:space="preserve"> {empresa}</w:t>',
        "Empresa (63)",
    )
    xml = _repl_once(
        xml,
        '<w:t xml:space="preserve"> ................................................................</w:t>',
        f'<w:t xml:space="preserve"> {puesto}</w:t>',
        "Puesto (64)",
    )
    xml = _repl_once(
        xml,
        '<w:t xml:space="preserve"> ..................................................................................................</w:t>',
        f'<w:t xml:space="preserve"> {nombre}</w:t>',
        "Nombre (98)",
    )
    xml = _repl_once(
        xml,
        '<w:t xml:space="preserve"> .......................................</w:t>',
        f'<w:t xml:space="preserve"> {dni}</w:t>',
        "DNI (39)",
    )
    xml = _repl_once(
        xml,
        '<w:t>……………………………., a …... de ………….. de 201_</w:t>',
        f'<w:t>{fecha_lugar}, a {fecha_dia} de {fecha_mes} de {fecha_anio}</w:t>',
        "fecha",
    )

    # Fdo. del trabajador/a (solo el primero; el de "Empresa" se deja en blanco)
    idx_fdo1 = xml.find('<w:t>Fdo.:……………………………</w:t>')
    if idx_fdo1 == -1:
        raise FillError("No se encontró el bloque 'Fdo.:' del trabajador/a")
    old_fdo = '<w:t>Fdo.:……………………………</w:t>'
    xml = xml[:idx_fdo1] + f'<w:t>Fdo.: {nombre}</w:t>' + xml[idx_fdo1 + len(old_fdo):]

    # Casillas SI / NO de consentimiento — se marca UNA de las dos con una X,
    # nunca las dos. tblpX identifica cada casilla de forma única (451=SI, 250=NO).
    # NOTA: tblpX="250" de la casilla NO es un fix aplicado sobre el original
    # (que traía tblpX="496" y partía visualmente la palabra "No" en "N" + caja + "o").
    # Si se reemplaza la plantilla por una versión nueva del documento, hay que
    # verificar de nuevo estos valores antes de que esta función vuelva a funcionar.
    empty_run = ('<w:r><w:rPr><w:rFonts w:cs="Arial" w:ascii="Arial" w:hAnsi="Arial"/>'
                 '<w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr></w:r>')
    x_run = ('<w:r><w:rPr><w:rFonts w:cs="Arial" w:ascii="Arial" w:hAnsi="Arial"/><w:b/><w:bCs/>'
             '<w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr><w:t>X</w:t></w:r>')

    tbl_si = (
        '<w:tbl><w:tblPr><w:tblpPr w:vertAnchor="text" w:horzAnchor="text" w:leftFromText="141" '
        'w:rightFromText="141" w:tblpX="250" w:tblpY="181"/><w:tblW w:w="299" w:type="dxa"/>'
        '<w:jc w:val="start"/><w:tblInd w:w="70" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:start w:w="70" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:end w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="299"/></w:tblGrid><w:tr><w:trPr><w:trHeight w:val="279" '
        'w:hRule="atLeast"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="299" w:type="dxa"/><w:tcBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:start w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:end w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders></w:tcPr>'
        '<w:p><w:pPr><w:pStyle w:val="Normal"/><w:snapToGrid w:val="false"/><w:jc w:val="both"/>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="16"/>'
        f'<w:szCs w:val="16"/></w:rPr></w:pPr>{empty_run}</w:p></w:tc></w:tr></w:tbl>'
    )

    tbl_no = (
        '<w:tbl><w:tblPr><w:tblpPr w:vertAnchor="text" w:horzAnchor="text" w:leftFromText="141" '
        'w:rightFromText="141" w:tblpX="250" w:tblpY="121"/><w:tblW w:w="300" w:type="dxa"/>'
        '<w:jc w:val="start"/><w:tblInd w:w="70" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:start w:w="70" w:type="dxa"/>'
        '<w:bottom w:w="0" w:type="dxa"/><w:end w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblGrid><w:gridCol w:w="300"/></w:tblGrid><w:tr><w:trPr><w:trHeight w:val="300" '
        'w:hRule="atLeast"/></w:trPr><w:tc><w:tcPr><w:tcW w:w="300" w:type="dxa"/><w:tcBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:start w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        '<w:end w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders></w:tcPr>'
        '<w:p><w:pPr><w:pStyle w:val="Normal"/><w:snapToGrid w:val="false"/><w:jc w:val="both"/>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="16"/>'
        f'<w:szCs w:val="16"/></w:rPr></w:pPr>{empty_run}</w:p></w:tc></w:tr></w:tbl>'
    )

    if consentimiento_si is True:
        xml = _repl_once(xml, tbl_si, tbl_si.replace(empty_run, x_run), "casilla SI consentimiento")
    elif consentimiento_si is False:
        xml = _repl_once(xml, tbl_no, tbl_no.replace(empty_run, x_run), "casilla NO consentimiento")

    return xml


def fill_acuse_acoso(xml: str, *, nombre: str, dni: str, fecha_lugar: str,
                     fecha_dia: str, fecha_mes: str, fecha_anio: str) -> str:
    old_nombre = (
        '<w:color w:val="D0D5DD"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        '<w:t xml:space="preserve">_______________________________________________</w:t>'
    )
    new_nombre = (
        f'<w:color w:val="1A1A1A"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        f'<w:t xml:space="preserve">{nombre}</w:t>'
    )
    xml = _repl_once(xml, old_nombre, new_nombre, "nombre (47 guiones)")

    old_dni = (
        '<w:color w:val="D0D5DD"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        '<w:t xml:space="preserve">________________</w:t>'
    )
    new_dni = (
        f'<w:color w:val="1A1A1A"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>'
        f'<w:t xml:space="preserve">{dni}</w:t>'
    )
    xml = _repl_once(xml, old_dni, new_dni, "DNI (16 guiones)")

    old_fecha = 'En _____________________ a ________ de ________________ de _____________'
    new_fecha = f'En {fecha_lugar} a {fecha_dia} de {fecha_mes} de {fecha_anio}'
    xml = _repl_once(xml, old_fecha, new_fecha, "fecha")
    return xml


def fill_contrato_trabajo(xml: str, *, nombre: str, dni: str, fecha_nacimiento: str,
                          num_afiliacion_ss: str, nivel_formativo: str, nacionalidad: str,
                          municipio_domicilio: str, puesto: str, grupo_profesional: str,
                          funciones: str, fecha_dia: str, fecha_mes: str, fecha_anio: str,
                          periodo_prueba: str, salario: str,
                          trabajo_a_distancia: bool = False) -> str:
    """
    Contrato de trabajo indefinido ORDINARIO (modelo SEPE código 100).

    ⛔ DESACTIVADO el 31/08/2026: la gestoría cambió al modelo INDEFINIDO
    BONIFICADO (código 150). Esta función y templates/contrato_trabajo/ se
    conservan intactas; solo está comentada su entrada en DOCUMENT_FILLERS.
    Para reactivarlo, descomentar esa línea. Ver CLAUDE.md.

    NO incluye el anexo de teletrabajo (todavía no existe como documento —
    pendiente de Jorge). Si trabajo_a_distancia=True, se marca la casilla en
    la cláusula correspondiente, pero el % de teletrabajo NO se usa aquí:
    vive en el anexo aparte que se generará en el futuro.

    fecha_dia/fecha_mes/fecha_anio se usan tanto para "fecha de inicio"
    (cláusula cuarta) como para el día/mes de los DOS bloques de firma del
    documento (el contrato y el anexo de cláusulas adicionales, que
    comparten la misma fecha). El año de los bloques de firma viene fijo
    en la plantilla como "2026" -- si este flujo sigue en uso en 2027,
    hay que revisar y actualizar esa parte de la plantilla maestra.
    """
    # --- Tabla "DATOS DEL/DE LA TRABAJADOR/A" ---
    def insertar_en_vacio(xml, paraId, valor, label):
        m = re.search(rf'(<w:p w14:paraId="{paraId}"[^>]*>.*?)(</w:p>)', xml, re.DOTALL)
        if not m:
            raise FillError(f"{label}: no se encontró el paraId {paraId}")
        nuevo_run = f'<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t>{_esc(valor)}</w:t></w:r>'
        nuevo_para = m.group(1) + nuevo_run + m.group(2)
        return _repl_once(xml, m.group(0), nuevo_para, label)

    xml = insertar_en_vacio(xml, '60A7950A', nombre, "nombre trabajador")
    xml = insertar_en_vacio(xml, '5A1FEE9C', dni, "NIF/NIE trabajador")
    xml = insertar_en_vacio(xml, '3EE9EC0E', fecha_nacimiento, "fecha nacimiento")
    xml = insertar_en_vacio(xml, '561FB85F', num_afiliacion_ss, "nº afiliación SS")
    xml = insertar_en_vacio(xml, '3D984518', nacionalidad, "nacionalidad")
    xml = insertar_en_vacio(xml, '385B5284', municipio_domicilio, "municipio domicilio")

    # El placeholder original traía "Times New Roman" harcodeado en el run
    # (distinto a la fuente del resto de la tabla) y le faltaba la sangría
    # izquierda que sí tienen las celdas hermanas (nombre/DNI/municipio,
    # w:ind w:left="71"). Se corrigen ambas cosas en el mismo reemplazo.
    old_nivel = (
        '<w:pPr><w:pStyle w:val="TableParagraph"/>'
        '<w:rPr><w:rFonts w:ascii="Times New Roman"/><w:sz w:val="16"/></w:rPr></w:pPr>'
        '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman"/><w:sz w:val="16"/></w:rPr>'
        '<w:t xml:space="preserve"> </w:t></w:r>'
    )
    new_nivel = (
        '<w:pPr><w:pStyle w:val="TableParagraph"/><w:ind w:left="71"/>'
        '<w:rPr><w:sz w:val="16"/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">{_esc(nivel_formativo)}</w:t></w:r>'
    )
    xml = _repl_once(xml, old_nivel, new_nivel, "nivel formativo")

    # --- Cláusula PRIMERA: puesto, grupo profesional, funciones ---
    old_puesto = '<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:tab/><w:t>.</w:t></w:r>'
    new_puesto = (
        f'<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        f'<w:t xml:space="preserve"> {_esc(puesto)}</w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>.</w:t></w:r>'
    )
    xml = _repl_once(xml, old_puesto, new_puesto, "puesto (cláusula primera)")

    old_grupo = (
        '<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        '<w:t xml:space="preserve"> </w:t></w:r>'
        '<w:r><w:rPr><w:spacing w:val="80"/><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        '<w:t xml:space="preserve"> </w:t></w:r>'
    )
    new_grupo = f'<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:t xml:space="preserve">{_esc(grupo_profesional)}</w:t></w:r>'
    xml = _repl_once(xml, old_grupo, new_grupo, "grupo profesional")

    # Se escapa el texto libre de "funciones" para que, si llegara con marcado
    # (p.ej. restos de formato tipo tachado copiados de otra fuente), se inserte
    # como texto literal en vez de ser interpretado como XML del documento.
    old_funciones = '<w:t>. para la realización de las funciones (4)</w:t><w:tab/><w:tab/><w:t xml:space="preserve">. de acuerdo'
    funciones_sin_punto = _esc(funciones.rstrip().rstrip("."))
    new_funciones = f'<w:t xml:space="preserve">. para la realización de las funciones (4) {funciones_sin_punto}</w:t><w:t xml:space="preserve">. de acuerdo'
    xml = _repl_once(xml, old_funciones, new_funciones, "funciones del puesto")

    # --- Checkbox "Trabajo a distancia" (mecanismo VML, no tabla) ---
    if trabajo_a_distancia:
        old_tad = '</mc:AlternateContent></w:r><w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>Trabajo</w:t></w:r>'
        new_tad = (
            '</mc:AlternateContent></w:r>'
            '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">X </w:t></w:r>'
            '<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>Trabajo</w:t></w:r>'
        )
        xml = _repl_once(xml, old_tad, new_tad, "checkbox trabajo a distancia")

    # --- Cláusula CUARTA: fecha de inicio, período de prueba ---
    old_fecha_inicio = '<w:t xml:space="preserve">fecha </w:t></w:r><w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:t>,</w:t></w:r>'
    new_fecha_inicio = (
        f'<w:t xml:space="preserve">fecha </w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">{_esc(fecha_dia)} de {_esc(fecha_mes)} de {_esc(fecha_anio)}</w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="18"/></w:rPr><w:t>,</w:t></w:r>'
    )
    xml = _repl_once(xml, old_fecha_inicio, new_fecha_inicio, "fecha de inicio")

    old_periodo = (
        '<w:r><w:rPr><w:spacing w:val="80"/><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        '<w:t xml:space="preserve"> </w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:tab/></w:r>'
    )
    new_periodo = f'<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:t xml:space="preserve">{_esc(periodo_prueba)} meses</w:t></w:r>'
    xml = _repl_once(xml, old_periodo, new_periodo, "período de prueba")

    # --- Cláusula QUINTA: salario ---
    old_salario = (
        '<w:t xml:space="preserve">: el/la trabajador/a percibirá una retribución total de </w:t></w:r>'
        '<w:r><w:rPr><w:spacing w:val="80"/><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        '<w:t xml:space="preserve"> </w:t></w:r>'
    )
    new_salario = (
        '<w:t xml:space="preserve">: el/la trabajador/a percibirá una retribución total de </w:t></w:r>'
        f'<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:t xml:space="preserve">{_esc(salario)}</w:t></w:r>'
    )
    xml = _repl_once(xml, old_salario, new_salario, "salario")

    old_periodicidad = (
        '<w:t xml:space="preserve">euros brutos (15) </w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:tab/><w:tab/></w:r>'
    )
    new_periodicidad = (
        '<w:t xml:space="preserve">euros brutos (15) </w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="18"/><w:u w:val="single"/></w:rPr><w:t xml:space="preserve">anuales</w:t></w:r>'
    )
    xml = _repl_once(xml, old_periodicidad, new_periodicidad, "periodicidad salario")

    # --- Fecha de firma (aparece 2 veces: contrato base + anexo de cláusulas adicionales) ---
    old_dia1 = '<w:t xml:space="preserve">a de</w:t>'
    new_dia1 = f'<w:t xml:space="preserve">a {_esc(fecha_dia)} de</w:t>'
    xml = _repl_once(xml, old_dia1, new_dia1, "día firma (bloque 1)")

    old_dia2 = '<w:t xml:space="preserve">a de </w:t>'
    new_dia2 = f'<w:t xml:space="preserve">a {_esc(fecha_dia)} de </w:t>'
    xml = _repl_once(xml, old_dia2, new_dia2, "día firma (bloque 2)")

    old_mes = (
        '<w:r><w:rPr><w:spacing w:val="40"/><w:sz w:val="12"/></w:rPr><w:t xml:space="preserve"> </w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="12"/></w:rPr><w:t>de 2026</w:t></w:r>'
    )
    n_mes = xml.count(old_mes)
    if n_mes != 2:
        raise FillError(f"mes firma: aparece {n_mes} veces en la plantilla, se esperaban 2")
    new_mes = (
        f'<w:r><w:rPr><w:sz w:val="12"/></w:rPr><w:t xml:space="preserve"> {_esc(fecha_mes)} </w:t></w:r>'
        '<w:r><w:rPr><w:sz w:val="12"/></w:rPr><w:t>de 2026</w:t></w:r>'
    )
    xml = xml.replace(old_mes, new_mes)

    # --- Salto de página forzado antes del bloque "INDEFINIDO ORDINARIO" /
    #     "CÓDIGO DE CONTRATO" ---
    # Ese bloque (casilla "INDEFINIDO ORDINARIO" + tabla "CÓDIGO DE
    # CONTRATO") se dibuja con formas ancladas a coordenadas ABSOLUTAS de
    # página (w10:wrap/wp:anchor con relativeFrom="page"), calibradas
    # asumiendo que el párrafo que las contiene cae justo al principio de
    # una página. En la plantilla original esto ocurre "por casualidad"
    # (no hay salto de página explícito): si el texto de "funciones" (u
    # otro campo anterior) ocupa más o menos líneas de las previstas,
    # todo el contenido se repagina y ese párrafo deja de caer al
    # principio de página, con lo que la casilla y la tabla quedan
    # dibujadas en un sitio distinto al del texto que las acompaña
    # (descoloque visual, confirmado con datos de funciones largos).
    # Forzar el salto de página aquí garantiza que el bloque siempre
    # empiece en la parte superior de una página nueva, sea cual sea la
    # longitud del contenido anterior.
    old_break_anchor = (
        '<w:p w14:paraId="46C937E3" w14:textId="77777777" w:rsidR="00FE6C63" '
        'w:rsidRDefault="00836B5C"><w:pPr><w:pStyle w:val="Textoindependiente"/>'
        '<w:rPr><w:sz w:val="20"/></w:rPr></w:pPr>'
    )
    new_break_anchor = (
        '<w:p w14:paraId="46C937E3" w14:textId="77777777" w:rsidR="00FE6C63" '
        'w:rsidRDefault="00836B5C"><w:pPr><w:pStyle w:val="Textoindependiente"/>'
        '<w:pageBreakBefore/><w:rPr><w:sz w:val="20"/></w:rPr></w:pPr>'
    )
    xml = _repl_once(xml, old_break_anchor, new_break_anchor, "salto de página INDEFINIDO ORDINARIO/CÓDIGO DE CONTRATO")

    return xml


# ---------------------------------------------------------------------
# Helpers específicos del Modelo 150
# ---------------------------------------------------------------------

# Un "hueco" en esta plantilla es un <w:t> que solo contiene espacios y/o
# guiones bajos (a diferencia de contrato_trabajo, donde había 4 mecanismos
# distintos). Se localiza a partir de un ancla de texto contiguo, que se
# valida como única igual que hace _repl_once.
_HUECO_150 = re.compile(r'<w:t(?: [^>]*)?>([\s_]*)</w:t>')
_RUN_VACIO_150 = re.compile(r'<w:r>(<w:rPr>.*?</w:rPr>)</w:r>', re.DOTALL)
_RPR_150 = re.compile(r'<w:rPr>.*?</w:rPr>', re.DOTALL)


def _rellenar_hueco_150(xml: str, ancla: str, valor: str, label: str, ventana: int = 700) -> str:
    """Rellena el primer hueco que aparece después de `ancla`."""
    n = xml.count(ancla)
    if n != 1:
        raise FillError(f"{label}: el ancla aparece {n} veces en la plantilla, se esperaba 1")
    inicio = xml.index(ancla) + len(ancla)
    m = _HUECO_150.search(xml, inicio, inicio + ventana)
    if not m:
        raise FillError(f"{label}: no se encontró hueco en los {ventana} caracteres tras el ancla")
    return xml[:m.start()] + f'<w:t xml:space="preserve">{_esc(valor)}</w:t>' + xml[m.end():]


def _rellenar_celda_150(xml: str, etiqueta: str, valor: str, label: str) -> str:
    """
    Rellena la celda de la tabla "DATOS DEL/DE LA TRABAJADOR/A" que lleva
    `etiqueta`. Hay tres formas de hueco según la celda:
      a) un <w:t> de solo espacios detrás de la etiqueta,
      b) un <w:r> sin <w:t> (párrafo vacío) al que hay que insertarle texto,
      c) solo la etiqueta (y a veces un <w:br/>): se añade un run nuevo.
    """
    marca = f'>{etiqueta}</w:t>'
    n = xml.count(marca)
    if n != 1:
        raise FillError(f"{label}: la etiqueta {etiqueta!r} aparece {n} veces, se esperaba 1")

    pos = xml.index(marca)
    ini_celda = xml.rfind("<w:tc>", 0, pos)
    if ini_celda < 0:
        raise FillError(f"{label}: no se localizó la celda contenedora")
    fin_celda = xml.index("</w:tc>", pos) + len("</w:tc>")
    celda = xml[ini_celda:fin_celda]
    desde = celda.index(marca)

    m = _HUECO_150.search(celda, desde)
    if m:
        nueva = celda[:m.start()] + f'<w:t xml:space="preserve">{_esc(valor)}</w:t>' + celda[m.end():]
        return xml[:ini_celda] + nueva + xml[fin_celda:]

    m = _RUN_VACIO_150.search(celda, desde)
    if m:
        run = f'<w:r>{m.group(1)}<w:t xml:space="preserve">{_esc(valor)}</w:t></w:r>'
        nueva = celda[:m.start()] + run + celda[m.end():]
        return xml[:ini_celda] + nueva + xml[fin_celda:]

    cierre = celda.rfind("</w:p>")
    if cierre == -1:
        raise FillError(f"{label}: la celda de {etiqueta!r} no tiene ningún párrafo")
    rpr = ""
    for candidato in reversed(_RPR_150.findall(celda[:cierre])):
        if "<w:b/>" not in candidato:  # el run de la etiqueta va en negrita
            rpr = candidato
            break
    run = f'<w:r>{rpr}<w:t xml:space="preserve">{_esc(valor)}</w:t></w:r>'
    nueva = celda[:cierre] + run + celda[cierre:]
    return xml[:ini_celda] + nueva + xml[fin_celda:]


_MESES_150 = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _parsear_importe_es(valor) -> Decimal:
    """Acepta 41000, '41.000', '41.000,50', 41000.0 -> Decimal."""
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    s = str(valor).strip().replace("€", "").replace(" ", "")
    if not s:
        raise FillError("salario vacío")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1 or (s.count(".") == 1 and len(s.split(".")[1]) == 3):
        s = s.replace(".", "")
    try:
        return Decimal(s)
    except Exception as exc:
        raise FillError(f"no se pudo interpretar el salario: {valor!r}") from exc


def _formatear_euros_es(cantidad: Decimal) -> str:
    """Decimal('1250.5') -> '1.250,50€'"""
    entero, decimal = f"{cantidad:.2f}".split(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    return f"{'.'.join(grupos)},{decimal}€"


def calcular_compensacion_no_competencia(salario_anual) -> str:
    """
    Cláusula adicional QUINTA: 10% de la remuneración fija bruta MENSUAL.

    Se calcula con Decimal y ROUND_HALF_UP (criterio contable), NO con
    round() de Python, que usa redondeo bancario y daría importes
    incorrectos en un concepto que acaba en la nómina.
    """
    anual = _parsear_importe_es(salario_anual)
    if anual <= 0:
        raise FillError(f"salario debe ser positivo, recibido: {anual}")
    mensual = anual / Decimal("12")
    importe = (mensual * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _formatear_euros_es(importe)


def _fecha_inicio_ddmmaa(fecha_dia: str, fecha_mes: str, fecha_anio: str) -> str:
    """'16', 'MARZO', '2026' -> '16/03/26' (formato del modelo 150)."""
    mes = _MESES_150.get(str(fecha_mes).strip().lower())
    if mes is None:
        try:
            mes = int(str(fecha_mes).strip())
        except ValueError:
            raise FillError(f"mes no reconocido: {fecha_mes!r}")
    anio = str(fecha_anio).strip()[-2:]
    return f"{int(str(fecha_dia).strip()):02d}/{mes:02d}/{anio}"


# ---------------------------------------------------------------------
# Modelo 150 — INDEFINIDO BONIFICADO
# ---------------------------------------------------------------------

def fill_contrato_trabajo_150(
    xml: str, *,
    nombre: str, dni: str, fecha_nacimiento: str, num_afiliacion_ss: str,
    nivel_formativo: str, nacionalidad: str, puesto: str, grupo_profesional: str,
    periodo_prueba: str, salario: str,
    fecha_dia: str, fecha_mes: str, fecha_anio: str,
    municipio_domicilio: str = "", pais_domicilio: str = "",
    fecha_inicio: str = "", horas_semana: str = "40",
    jornada_desde: str = "Lunes", jornada_hasta: str = "Viernes",
    partes: dict | None = None,
) -> dict:
    """
    Contrato de trabajo INDEFINIDO BONIFICADO (modelo SEPE código 150).

    Sustituye a `contrato_trabajo` (INDEFINIDO ORDINARIO), que queda
    desregistrado pero con su código y plantilla intactos.

    Diferencias relevantes respecto al anterior:
      - No tiene campo `funciones` ni casilla "Trabajo a distancia".
      - Añade la cláusula adicional SÉPTIMA de I+D+i.
      - La compensación del pacto de no competencia es un campo CALCULADO
        a partir del salario (10% de la mensualidad), no un dato de entrada.
      - La fecha de firma del pie ("En BARCELONA a __ de __ de __") vive en
        word/footer1.xml, no en document.xml, así que esta función NO la
        rellena: main.py solo entrega document.xml al filler.
    """
    # --- Tabla "DATOS DEL/DE LA TRABAJADOR/A" ---
    xml = _rellenar_celda_150(xml, "D./DÑA.", nombre, "nombre trabajador")
    xml = _rellenar_celda_150(xml, "NIF/NIE (2)", dni, "NIF/NIE trabajador")
    xml = _rellenar_celda_150(xml, "FECHA DE NACIMIENTO", fecha_nacimiento, "fecha nacimiento")
    xml = _rellenar_celda_150(xml, "Nº AFILIACIÓN  S. S.", num_afiliacion_ss, "nº afiliación SS")
    xml = _rellenar_celda_150(xml, "NIVEL FORMATIVO", nivel_formativo, "nivel formativo")
    xml = _rellenar_celda_150(xml, "NACIONALIDAD", nacionalidad, "nacionalidad")
    if municipio_domicilio:
        xml = _rellenar_celda_150(xml, "MUNICIPIO DEL DOMICILIO", municipio_domicilio, "municipio domicilio")
    if pais_domicilio:
        xml = _rellenar_celda_150(xml, "PAÍS DOMICILIO ", pais_domicilio, "país domicilio")

    # --- Cláusula PRIMERA: puesto y categoría profesional ---
    # El guion bajo suelto tras "de" forma parte del hueco original.
    xml = _repl_once(
        xml,
        "categoría   o nivel profesional de            _",
        "categoría   o nivel profesional de",
        "guion suelto de categoría profesional",
    )
    xml = _rellenar_hueco_150(xml, "prestará  sus  servicios  como  (4)", puesto, "puesto")
    # el espacio va dentro del valor: el <w:t> del ancla no lleva
    # xml:space="preserve" y Word/LibreOffice recortarían un espacio final
    xml = _rellenar_hueco_150(xml, "categoría   o nivel profesional de", f" {grupo_profesional}", "categoría profesional")

    # --- Cláusula SEGUNDA: fecha de inicio y período de prueba ---
    inicio = fecha_inicio or _fecha_inicio_ddmmaa(fecha_dia, fecha_mes, fecha_anio)
    xml = _rellenar_hueco_150(xml, "iniciándose la relación laboral con fecha", inicio, "fecha de inicio")
    xml = _rellenar_hueco_150(xml, "un período de prueba de  (5)", periodo_prueba, "período de prueba")

    # --- Cláusula TERCERA: jornada ---
    xml = _rellenar_hueco_150(xml, "la jornada de trabajo será de", horas_semana, "horas semanales")
    xml = _rellenar_hueco_150(xml, "horas semanales, prestadas de", jornada_desde, "jornada desde")
    xml = _rellenar_hueco_150(xml, "horas semanales, prestadas de", jornada_hasta, "jornada hasta")

    # --- Cláusula QUINTA: salario ---
    xml = _rellenar_hueco_150(xml, "percibirá una retribución total de", salario, "salario")

    # --- Cláusula adicional QUINTA: compensación por no competencia (calculada) ---
    xml = _repl_once(
        xml,
        "{{COMPENSACION_NO_COMPETENCIA}}",
        _esc(calcular_compensacion_no_competencia(salario)),
        "compensación pacto de no competencia",
    )

    # --- Pie: fecha de firma (word/footer1.xml) ---
    if partes is None or "word/footer1.xml" not in partes:
        raise FillError(
            "no se recibió word/footer1.xml: main.py debe pasar el parámetro "
            "`partes` para poder rellenar la fecha de firma"
        )
    pie = partes["word/footer1.xml"]
    # Los tres huecos (día, mes, año) cuelgan del mismo ancla y se rellenan
    # en orden: cada uno deja de ser "solo espacios" al rellenarse, así que
    # la llamada siguiente cae en el hueco posterior.
    ancla_pie = '<w:t xml:space="preserve"> a </w:t>'
    pie = _rellenar_hueco_150(pie, ancla_pie, fecha_dia, "día firma", ventana=1200)
    pie = _rellenar_hueco_150(pie, ancla_pie, fecha_mes, "mes firma", ventana=1200)
    pie = _rellenar_hueco_150(pie, ancla_pie, fecha_anio, "año firma", ventana=1200)

    return {"word/document.xml": xml, "word/footer1.xml": pie}


# ---------------------------------------------------------------------
# Registro de documentos disponibles
# ---------------------------------------------------------------------

DOCUMENT_FILLERS = {
    "retribucion_flexible": fill_retribucion_flexible,
    "confidencialidad": fill_confidencialidad,
    "consentimiento_empleados": fill_consentimiento_empleados,
    "rml": fill_rml,
    "acuse_acoso": fill_acuse_acoso,
    "contrato_trabajo_150": fill_contrato_trabajo_150,

    # DESACTIVADO (31/08/2026): la gestoría cambió el modelo de contrato del
    # INDEFINIDO ORDINARIO (código 100) al INDEFINIDO BONIFICADO (código 150).
    # La función fill_contrato_trabajo y templates/contrato_trabajo/ se
    # conservan intactas: para reactivarlo basta descomentar esta línea.
    # "contrato_trabajo": fill_contrato_trabajo,
}
