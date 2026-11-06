"""
Convierte el export de Oxford Abstracts (xlsx) en un archivo SQL para cargar
en Supabase (SQL Editor).

Uso:
    pip install pandas openpyxl
    python excel_a_sql.py Revision_oa_export.xlsx 02_datos.sql

Qué hace:
  - Omite los envíos con decisión "Withdrawn".
  - NO exporta nombres, correos ni calificaciones de los revisores: los
    comentarios se muestran a los autores como "Revisor 1" y "Revisor 2".
  - Usa "on conflict do update" solo sobre los campos originales, así que si
    vuelves a cargar el archivo NO se pierden las ediciones de los autores.

El SQL resultante contiene los comentarios de revisión: no lo subas a GitHub.
"""
import json
import sys

import pandas as pd

ORDINALES = ["1st", "2nd", "3rd", "4th", "5th"]


def limpio(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def sql_texto(valor):
    return "'" + limpio(valor).replace("'", "''") + "'"


def revisiones(fila, columnas):
    salida = []
    n = 0
    for ordinal in ORDINALES:
        col_gen = f"Comentarios generales: {ordinal} review"
        col_txt = f"Comentarios sobre el texto: {ordinal} review"
        if col_gen not in columnas and col_txt not in columnas:
            continue
        generales = limpio(fila.get(col_gen))
        texto = limpio(fila.get(col_txt))
        if not generales and not texto:
            continue
        n += 1
        salida.append({"revisor": n, "generales": generales, "texto": texto})
    return salida


def main(entrada, salida):
    df = pd.read_excel(entrada)
    columnas = set(df.columns)
    df = df[df["Decision"].astype(str).str.strip() != "Withdrawn"]

    lineas = [
        "-- Generado por excel_a_sql.py. Contiene comentarios de revisión: NO subir a GitHub.",
        "begin;",
    ]
    for _, f in df.iterrows():
        nombre = f"{limpio(f['Submitter first name'])} {limpio(f['Submitter last name'])}".strip()
        revs = json.dumps(revisiones(f, columnas), ensure_ascii=False)
        valores = ", ".join([
            str(int(f["Submission Id"])),
            sql_texto(limpio(f["Submitter email"]).lower()),
            sql_texto(nombre),
            sql_texto(f["Simposio"]),
            sql_texto(f["Decision"]),
            sql_texto(f["Título"]),
            sql_texto(f["Authors"]),
            sql_texto(f["Presenting"]),
            sql_texto(f["Resumen"]),
            sql_texto(revs) + "::jsonb",
            sql_texto(f["Título"]),
            sql_texto(f["Authors"]),
            sql_texto(f["Resumen"]),
        ])
        lineas.append(
            "insert into public.resumenes (id, correo, nombre_remitente, simposio, decision, "
            "titulo_original, autores_original, presentador, resumen_original, revisiones, "
            "titulo, autores, resumen) values (" + valores + ")\n"
            "  on conflict (id) do update set correo = excluded.correo, "
            "nombre_remitente = excluded.nombre_remitente, simposio = excluded.simposio, "
            "decision = excluded.decision, titulo_original = excluded.titulo_original, "
            "autores_original = excluded.autores_original, presentador = excluded.presentador, "
            "resumen_original = excluded.resumen_original, revisiones = excluded.revisiones;"
        )
    lineas.append("commit;")

    with open(salida, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")
    print(f"{len(df)} resúmenes escritos en {salida} "
          f"({df['Submitter email'].str.lower().nunique()} correos distintos)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
