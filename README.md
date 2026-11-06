# Corrección de resúmenes — 3er Congreso Colombiano de Bioacústica y Ecoacústica

Página estática (GitHub Pages) + Supabase (ingreso con correo y base de datos con reglas de acceso).

```
docs/                     ← lo que publica GitHub Pages
  index.html              ← la plataforma
  config.js               ← URL y clave pública de Supabase
  logo.png
supabase/
  01_esquema.sql          ← tablas, reglas de seguridad y administradores
herramientas/
  excel_a_sql.py          ← convierte el export de Oxford Abstracts en 02_datos.sql
```

**02_datos.sql y el Excel NO van al repositorio** (tienen los comentarios de revisión). El `.gitignore` ya los excluye.

## 1. Crear el proyecto en Supabase
1. https://supabase.com → New project. Región: `South America (São Paulo)`. Guarda la contraseña de la base de datos.
2. Project Settings → API Keys: copia la **Publishable key** (`sb_publishable_…`); en Data API copia la **Project URL**. Pégalas en `docs/config.js`.

## 2. Crear las tablas
1. SQL Editor → New query → pega `supabase/01_esquema.sql`.
2. Antes de ejecutar, cambia los 5 correos de administradores al final del archivo (en minúsculas). Run.
3. New query → pega `02_datos.sql` → Run. Comprueba en Table Editor → `resumenes` (121 filas).

## 3. Ingreso sin correo
Cada persona entra con su correo como usuario y como contraseña. La cuenta se crea sola en su primer ingreso, así que no hay que configurar ningún servidor de correo.

Authentication → Sign In / Providers → Email:
- **Confirm email**: apagado (si queda encendido, el primer ingreso falla).
- **Allow new users to sign up**: encendido.

Solo pueden entrar los correos que tienen resúmenes cargados o que están en la tabla `admins`; la página rechaza los demás antes de crear la cuenta.

## 4. Publicar en GitHub Pages
1. Crea un repositorio y sube esta carpeta (sin el Excel ni `02_datos.sql`).
2. Settings → Pages → Source: *Deploy from a branch* → rama `main`, carpeta `/docs`.
3. La página queda en `https://<usuario>.github.io/<repositorio>/`.

## 5. Probar
- Entra con un correo de administrador: debes ver el panel con los 121 resúmenes.
- Entra con el correo de un autor de prueba (ej. el del envío "Ensayo 1"): solo debe ver su resumen.

## Actualizar los datos
Si cambian los envíos en Oxford Abstracts, exporta de nuevo y ejecuta:
```
python herramientas/excel_a_sql.py Revision_oa_export.xlsx 02_datos.sql
```
y vuelve a correr `02_datos.sql`. Solo se actualizan los campos originales; las correcciones de los autores se conservan.

## Tareas frecuentes (SQL Editor)
- Añadir administrador: `insert into admins values ('correo@ejemplo.org');`
- Devolver un resumen a edición: desde el panel (botón **Devolver a edición**).
