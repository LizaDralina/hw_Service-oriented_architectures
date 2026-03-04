create table products (
  id uuid primary key,
  name text not null,
  description text null,
  price numeric(19,2) not null check (price > 0),
  stock integer not null check (stock >= 0),
  category text not null,
  status text not null check (status in ('ACTIVE','INACTIVE','ARCHIVED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- индекс на status 
create index idx_products_status on products(status);

-- авто-обновление updated_at 
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_products_updated_at
before update on products
for each row
execute function set_updated_at();