-- =====================================================================
-- Plataforma de corrección de resúmenes — 3er Congreso Colombiano de
-- Bioacústica y Ecoacústica
-- Pegar completo en Supabase > SQL Editor > Run (una sola vez).
-- =====================================================================

-- ---------- Tablas ----------
create table if not exists public.admins (
  email text primary key check (email = lower(email))
);

create table if not exists public.resumenes (
  id                bigint primary key,          -- Submission Id de Oxford Abstracts
  correo            text not null,               -- correo del remitente (en minúsculas)
  nombre_remitente  text,
  simposio          text,
  decision          text,
  titulo_original   text,
  autores_original  text,
  presentador       text,
  resumen_original  text,
  revisiones        jsonb not null default '[]'::jsonb,
  -- Versión que editan los autores (arranca igual a la original)
  titulo            text,
  autores           text,
  resumen           text,
  estado            text not null default 'pendiente'
                    check (estado in ('pendiente', 'borrador', 'listo')),
  actualizado       timestamptz,
  listo_en          timestamptz,
  editado_por       text
);

create index if not exists resumenes_correo_idx on public.resumenes (correo);

-- ---------- Funciones auxiliares ----------
create or replace function public.correo_actual()
returns text language sql stable as $$
  select lower(coalesce(auth.jwt() ->> 'email', ''));
$$;

create or replace function public.es_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where email = public.correo_actual());
$$;

-- Permite a la pantalla de ingreso saber si el correo puede entrar,
-- sin revelar ningún dato del resumen.
create or replace function public.puede_ingresar(p_correo text)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.resumenes where correo = lower(trim(p_correo)))
      or exists (select 1 from public.admins    where email  = lower(trim(p_correo)));
$$;

-- ---------- Reglas al actualizar ----------
create or replace function public.antes_de_actualizar()
returns trigger language plpgsql security definer set search_path = public as $$
declare
  es_usuario boolean := coalesce(auth.jwt() ->> 'role', '') = 'authenticated';
begin
  if es_usuario and not public.es_admin() then
    if old.estado = 'listo' then
      raise exception 'Este resumen ya fue entregado. Si necesitas cambiarlo, escribe al comité organizador.';
    end if;
    if new.estado not in ('borrador', 'listo') then
      raise exception 'Estado no permitido.';
    end if;
    if new.estado = 'listo' and length(trim(coalesce(new.resumen, ''))) = 0 then
      raise exception 'El resumen no puede quedar vacío.';
    end if;
  end if;

  if (new.titulo, new.autores, new.resumen, new.estado)
     is distinct from (old.titulo, old.autores, old.resumen, old.estado) then
    new.actualizado := now();
    if es_usuario then
      new.editado_por := public.correo_actual();
    end if;
  end if;

  if new.estado = 'listo' and old.estado <> 'listo' then
    new.listo_en := now();
  elsif new.estado <> 'listo' then
    new.listo_en := null;
  end if;

  return new;
end;
$$;

drop trigger if exists resumenes_antes_de_actualizar on public.resumenes;
create trigger resumenes_antes_de_actualizar
  before update on public.resumenes
  for each row execute function public.antes_de_actualizar();

-- ---------- Seguridad (Row Level Security) ----------
alter table public.resumenes enable row level security;
alter table public.admins    enable row level security;

drop policy if exists "leer propios o admin"      on public.resumenes;
drop policy if exists "editar propios o admin"    on public.resumenes;

create policy "leer propios o admin" on public.resumenes
  for select to authenticated
  using (correo = public.correo_actual() or public.es_admin());

create policy "editar propios o admin" on public.resumenes
  for update to authenticated
  using (correo = public.correo_actual() or public.es_admin())
  with check (correo = public.correo_actual() or public.es_admin());

-- Nadie inserta ni borra desde la página; solo se editan cuatro columnas.
revoke all on public.resumenes from anon, authenticated;
revoke all on public.admins    from anon, authenticated;
grant select on public.resumenes to authenticated;
grant update (titulo, autores, resumen, estado) on public.resumenes to authenticated;

revoke all on function public.es_admin()            from public, anon;
revoke all on function public.puede_ingresar(text)  from public;
grant execute on function public.es_admin()           to authenticated;
grant execute on function public.puede_ingresar(text) to anon, authenticated;

-- ---------- Los 5 administradores ----------
-- Reemplaza por los correos reales (en minúsculas) y ejecuta.
insert into public.admins (email) values
  ('admin1@ejemplo.org'),
  ('admin2@ejemplo.org'),
  ('admin3@ejemplo.org'),
  ('admin4@ejemplo.org'),
  ('admin5@ejemplo.org')
on conflict do nothing;
