-- Eventos que envían los organizadores desde «Publica tu evento» (proyecto Supabase de Planika, eu-west-1).
-- Aplicado con las migraciones «eventos_organizadores» y «organizadores_locales» (26/11/2026): la segunda añade los
-- locales abiertos todo el año (kind = lugar: escape rooms, parques de bolas…) y las categorías ocio y parques.
--
-- - La tabla tiene RLS sin políticas y sin permisos para anon: nadie puede leerla ni escribirla directamente.
-- - submit_event(p): valida y guarda un envío. Límites: 5 envíos al día por correo y 300 al día en total.
--   Si viene relleno el campo trampa «hp» (bots), responde «ok» sin guardar nada.
-- - event_submissions_pending(): lo que usa el flujo diario de GitHub Actions para proponer los envíos en un PR.
--   Devuelve solo los datos del evento (que se envían para publicarse), nunca el correo.
-- - Los envíos se borran 6 meses después (pg_cron «planika-envios-organizadores-6-meses»).

create table if not exists public.event_submissions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  email text not null check (char_length(email) <= 160),
  plan text not null check (plan in ('gratis', 'destacado', 'destacado_instagram', 'bono')),
  data jsonb not null check (octet_length(data::text) <= 8000)
);
create index if not exists event_submissions_created_idx on public.event_submissions (created_at);
create index if not exists event_submissions_email_idx on public.event_submissions (email, created_at);
alter table public.event_submissions enable row level security;
revoke all on public.event_submissions from anon, authenticated;

create or replace function public._sub_text(p jsonb, k text, maxlen integer, minlen integer default 0)
returns text language plpgsql immutable set search_path = '' as $$
declare v text;
begin
  if p ? k and jsonb_typeof(p -> k) not in ('string', 'null') then
    raise exception '% no válido', k using errcode = '22023';
  end if;
  v := btrim(regexp_replace(coalesce(p ->> k, ''), '\s+', ' ', 'g'));
  if char_length(v) > maxlen or char_length(v) < minlen then
    raise exception '% no válido', k using errcode = '22023';
  end if;
  return v;
end $$;

create or replace function public._sub_url(p jsonb, k text, required boolean)
returns text language plpgsql immutable set search_path = '' as $$
declare v text := public._sub_text(p, k, 400);
begin
  if v = '' and not required then return ''; end if;
  if v !~* '^https?://[^\s/$.?#][^\s]*$' then
    raise exception '% no válido', k using errcode = '22023';
  end if;
  return v;
end $$;

create or replace function public.submit_event(p jsonb)
returns text language plpgsql security definer set search_path = '' as $$
declare
  e text; s date; en date; t text; pc text; cat text; pl text; newid uuid; d jsonb; k text; hor text := ''; addr text;
begin
  if p is null or jsonb_typeof(p) <> 'object' or octet_length(p::text) > 12000 then
    raise exception 'datos no válidos' using errcode = '22023';
  end if;
  if coalesce(p ->> 'hp', '') <> '' then
    return 'ok';  -- campo trampa relleno: bot, se ignora en silencio
  end if;
  e := lower(public._sub_text(p, 'email', 160, 6));
  if e !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'email no válido' using errcode = '22023';
  end if;
  -- evento: con fecha; lugar: local o actividad abierta todo el año (escape room, parque de bolas…), sin fecha
  k := coalesce(nullif(public._sub_text(p, 'kind', 10), ''), 'evento');
  if k not in ('evento', 'lugar') then
    raise exception 'kind no válido' using errcode = '22023';
  end if;
  if k = 'evento' then
    begin
      s := (p ->> 'start')::date;
      en := coalesce(nullif(p ->> 'end', '')::date, s);
    exception when others then
      raise exception 'fecha no válida' using errcode = '22023';
    end;
    if s is null or s < current_date or s > current_date + 400 or en < s or en > s + 180 then
      raise exception 'fechas fuera de rango' using errcode = '22023';
    end if;
    t := public._sub_text(p, 'time', 5);
    if t <> '' and t !~ '^([01][0-9]|2[0-3]):[0-5][0-9]$' then
      raise exception 'hora no válida' using errcode = '22023';
    end if;
    addr := public._sub_text(p, 'address', 160);
  else
    t := '';
    hor := public._sub_text(p, 'horario', 200);
    addr := public._sub_text(p, 'address', 160, 5);  -- un local necesita su dirección
  end if;
  pc := public._sub_text(p, 'province_code', 2, 2);
  if pc !~ '^[0-9]{2}$' or pc::integer < 1 or pc::integer > 53 then
    raise exception 'provincia no válida' using errcode = '22023';
  end if;
  cat := public._sub_text(p, 'category', 20);
  if (cat = '' and k = 'lugar')
     or (cat <> '' and cat not in ('musica', 'escena', 'expos', 'cine', 'deporte', 'gastro', 'infantil', 'navidad',
                                   'fiestas', 'naturaleza', 'charlas', 'ocio', 'parques', 'otros')) then
    raise exception 'categoría no válida' using errcode = '22023';
  end if;
  pl := coalesce(nullif(public._sub_text(p, 'plan', 30), ''), 'gratis');
  if pl not in ('gratis', 'destacado', 'destacado_instagram', 'bono') then
    raise exception 'opción no válida' using errcode = '22023';
  end if;
  if p ? 'free' and jsonb_typeof(p -> 'free') not in ('boolean', 'null') then
    raise exception 'free no válido' using errcode = '22023';
  end if;
  d := jsonb_build_object(
    'kind', k,
    'title', public._sub_text(p, 'title', 140, 3),
    'start', s::text, 'end', en::text, 'time', t, 'horario', hor,
    'city', public._sub_text(p, 'city', 80, 2),
    'province_code', pc,
    'venue', public._sub_text(p, 'venue', 120, 2),
    'address', addr,
    'category', cat,
    'price', public._sub_text(p, 'price', 80),
    'free', coalesce((p ->> 'free')::boolean, false),
    'url', public._sub_url(p, 'url', true),
    'tickets_url', public._sub_url(p, 'tickets_url', false),
    'image', public._sub_url(p, 'image', false),
    'description', public._sub_text(p, 'description', 2000, 20),
    'organizer', public._sub_text(p, 'organizer', 120));
  if (select count(*) from public.event_submissions where email = e and created_at > now() - interval '1 day') >= 5
     or (select count(*) from public.event_submissions where created_at > now() - interval '1 day') >= 300 then
    raise exception 'demasiados envíos, prueba mañana' using errcode = 'P0001';
  end if;
  insert into public.event_submissions (email, plan, data) values (e, pl, d) returning id into newid;
  return left(newid::text, 8);
end $$;

create or replace function public.event_submissions_pending()
returns table (sub_id uuid, sent date, plan text, data jsonb)
language sql stable security definer set search_path = '' as $$
  select s.id, (s.created_at at time zone 'Europe/Madrid')::date, s.plan, s.data
  from public.event_submissions s
  where s.created_at > now() - interval '45 days'
  order by s.created_at
$$;

revoke all on function public._sub_text(jsonb, text, integer, integer) from public, anon, authenticated;
revoke all on function public._sub_url(jsonb, text, boolean) from public, anon, authenticated;
revoke all on function public.submit_event(jsonb) from public;
revoke all on function public.event_submissions_pending() from public;
grant execute on function public.submit_event(jsonb) to anon, authenticated;
grant execute on function public.event_submissions_pending() to anon, authenticated;

select cron.schedule('planika-envios-organizadores-6-meses', '41 3 * * *',
  $$delete from public.event_submissions where created_at < now() - interval '6 months'$$);
