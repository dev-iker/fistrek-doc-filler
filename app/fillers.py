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
"""


class FillError(Exception):
    """Se lanza cuando un hueco esperado no aparece exactamente 1 vez."""
    pass


def _repl_once(xml: str, old: str, new: str, label: str) -> str:
    n = xml.count(old)
    if n != 1:
        raise FillError(f"{label}: aparece {n} veces en la plantilla, se esperaba 1")
    return xml.replace(old, new, 1)


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
             fecha_dia: str, fecha_mes: str, fecha_anio: str, consentimiento_si: bool = True) -> str:
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

    if consentimiento_si:
        xml = _repl_once(xml, tbl_si, tbl_si.replace(empty_run, x_run), "casilla SI consentimiento")
    else:
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


# Registro de documentos disponibles: key -> (nombre carpeta template, función de relleno)
DOCUMENT_FILLERS = {
    "retribucion_flexible": fill_retribucion_flexible,
    "confidencialidad": fill_confidencialidad,
    "consentimiento_empleados": fill_consentimiento_empleados,
    "rml": fill_rml,
    "acuse_acoso": fill_acuse_acoso,
}
