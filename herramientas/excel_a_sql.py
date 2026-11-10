"""
Convierte el export de Oxford Abstracts (xlsx) en SQL para cargar en Supabase
(SQL Editor). Opcionalmente añade los "comentarios sobre el texto" (texto
seleccionado + comentario) desde un documento .odt o .txt copiado de Oxford
Abstracts.

Uso:
    pip install pandas openpyxl
    python excel_a_sql.py Revision_oa_export.xlsx 02_datos.sql
    python excel_a_sql.py Revision_oa_export.xlsx 02_datos.sql ComentariosSobreTexto.odt
    # Solo actualizar comentarios (sin tocar nada más):
    python excel_a_sql.py Revision_oa_export.xlsx 02b_comentarios_texto.sql ComentariosSobreTexto.odt --solo-comentarios

Garantías:
  - Omite los envíos con decisión "Withdrawn".
  - NO exporta nombres, correos ni calificaciones de los revisores: se
    muestran como "Revisor 1", "Revisor 2"...
  - Nunca toca título, autores, resumen, respuesta ni estado de los autores.
  - Nunca cambia los comentarios de un resumen ya entregado (estado 'listo').

El SQL resultante contiene los comentarios de revisión: no lo subas a GitHub.
"""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd

ORDINALES = ["1st", "2nd", "3rd", "4th", "5th"]


