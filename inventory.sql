\set ON_ERROR_STOP on
BEGIN;
CREATE TABLE recovery_marker (
    run_id text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE products (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku text NOT NULL UNIQUE,
    quantity integer NOT NULL CHECK (quantity >= 0),
    price numeric(10,2) NOT NULL CHECK (price >= 0),
    note text
);
CREATE TABLE movements (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id bigint NOT NULL REFERENCES products(id),
    delta integer NOT NULL
);
COMMIT;
