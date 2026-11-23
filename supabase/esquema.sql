-- Planika · base de datos de las cuentas opcionales (Supabase).
-- Para un proyecto nuevo: pegar entero en SQL Editor → Run. Es lo mismo que las migraciones aplicadas.

-- 1. Favoritos y «Mi ciudad». Cada persona solo ve y cambia lo suyo (seguridad por fila).
create table public.favorites (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  event_id text not null check (char_length(event_id) between 1 and 64),
  created_at timestamptz not null default now(),
  primary key (user_id, event_id)
);
comment on table public.favorites is 'Planes guardados en favoritos por cada persona (id del plan de Planika).';

create table public.profiles (
  user_id uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  place text check (place is null or char_length(place) <= 120),
  updated_at timestamptz not null default now()
);
comment on table public.profiles is 'Preferencias de cada persona: su lugar («Dónde») por defecto.';

alter table public.favorites enable row level security;
alter table public.profiles enable row level security;

revoke all on table public.favorites from anon;
revoke all on table public.profiles from anon;
grant select, insert, delete on table public.favorites to authenticated;
grant select, insert, update, delete on table public.profiles to authenticated;

create policy "favoritos: ver los propios" on public.favorites
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "favoritos: añadir los propios" on public.favorites
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "favoritos: quitar los propios" on public.favorites
  for delete to authenticated using ((select auth.uid()) = user_id);

create policy "perfil: ver el propio" on public.profiles
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "perfil: crear el propio" on public.profiles
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "perfil: cambiar el propio" on public.profiles
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "perfil: borrar el propio" on public.profiles
  for delete to authenticated using ((select auth.uid()) = user_id);

-- 2. Tope de favoritos por persona (evita abusos)
create or replace function public.favorites_limit()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if (select count(*) from public.favorites where user_id = new.user_id) >= 2000 then
    raise exception 'Has llegado al máximo de 2000 favoritos';
  end if;
  return new;
end;
$$;
revoke all on function public.favorites_limit() from public, anon, authenticated;
create trigger favorites_limit before insert on public.favorites
  for each row execute function public.favorites_limit();

-- 3. «Borrar mi cuenta»: borra la cuenta de quien lo pide y, en cascada, sus favoritos y su perfil
create or replace function public.delete_my_account()
returns void language plpgsql security definer set search_path = '' as $$
begin
  if auth.uid() is null then
    raise exception 'Hace falta iniciar sesión';
  end if;
  delete from auth.users where id = auth.uid();
end;
$$;
revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

-- 4. Consulta mínima diaria (update.yml) para que el proyecto gratuito no se pause por inactividad
create or replace function public.ping()
returns timestamptz language sql stable set search_path = '' as $$ select now() $$;
revoke all on function public.ping() from public;
grant execute on function public.ping() to anon, authenticated;

-- 5. Google comparte nombre y foto; Planika solo necesita el email: se descartan al recibirlos
create or replace function public.minimizar_datos_google() returns trigger
language plpgsql set search_path = '' as $$
declare quitar text[] := array['name','full_name','avatar_url','picture','given_name','family_name','nickname','preferred_username','user_name','locale'];
begin
  if tg_table_name = 'users' then
    new.raw_user_meta_data := coalesce(new.raw_user_meta_data, '{}'::jsonb) - quitar;
  else
    new.identity_data := coalesce(new.identity_data, '{}'::jsonb) - quitar;
  end if;
  return new;
end $$;
revoke execute on function public.minimizar_datos_google() from public, anon, authenticated;
create trigger minimizar_datos_google before insert or update on auth.users
  for each row execute function public.minimizar_datos_google();
create trigger minimizar_datos_google before insert or update on auth.identities
  for each row execute function public.minimizar_datos_google();

-- 6. Quien pide el enlace por email y nunca entra deja un usuario sin confirmar: se borra a los 7 días
create extension if not exists pg_cron;
select cron.schedule(
  'planika-limpiar-sin-confirmar',
  '17 3 * * *',
  $$delete from auth.users where email_confirmed_at is null and last_sign_in_at is null and created_at < now() - interval '7 days'$$
);
