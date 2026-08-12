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
import re
from xml.sax.saxutils import escape as _esc


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
        'w:rightFromText="141" w:tblpX="451" w:tblpY="181"/><w:tblW w:w="299" w:type="dxa"/>'
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


def fill_contrato_trabajo(xml: str, *, nombre: str, dni: str, fecha_nacimiento: str,
                           num_afiliacion_ss: str, nivel_formativo: str, nacionalidad: str,
                           municipio_domicilio: str, puesto: str, grupo_profesional: str,
                           funciones: str, fecha_dia: str, fecha_mes: str, fecha_anio: str,
                           periodo_prueba: str, salario: str,
                           trabajo_a_distancia: bool = False) -> str:
    """
    Contrato de trabajo indefinido (modelo SEPE). NO incluye el anexo de
    teletrabajo (todavía no existe como documento — pendiente de Jorge).
    Si trabajo_a_distancia=True, se marca la casilla en la cláusula
    correspondiente, pero el % de teletrabajo NO se usa aquí: vive en el
    anexo aparte que se generará en el futuro.

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

    old_nivel = '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman"/><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">  </w:t></w:r>'
    new_nivel = f'<w:r><w:rPr><w:rFonts w:ascii="Times New Roman"/><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">{_esc(nivel_formativo)}</w:t></w:r>'
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
        '<w:t xml:space="preserve">     </w:t></w:r>'
        '<w:r><w:rPr><w:spacing w:val="80"/><w:sz w:val="18"/><w:u w:val="single"/></w:rPr>'
        '<w:t xml:space="preserve">  </w:t></w:r>'
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
    old_dia1 = '<w:t xml:space="preserve">a  de</w:t>'
    new_dia1 = f'<w:t xml:space="preserve">a {_esc(fecha_dia)} de</w:t>'
    xml = _repl_once(xml, old_dia1, new_dia1, "día firma (bloque 1)")

    old_dia2 = '<w:t xml:space="preserve">a  de </w:t>'
    new_dia2 = f'<w:t xml:space="preserve">a {_esc(fecha_dia)} de </w:t>'
    xml = _repl_once(xml, old_dia2, new_dia2, "día firma (bloque 2)")

    old_mes = (
        '<w:r><w:rPr><w:spacing w:val="40"/><w:sz w:val="12"/></w:rPr><w:t xml:space="preserve">  </w:t></w:r>'
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

    return xml


# Registro de documentos disponibles: key -> (nombre carpeta template, función de relleno)
DOCUMENT_FILLERS = {
    "retribucion_flexible": fill_retribucion_flexible,
    "confidencialidad": fill_confidencialidad,
    "consentimiento_empleados": fill_consentimiento_empleados,
    "rml": fill_rml,
    "acuse_acoso": fill_acuse_acoso,
    "contrato_trabajo": fill_contrato_trabajo,
}