def limpio(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def sql_texto(valor):
    return "'" + limpio(valor).replace("'", "''") + "'"


# ---------- Lectura del documento de comentarios sobre el texto ----------
def parrafos_odt(ruta):
    ns = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    with zipfile.ZipFile(ruta) as z:
        raiz = ET.fromstring(z.read("content.xml"))
    salida = []
    for el in raiz.iter():
        if el.tag in (ns + "p", ns + "h"):
            partes = []
            for t in el.iter():
                if t.text:
                    partes.append(t.text)
                if t.tag == ns + "s":
                    partes.append(" " * int(t.get(ns + "c", "1")))
                if t.tag in (ns + "tab", ns + "line-break"):
                    partes.append(" ")
                if t is not el and t.tail:
                    partes.append(t.tail)
            salida.append("".join(partes))
    return salida


def leer_comentarios(ruta):
    """Devuelve {id: [{"email", "generales", "anotaciones": [{"seleccion", "comentario"}]}]}"""
    if ruta.lower().endswith(".odt"):
        lineas = parrafos_odt(ruta)
    else:
        with open(ruta, encoding="utf-8") as fh:
            lineas = fh.read().splitlines()
    lineas = [l.strip() for l in lineas]
    lineas = [l for l in lineas if l]

    re_envio = re.compile(r"^(\d+)\s*,\s*(.+)$")
    re_revisor = re.compile(r"^\d+\.\s+(\S+@\S+?),")
    re_coment = re.compile(r"^Comment\s+\d{1,2}/\d{1,2}/\d{2,4}")
    re_desactualizado = re.compile(r"^Outdated comment\s+\d{1,2}/\d{1,2}/\d{2,4}")
    re_actualizado = re.compile(r"^Submission updated\s+\d{1,2}/\d{1,2}/\d{2,4}")
    re_separador = re.compile(r"^_{3,}-*$")

    datos, envio, revisor, modo, anot = {}, None, None, None, None
    i = 0
    while i < len(lineas):
        l = lineas[i]
        sig = lineas[i + 1] if i + 1 < len(lineas) else ""
        m = re_envio.match(l)
        if m and sig.lower().startswith("description"):
            envio = int(m.group(1))
            datos.setdefault(envio, [])
            revisor, modo, anot = None, None, None
            i += 2
            continue
        if re_separador.match(l):
            envio, revisor, modo, anot = None, None, None, None
        elif envio is not None and re_revisor.match(l):
            email = re_revisor.match(l).group(1).lower()
            revisor = {"email": email, "generales": "", "anotaciones": []}
            datos[envio].append(revisor)
            modo, anot = None, None
            if sig.lower().startswith(email):
                i += 1  # línea repetida con el mismo correo
        elif revisor is None:
            pass
        elif l == "Comentarios generales":
            modo = "generales"
        elif l == "Comentarios sobre el texto":
            modo = "texto"
        elif l == "Selected text:":
            anot = {"seleccion": "", "comentario": ""}
            revisor["anotaciones"].append(anot)
            modo = "seleccion"
        elif re_coment.match(l) and anot is not None:
            modo = "comentario"
        elif re_desactualizado.match(l):
            # Comentario hecho sobre una versión anterior: ya no tiene texto seleccionado
            anot = {"seleccion": "", "comentario": ""}
            revisor["anotaciones"].append(anot)
            modo = "comentario"
        elif re_actualizado.match(l):
            pass
        elif modo == "generales":
            revisor["generales"] = (revisor["generales"] + "\n" + l).strip()
        elif modo == "seleccion":
            anot["seleccion"] = (anot["seleccion"] + " " + l).strip()
        elif modo == "comentario":
            anot["comentario"] = (anot["comentario"] + "\n" + l).strip()
        i += 1
    return datos


# ---------- Construcción de las revisiones de cada resumen ----------
def revisiones(fila, columnas, comentarios_doc):
    doc = list(comentarios_doc.get(int(fila["Submission Id"]), []))
    salida = []
    for ordinal in ORDINALES:
        col_gen = f"Comentarios generales: {ordinal} review"
        col_txt = f"Comentarios sobre el texto: {ordinal} review"
        col_mail = f"Reviewer email: {ordinal} review"
        if col_gen not in columnas and col_txt not in columnas:
            continue
        email = limpio(fila.get(col_mail)).lower()
        generales = limpio(fila.get(col_gen))
        texto = limpio(fila.get(col_txt))
        anotaciones = []
        for r in doc:
            if email and r["email"] == email:
                anotaciones = r["anotaciones"]
                generales = generales or r["generales"]
                doc.remove(r)
                break
        if generales or texto or anotaciones:
            salida.append({"generales": generales, "texto": texto, "anotaciones": anotaciones})
    for r in doc:  # revisores del documento que no estén en el Excel
        if r["generales"] or r["anotaciones"]:
            salida.append({"generales": r["generales"], "texto": "", "anotaciones": r["anotaciones"]})
    for n, r in enumerate(salida, start=1):
        r["revisor"] = n
    return [{"revisor": r["revisor"], "generales": r["generales"], "texto": r["texto"],
             "anotaciones": r["anotaciones"]} for r in salida]


def main(entrada, salida, ruta_comentarios=None, solo_comentarios=False):
    df = pd.read_excel(entrada)
    columnas = set(df.columns)
    df = df[df["Decision"].astype(str).str.strip() != "Withdrawn"]
    comentarios_doc = leer_comentarios(ruta_comentarios) if ruta_comentarios else {}

    lineas = ["-- Generado por excel_a_sql.py. Contiene comentarios de revisión: NO subir a GitHub.",
              "begin;"]
    n = 0
    for _, f in df.iterrows():
        sid = int(f["Submission Id"])
        revs = sql_texto(json.dumps(revisiones(f, columnas, comentarios_doc), ensure_ascii=False)) + "::jsonb"
        if solo_comentarios:
            if sid not in comentarios_doc:
                continue
            lineas.append(f"update public.resumenes set revisiones = {revs} "
                          f"where id = {sid} and estado <> 'listo';")
            n += 1
            continue
        nombre = f"{limpio(f['Submitter first name'])} {limpio(f['Submitter last name'])}".strip()
        valores = ", ".join([
            str(sid), sql_texto(limpio(f["Submitter email"]).lower()), sql_texto(nombre),
            sql_texto(f["Simposio"]), sql_texto(f["Decision"]), sql_texto(f["Título"]),
            sql_texto(f["Authors"]), sql_texto(f["Presenting"]), sql_texto(f["Resumen"]), revs,
            sql_texto(f["Título"]), sql_texto(f["Authors"]), sql_texto(f["Resumen"]),
        ])
        lineas.append(
            "insert into public.resumenes (id, correo, nombre_remitente, simposio, decision, "
            "titulo_original, autores_original, presentador, resumen_original, revisiones, "
            "titulo, autores, resumen) values (" + valores + ")\n"
            "  on conflict (id) do update set correo = excluded.correo, "
            "nombre_remitente = excluded.nombre_remitente, simposio = excluded.simposio, "
            "decision = excluded.decision, titulo_original = excluded.titulo_original, "
            "autores_original = excluded.autores_original, presentador = excluded.presentador, "
            "resumen_original = excluded.resumen_original, "
            "revisiones = case when resumenes.estado = 'listo' then resumenes.revisiones "
            "else excluded.revisiones end;")
        n += 1
    lineas.append("commit;")

    with open(salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    total_anot = sum(len(r["anotaciones"]) for v in comentarios_doc.values() for r in v)
    print(f"{n} resúmenes escritos en {salida}"
          + (f"; {len(comentarios_doc)} con comentarios sobre el texto ({total_anot} anotaciones)"
             if comentarios_doc else ""))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) not in (2, 3):
        print(__doc__)
        sys.exit(1)
    main(args[0], args[1], args[2] if len(args) == 3 else None, "--solo-comentarios" in sys.argv)
