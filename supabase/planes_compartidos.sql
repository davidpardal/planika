-- Planes compartidos en vivo de «Mis planes» (proyecto Supabase de Planika, región eu-west-1).
-- Aplicado con las migraciones «planes_compartidos_en_vivo» y «planes_compartidos_id_del_movil» (25/11/2026).
--
-- Sin cuentas: quien tiene el enlace (?plan=<id>, 16 bytes aleatorios generados en el móvil) ve y edita el plan.
-- La tabla tiene RLS sin políticas y sin permisos para anon: no se puede listar ni leer directamente; solo con las
-- funciones shared_plan_* (SECURITY DEFINER), que exigen conocer el id. Las alertas del linter de Supabase sobre
-- funciones SECURITY DEFINER ejecutables por anon son, por tanto, intencionadas.
-- Se borran 6 meses después del último cambio (pg_cron «planika-planes-compartidos-6-meses»).

create table if not exists public.shared_plans (
  id text primary key check (id ~ '^[A-Za-z0-9_-]{22}$'),
  plan jsonb not null check (octet_length(plan::text) <= 16000),
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists shared_plans_updated_at_idx on public.shared_plans (updated_at);
alter table public.shared_plans enable row level security;
revoke all on public.shared_plans from anon, authenticated;

create or replace function public._shared_plan_valid(p jsonb) returns boolean
language sql immutable set search_path = '' as $$
  select jsonb_typeof(p) = 'object'
    and octet_length(p::text) <= 16000
    and jsonb_typeof(coalesce(p->'n', '""'::jsonb)) = 'string' and char_length(coalesce(p->>'n', '')) <= 60
    and jsonb_typeof(coalesce(p->'i', '[]'::jsonb)) = 'array' and jsonb_array_length(coalesce(p->'i', '[]'::jsonb)) <= 40
    and jsonb_typeof(coalesce(p->'o', '[]'::jsonb)) = 'array' and jsonb_array_length(coalesce(p->'o', '[]'::jsonb)) <= 20
$$;

create or replace function public._shared_plan_clean(p jsonb) returns jsonb
language sql immutable set search_path = '' as $$
  select jsonb_build_object('n', coalesce(p->'n', '""'::jsonb), 'i', coalesce(p->'i', '[]'::jsonb), 'o', coalesce(p->'o', '[]'::jsonb))
$$;

create or replace function public.shared_plan_create(p_id text, p_plan jsonb)
returns table (plan_version integer, plan_updated timestamptz)
language plpgsql security definer set search_path = '' as $$
begin
  if p_id is null or p_id !~ '^[A-Za-z0-9_-]{22}$' then raise exception 'id no válido' using errcode = '22023'; end if;
  if not public._shared_plan_valid(p_plan) then raise exception 'plan no válido' using errcode = '22023'; end if;
  insert into public.shared_plans (id, plan) values (p_id, public._shared_plan_clean(p_plan));
  return query select s.version, s.updated_at from public.shared_plans s where s.id = p_id;
exception when unique_violation then
  raise exception 'id en uso' using errcode = '23505';
end $$;

create or replace function public.shared_plan_get(p_ids text[])
returns table (plan_id text, plan jsonb, plan_version integer, plan_updated timestamptz)
language sql stable security definer set search_path = '' as $$
  select s.id, s.plan, s.version, s.updated_at from public.shared_plans s where s.id = any (p_ids[1:20])
$$;

create or replace function public.shared_plan_save(p_id text, p_plan jsonb)
returns table (plan_version integer, plan_updated timestamptz)
language plpgsql security definer set search_path = '' as $$
begin
  if not public._shared_plan_valid(p_plan) then raise exception 'plan no válido' using errcode = '22023'; end if;
  return query
    update public.shared_plans s
       set plan = public._shared_plan_clean(p_plan), version = s.version + 1, updated_at = now()
     where s.id = p_id
     returning s.version, s.updated_at;
end $$;

create or replace function public.shared_plan_ping()
returns integer language sql stable security definer set search_path = '' as $$
  select count(*)::integer from public.shared_plans
$$;

revoke all on function public._shared_plan_valid(jsonb) from public, anon, authenticated;
revoke all on function public._shared_plan_clean(jsonb) from public, anon, authenticated;
revoke all on function public.shared_plan_create(text, jsonb) from public;
revoke all on function public.shared_plan_get(text[]) from public;
revoke all on function public.shared_plan_save(text, jsonb) from public;
revoke all on function public.shared_plan_ping() from public;
grant execute on function public.shared_plan_create(text, jsonb) to anon, authenticated;
grant execute on function public.shared_plan_get(text[]) to anon, authenticated;
grant execute on function public.shared_plan_save(text, jsonb) to anon, authenticated;
grant execute on function public.shared_plan_ping() to anon, authenticated;

select cron.schedule('planika-planes-compartidos-6-meses', '27 3 * * *',
  $$delete from public.shared_plans where updated_at < now() - interval '6 months'$$);
