DROP TABLE IF EXISTS delivery_status_history CASCADE;
DROP TABLE IF EXISTS delivery_courier_assignments CASCADE;
DROP TABLE IF EXISTS deliveries CASCADE;
DROP TABLE IF EXISTS delivery_statuses CASCADE;
DROP TABLE IF EXISTS couriers CASCADE;
DROP TABLE IF EXISTS employees CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS persons CASCADE;
DROP TABLE IF EXISTS city_delivery_tariffs CASCADE;
DROP TABLE IF EXISTS branches CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS users_account CASCADE;

CREATE TABLE users_account (
    user_id SERIAL PRIMARY KEY,
    login VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_users_account_role CHECK (role IN ('client', 'employee', 'courier', 'admin'))
);

CREATE TABLE addresses (
    address_id SERIAL PRIMARY KEY,
    city VARCHAR(100) NOT NULL,
    street VARCHAR(100) NOT NULL,
    house VARCHAR(20) NOT NULL,
    apartment VARCHAR(20),
    postal_code VARCHAR(20),
    comment VARCHAR(255)
);

CREATE TABLE branches (
    branch_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    address_id INTEGER NOT NULL UNIQUE,
    CONSTRAINT fk_branches_address FOREIGN KEY (address_id) REFERENCES addresses(address_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE city_delivery_tariffs (
    tariff_id SERIAL PRIMARY KEY,
    origin_city VARCHAR(100) NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    distance_km NUMERIC(8,2) NOT NULL,
    CONSTRAINT chk_city_tariffs_cities_different CHECK (origin_city <> destination_city),
    CONSTRAINT chk_city_tariffs_distance CHECK (distance_km > 0),
    CONSTRAINT uq_city_tariffs_route UNIQUE (origin_city, destination_city)
);

CREATE TABLE persons (
    person_id SERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20) UNIQUE,
    email VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clients (
    client_id SERIAL PRIMARY KEY,
    person_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER UNIQUE,
    client_status VARCHAR(20) NOT NULL DEFAULT 'active',
    registered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_clients_person FOREIGN KEY (person_id) REFERENCES persons(person_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_clients_user FOREIGN KEY (user_id) REFERENCES users_account(user_id) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_clients_status CHECK (client_status IN ('active', 'inactive'))
);

CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    person_id INTEGER NOT NULL UNIQUE,
    branch_id INTEGER NOT NULL,
    employee_role VARCHAR(20) NOT NULL,
    hired_at DATE NOT NULL DEFAULT CURRENT_DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_employees_user FOREIGN KEY (user_id) REFERENCES users_account(user_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_employees_person FOREIGN KEY (person_id) REFERENCES persons(person_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_employees_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_employees_role CHECK (employee_role IN ('admin', 'operator', 'courier')),
    CONSTRAINT chk_employees_hired_at CHECK (hired_at <= CURRENT_DATE)
);

CREATE TABLE couriers (
    employee_id INTEGER PRIMARY KEY,
    transport_type VARCHAR(50) NOT NULL,
    capacity_kg NUMERIC(8,2) NOT NULL,
    CONSTRAINT fk_couriers_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_couriers_capacity CHECK (capacity_kg > 0),
    CONSTRAINT chk_couriers_transport_type CHECK (transport_type IN ('foot', 'bicycle', 'motorcycle', 'car', 'truck'))
);

CREATE TABLE delivery_statuses (
    status_id SERIAL PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    sort_order INTEGER NOT NULL,
    CONSTRAINT chk_delivery_statuses_sort_order CHECK (sort_order > 0)
);

CREATE TABLE deliveries (
    delivery_id SERIAL PRIMARY KEY,
    tracking_number VARCHAR(30) NOT NULL UNIQUE,
    sender_client_id INTEGER NOT NULL,
    recipient_client_id INTEGER NOT NULL,
    origin_branch_id INTEGER NOT NULL,
    destination_branch_id INTEGER NOT NULL,
    sender_address_id INTEGER NOT NULL,
    recipient_address_id INTEGER NOT NULL,
    created_by_employee_id INTEGER NOT NULL,
    current_status_id INTEGER NOT NULL,
    declared_weight_kg NUMERIC(8,2) NOT NULL,
    declared_value NUMERIC(10,2) NOT NULL DEFAULT 0,
    description VARCHAR(255),
    base_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    extra_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP,
    CONSTRAINT fk_deliveries_sender_client FOREIGN KEY (sender_client_id) REFERENCES clients(client_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_recipient_client FOREIGN KEY (recipient_client_id) REFERENCES clients(client_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_origin_branch FOREIGN KEY (origin_branch_id) REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_destination_branch FOREIGN KEY (destination_branch_id) REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_sender_address FOREIGN KEY (sender_address_id) REFERENCES addresses(address_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_recipient_address FOREIGN KEY (recipient_address_id) REFERENCES addresses(address_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_created_by_employee FOREIGN KEY (created_by_employee_id) REFERENCES employees(employee_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_deliveries_current_status FOREIGN KEY (current_status_id) REFERENCES delivery_statuses(status_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_deliveries_weight CHECK (declared_weight_kg > 0),
    CONSTRAINT chk_deliveries_declared_value CHECK (declared_value >= 0),
    CONSTRAINT chk_deliveries_costs CHECK (base_cost >= 0 AND extra_cost >= 0 AND total_cost >= 0),
    CONSTRAINT chk_deliveries_total_cost CHECK (total_cost = base_cost + extra_cost),
    CONSTRAINT chk_deliveries_delivered_at CHECK (delivered_at IS NULL OR delivered_at >= created_at)
);

CREATE TABLE delivery_courier_assignments (
    assignment_id SERIAL PRIMARY KEY,
    delivery_id INTEGER NOT NULL,
    courier_id INTEGER,
    client_id INTEGER NOT NULL,
    service_type VARCHAR(20) NOT NULL,
    call_address_id INTEGER NOT NULL,
    service_cost NUMERIC(10,2) NOT NULL DEFAULT 0,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    CONSTRAINT fk_assignments_delivery FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_courier FOREIGN KEY (courier_id) REFERENCES couriers(employee_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_client FOREIGN KEY (client_id) REFERENCES clients(client_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_call_address FOREIGN KEY (call_address_id) REFERENCES addresses(address_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_assignments_service_type CHECK (service_type IN ('pickup', 'delivery', 'return', 'redelivery', 'express')),
    CONSTRAINT chk_assignments_service_cost CHECK (service_cost >= 0),
    CONSTRAINT chk_assignments_completed_at CHECK (completed_at IS NULL OR completed_at >= assigned_at)
);

CREATE TABLE delivery_status_history (
    history_id SERIAL PRIMARY KEY,
    delivery_id INTEGER NOT NULL,
    old_status_id INTEGER,
    new_status_id INTEGER NOT NULL,
    changed_by_employee_id INTEGER,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    comment VARCHAR(255),
    CONSTRAINT fk_status_history_delivery FOREIGN KEY (delivery_id) REFERENCES deliveries(delivery_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_status_history_old_status FOREIGN KEY (old_status_id) REFERENCES delivery_statuses(status_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_status_history_new_status FOREIGN KEY (new_status_id) REFERENCES delivery_statuses(status_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_status_history_employee FOREIGN KEY (changed_by_employee_id) REFERENCES employees(employee_id) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_status_history_status_change CHECK (old_status_id IS NULL OR old_status_id <> new_status_id)
);

CREATE UNIQUE INDEX ux_delivery_courier_assignments_delivery_service_type ON delivery_courier_assignments(delivery_id, service_type);

CREATE OR REPLACE FUNCTION calculate_delivery_cost(
    p_origin_branch_id INTEGER,
    p_destination_branch_id INTEGER,
    p_weight NUMERIC,
    p_declared_value NUMERIC
)
RETURNS TABLE(base_cost NUMERIC(10,2), extra_cost NUMERIC(10,2), total_cost NUMERIC(10,2))
LANGUAGE plpgsql
AS $$
DECLARE
    v_origin_city VARCHAR(100);
    v_destination_city VARCHAR(100);
    v_distance_km NUMERIC(8,2);
BEGIN
    SELECT addresses.city
    INTO v_origin_city
    FROM branches
    JOIN addresses ON addresses.address_id = branches.address_id
    WHERE branches.branch_id = p_origin_branch_id;

    SELECT addresses.city
    INTO v_destination_city
    FROM branches
    JOIN addresses ON addresses.address_id = branches.address_id
    WHERE branches.branch_id = p_destination_branch_id;

    IF v_origin_city IS NULL OR v_destination_city IS NULL THEN
        RAISE EXCEPTION 'Branch route % -> % is not found', p_origin_branch_id, p_destination_branch_id;
    END IF;

    IF v_origin_city = v_destination_city THEN
        base_cost := 300.00;
    ELSE
        SELECT distance_km
        INTO v_distance_km
        FROM city_delivery_tariffs
        WHERE (origin_city = v_origin_city AND destination_city = v_destination_city)
           OR (origin_city = v_destination_city AND destination_city = v_origin_city)
        LIMIT 1;

        IF v_distance_km IS NULL THEN
            RAISE EXCEPTION 'Tariff route % -> % is not found', v_origin_city, v_destination_city;
        END IF;

        base_cost := ROUND((350 + v_distance_km * 4 + p_weight * 55)::NUMERIC, 2);
    END IF;

    extra_cost := ROUND((p_declared_value * 0.01)::NUMERIC, 2);
    total_cost := base_cost + extra_cost;
    RETURN NEXT;
END;
$$;

CREATE OR REPLACE FUNCTION set_delivery_costs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_cost RECORD;
BEGIN
    SELECT * INTO v_cost
    FROM calculate_delivery_cost(
        NEW.origin_branch_id,
        NEW.destination_branch_id,
        NEW.declared_weight_kg,
        NEW.declared_value
    );

    NEW.base_cost := v_cost.base_cost;
    NEW.extra_cost := v_cost.extra_cost;
    NEW.total_cost := v_cost.total_cost;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION set_delivery_timestamp()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_status_code VARCHAR(30);
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.current_status_id IS DISTINCT FROM OLD.current_status_id THEN
        SELECT code INTO v_status_code
        FROM delivery_statuses
        WHERE status_id = NEW.current_status_id;

        IF v_status_code = 'DELIVERED' AND NEW.delivered_at IS NULL THEN
            NEW.delivered_at := CURRENT_TIMESTAMP;
        ELSIF v_status_code <> 'DELIVERED' THEN
            NEW.delivered_at := NULL;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION write_delivery_status_history()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_id INTEGER;
    v_comment VARCHAR(255);
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO delivery_status_history (
            delivery_id,
            old_status_id,
            new_status_id,
            changed_by_employee_id,
            comment
        )
        VALUES (
            NEW.delivery_id,
            NULL,
            NEW.current_status_id,
            NEW.created_by_employee_id,
            COALESCE(NULLIF(current_setting('app.status_comment', true), ''), 'Доставка создана')
        );
        RETURN NEW;
    END IF;

    IF NEW.current_status_id IS DISTINCT FROM OLD.current_status_id THEN
        v_employee_id := NULLIF(current_setting('app.changed_by_employee_id', true), '')::INTEGER;
        v_comment := NULLIF(current_setting('app.status_comment', true), '');

        INSERT INTO delivery_status_history (
            delivery_id,
            old_status_id,
            new_status_id,
            changed_by_employee_id,
            comment
        )
        VALUES (
            NEW.delivery_id,
            OLD.current_status_id,
            NEW.current_status_id,
            COALESCE(v_employee_id, NEW.created_by_employee_id),
            v_comment
        );
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION validate_courier()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_employee_role VARCHAR(20);
    v_is_active BOOLEAN;
BEGIN
    SELECT employee_role, is_active
    INTO v_employee_role, v_is_active
    FROM employees
    WHERE employee_id = NEW.employee_id;

    IF v_employee_role <> 'courier' THEN
        RAISE EXCEPTION 'Employee % is not a courier', NEW.employee_id;
    END IF;

    IF NOT v_is_active THEN
        RAISE EXCEPTION 'Employee % is inactive', NEW.employee_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION validate_courier_assignment()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_is_active BOOLEAN;
BEGIN
    IF NEW.courier_id IS NOT NULL THEN
        SELECT employees.is_active
        INTO v_is_active
        FROM couriers
        JOIN employees ON employees.employee_id = couriers.employee_id
        WHERE couriers.employee_id = NEW.courier_id;

        IF NOT COALESCE(v_is_active, FALSE) THEN
            RAISE EXCEPTION 'Courier % is inactive or not found', NEW.courier_id;
        END IF;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = NEW.delivery_id
          AND service_type = NEW.service_type
          AND assignment_id <> COALESCE(NEW.assignment_id, -1)
    ) THEN
        RAISE EXCEPTION 'Delivery % already has a courier assignment for service type %', NEW.delivery_id, NEW.service_type;
    END IF;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE PROCEDURE change_delivery_status(
    p_delivery_id INTEGER,
    p_new_status_id INTEGER,
    p_changed_by_employee_id INTEGER,
    p_comment VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_current_status_id INTEGER;
    v_current_code VARCHAR(30);
    v_new_code VARCHAR(30);
    v_has_courier_requests BOOLEAN;
    v_has_open_courier_requests BOOLEAN;
    v_has_pickup_requests BOOLEAN;
    v_has_open_pickup_requests BOOLEAN;
    v_has_delivery_requests BOOLEAN;
    v_has_open_delivery_requests BOOLEAN;
    v_same_branch_route BOOLEAN;
    v_origin_branch_id INTEGER;
    v_destination_branch_id INTEGER;
    v_employee_role VARCHAR(20);
    v_employee_branch_id INTEGER;
BEGIN
    SELECT current_status_id
    INTO v_current_status_id
    FROM deliveries
    WHERE delivery_id = p_delivery_id;

    IF v_current_status_id IS NULL THEN
        RAISE EXCEPTION 'Delivery % does not exist', p_delivery_id;
    END IF;

    SELECT code
    INTO v_current_code
    FROM delivery_statuses
    WHERE status_id = v_current_status_id;

    SELECT code
    INTO v_new_code
    FROM delivery_statuses
    WHERE status_id = p_new_status_id;

    IF v_new_code IS NULL THEN
        RAISE EXCEPTION 'Status % does not exist', p_new_status_id;
    END IF;

    IF v_current_status_id = p_new_status_id THEN
        RAISE EXCEPTION 'Delivery % already has status %', p_delivery_id, v_new_code;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
    )
    INTO v_has_courier_requests;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND courier_id IS NULL
    )
    INTO v_has_open_courier_requests;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND service_type = 'pickup'
    )
    INTO v_has_pickup_requests;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND service_type = 'pickup'
          AND courier_id IS NULL
    )
    INTO v_has_open_pickup_requests;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND service_type = 'delivery'
    )
    INTO v_has_delivery_requests;

    SELECT EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND service_type = 'delivery'
          AND courier_id IS NULL
    )
    INTO v_has_open_delivery_requests;

    SELECT origin_branch_id, destination_branch_id, origin_branch_id = destination_branch_id
    INTO v_origin_branch_id, v_destination_branch_id, v_same_branch_route
    FROM deliveries
    WHERE delivery_id = p_delivery_id;

    IF NOT (
        (v_current_code = 'CREATED' AND v_new_code IN ('REGISTERED', 'CANCELLED'))
        OR (v_current_code = 'REGISTERED' AND v_new_code = 'WAITING_COURIER' AND v_has_pickup_requests)
        OR (v_current_code = 'REGISTERED' AND v_new_code = 'AT_ORIGIN_BRANCH' AND NOT v_has_pickup_requests)
        OR (v_current_code = 'REGISTERED' AND v_new_code = 'CANCELLED')
        OR (v_current_code = 'WAITING_COURIER' AND v_new_code = 'COURIER_ASSIGNED' AND v_has_pickup_requests AND NOT v_has_open_pickup_requests)
        OR (v_current_code = 'WAITING_COURIER' AND v_new_code = 'CANCELLED')
        OR (v_current_code = 'COURIER_ASSIGNED' AND v_new_code IN ('COURIER_PICKED_UP', 'CANCELLED'))
        OR (v_current_code = 'COURIER_PICKED_UP' AND v_new_code IN ('AT_ORIGIN_BRANCH', 'CANCELLED'))
        OR (v_current_code = 'AT_ORIGIN_BRANCH' AND v_new_code = 'IN_TRANSIT' AND NOT v_same_branch_route)
        OR (v_current_code = 'AT_ORIGIN_BRANCH' AND v_new_code = 'AT_DESTINATION_BRANCH' AND v_same_branch_route)
        OR (v_current_code = 'AT_ORIGIN_BRANCH' AND v_new_code = 'CANCELLED')
        OR (v_current_code = 'IN_TRANSIT' AND v_new_code IN ('AT_DESTINATION_BRANCH', 'CANCELLED'))
        OR (v_current_code = 'AT_DESTINATION_BRANCH' AND v_new_code = 'COURIER_DELIVERING_RECIPIENT' AND v_has_delivery_requests AND NOT v_has_open_delivery_requests)
        OR (v_current_code = 'AT_DESTINATION_BRANCH' AND v_new_code = 'DELIVERED' AND NOT v_has_delivery_requests)
        OR (v_current_code = 'AT_DESTINATION_BRANCH' AND v_new_code = 'CANCELLED')
        OR (v_current_code = 'COURIER_DELIVERING_RECIPIENT' AND v_new_code IN ('COURIER_DELIVERED', 'CANCELLED'))
        OR (v_current_code = 'COURIER_DELIVERED' AND v_new_code IN ('DELIVERED', 'CANCELLED'))
    ) THEN
        RAISE EXCEPTION 'Invalid delivery status transition: % -> %', v_current_code, v_new_code;
    END IF;

    IF p_changed_by_employee_id IS NOT NULL THEN
        SELECT employee_role, branch_id
        INTO v_employee_role, v_employee_branch_id
        FROM employees
        WHERE employee_id = p_changed_by_employee_id;

        IF v_employee_role = 'operator'
           AND (
               (v_new_code = 'AT_ORIGIN_BRANCH' AND v_employee_branch_id <> v_origin_branch_id)
               OR (v_new_code = 'AT_DESTINATION_BRANCH' AND v_employee_branch_id <> v_destination_branch_id)
           ) THEN
            RAISE EXCEPTION 'Operator can confirm parcel acceptance only in own branch';
        END IF;
    END IF;

    PERFORM set_config('app.changed_by_employee_id', COALESCE(p_changed_by_employee_id::TEXT, ''), true);
    PERFORM set_config('app.status_comment', COALESCE(p_comment, ''), true);

    UPDATE deliveries
    SET current_status_id = p_new_status_id
    WHERE delivery_id = p_delivery_id;
END;
$$;

CREATE OR REPLACE PROCEDURE assign_courier_to_delivery(
    p_delivery_id INTEGER,
    p_courier_id INTEGER,
    p_client_id INTEGER,
    p_service_type VARCHAR,
    p_call_address_id INTEGER,
    p_service_cost NUMERIC,
    p_changed_by_employee_id INTEGER,
    p_comment VARCHAR DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_assigned_status_id INTEGER;
    v_current_status_code VARCHAR(30);
BEGIN
    SELECT status_id
    INTO v_assigned_status_id
    FROM delivery_statuses
    WHERE code = 'COURIER_ASSIGNED';

    SELECT delivery_statuses.code
    INTO v_current_status_code
    FROM deliveries
    JOIN delivery_statuses ON delivery_statuses.status_id = deliveries.current_status_id
    WHERE deliveries.delivery_id = p_delivery_id;

    IF v_assigned_status_id IS NULL THEN
        RAISE EXCEPTION 'Status COURIER_ASSIGNED does not exist';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM delivery_courier_assignments
        WHERE delivery_id = p_delivery_id
          AND service_type = p_service_type
          AND courier_id IS NULL
    ) THEN
        UPDATE delivery_courier_assignments
        SET courier_id = p_courier_id,
            client_id = p_client_id,
            call_address_id = p_call_address_id,
            service_cost = p_service_cost,
            assigned_at = CURRENT_TIMESTAMP
        WHERE delivery_id = p_delivery_id
          AND service_type = p_service_type
          AND courier_id IS NULL;
    ELSE
        INSERT INTO delivery_courier_assignments (
            delivery_id,
            courier_id,
            client_id,
            service_type,
            call_address_id,
            service_cost
        )
        VALUES (
            p_delivery_id,
            p_courier_id,
            p_client_id,
            p_service_type,
            p_call_address_id,
            p_service_cost
        );
    END IF;

    IF p_service_type = 'pickup' AND v_current_status_code = 'WAITING_COURIER' THEN
        CALL change_delivery_status(
            p_delivery_id,
            v_assigned_status_id,
            p_changed_by_employee_id,
            COALESCE(p_comment, 'Назначен курьер #' || p_courier_id)
        );
    END IF;
END;
$$;

CREATE TRIGGER trg_deliveries_set_costs
BEFORE INSERT OR UPDATE OF origin_branch_id, destination_branch_id, declared_weight_kg, declared_value
ON deliveries
FOR EACH ROW
EXECUTE FUNCTION set_delivery_costs();

CREATE TRIGGER trg_deliveries_set_timestamp
BEFORE UPDATE OF current_status_id
ON deliveries
FOR EACH ROW
EXECUTE FUNCTION set_delivery_timestamp();

CREATE TRIGGER trg_deliveries_write_status_history
AFTER INSERT OR UPDATE OF current_status_id
ON deliveries
FOR EACH ROW
EXECUTE FUNCTION write_delivery_status_history();

CREATE TRIGGER trg_couriers_validate
BEFORE INSERT OR UPDATE
ON couriers
FOR EACH ROW
EXECUTE FUNCTION validate_courier();

CREATE TRIGGER trg_assignments_validate
BEFORE INSERT OR UPDATE
ON delivery_courier_assignments
FOR EACH ROW
EXECUTE FUNCTION validate_courier_assignment();

INSERT INTO addresses (address_id, city, street, house, apartment, postal_code, comment) VALUES
(1, 'Москва', 'Тверская', '1', NULL, '125009', 'Центральный офис'),
(2, 'Санкт-Петербург', 'Невский проспект', '12', NULL, '191025', 'Северо-западный филиал'),
(3, 'Казань', 'Баумана', '24', NULL, '420111', 'Поволжский филиал'),
(4, 'Екатеринбург', 'Ленина', '10', NULL, '620014', 'Уральский филиал'),
(5, 'Нижний Новгород', 'Большая Покровская', '7', NULL, '603005', 'Нижегородский филиал'),
(6, 'Самара', 'Молодогвардейская', '3', NULL, '443099', 'Самарский филиал'),
(7, 'Пермь', 'Комсомольский проспект', '6', NULL, '614000', 'Пермский филиал'),
(8, 'Красноярск', 'Мира', '18', NULL, '660049', 'Красноярский филиал'),
(9, 'Омск', 'Ленина', '9', NULL, '644024', 'Омский филиал'),
(10, 'Томск', 'Ленина', '11', NULL, '634050', 'Томский филиал'),
(11, 'Москва', 'Арбат', '22', '15', '119002', 'Адрес клиента в Москве'),
(12, 'Санкт-Петербург', 'Литейный проспект', '44', '8', '191014', 'Адрес клиента в Санкт-Петербурге'),
(13, 'Казань', 'Пушкина', '9', '21', '420015', 'Адрес клиента в Казани'),
(14, 'Екатеринбург', 'Малышева', '51', '34', '620075', 'Адрес клиента в Екатеринбурге'),
(15, 'Нижний Новгород', 'Ильинская', '18', '7', '603109', 'Адрес клиента в Нижнем Новгороде'),
(16, 'Самара', 'Ленинградская', '42', '5', '443099', 'Адрес клиента в Самаре'),
(17, 'Пермь', 'Ленина', '30', '16', '614000', 'Адрес клиента в Перми'),
(18, 'Красноярск', 'Карла Маркса', '95', '11', '660017', 'Адрес клиента в Красноярске'),
(19, 'Омск', 'Гагарина', '14', '22', '644099', 'Адрес клиента в Омске'),
(20, 'Томск', 'Советская', '36', '3', '634034', 'Адрес клиента в Томске');

SELECT setval('addresses_address_id_seq', 20, true);

INSERT INTO branches (branch_id, name, address_id) VALUES
(1, 'Центральный филиал', 1),
(2, 'Левобережный филиал', 2),
(3, 'Казанский филиал', 3),
(4, 'Уральский филиал', 4),
(5, 'Нижегородский филиал', 5),
(6, 'Самарский филиал', 6),
(7, 'Пермский филиал', 7),
(8, 'Красноярский филиал', 8),
(9, 'Омский филиал', 9),
(10, 'Томский филиал', 10);

SELECT setval('branches_branch_id_seq', 10, true);

INSERT INTO city_delivery_tariffs (tariff_id, origin_city, destination_city, distance_km) VALUES
(1, 'Москва', 'Санкт-Петербург', 635.00),
(2, 'Москва', 'Казань', 820.00),
(3, 'Санкт-Петербург', 'Казань', 1510.00),
(4, 'Москва', 'Екатеринбург', 1790.00),
(5, 'Санкт-Петербург', 'Нижний Новгород', 1120.00),
(6, 'Казань', 'Пермь', 590.00),
(7, 'Москва', 'Самара', 1050.00),
(8, 'Санкт-Петербург', 'Красноярск', 4120.00),
(9, 'Казань', 'Омск', 1750.00),
(10, 'Москва', 'Томск', 3600.00),
(11, 'Москва', 'Нижний Новгород', 420.00),
(12, 'Москва', 'Пермь', 1440.00),
(13, 'Москва', 'Красноярск', 4140.00),
(14, 'Москва', 'Омск', 2700.00),
(15, 'Санкт-Петербург', 'Екатеринбург', 2280.00),
(16, 'Санкт-Петербург', 'Самара', 1760.00),
(17, 'Санкт-Петербург', 'Пермь', 2100.00),
(18, 'Санкт-Петербург', 'Омск', 3260.00),
(19, 'Санкт-Петербург', 'Томск', 4040.00),
(20, 'Казань', 'Екатеринбург', 950.00),
(21, 'Казань', 'Нижний Новгород', 390.00),
(22, 'Казань', 'Самара', 360.00),
(23, 'Казань', 'Красноярск', 3300.00),
(24, 'Казань', 'Томск', 2860.00),
(25, 'Екатеринбург', 'Нижний Новгород', 1280.00),
(26, 'Екатеринбург', 'Самара', 960.00),
(27, 'Екатеринбург', 'Пермь', 360.00),
(28, 'Екатеринбург', 'Красноярск', 2400.00),
(29, 'Екатеринбург', 'Омск', 940.00),
(30, 'Екатеринбург', 'Томск', 1500.00),
(31, 'Нижний Новгород', 'Самара', 670.00),
(32, 'Нижний Новгород', 'Пермь', 1060.00),
(33, 'Нижний Новгород', 'Красноярск', 3760.00),
(34, 'Нижний Новгород', 'Омск', 2340.00),
(35, 'Нижний Новгород', 'Томск', 3200.00),
(36, 'Самара', 'Пермь', 800.00),
(37, 'Самара', 'Красноярск', 3020.00),
(38, 'Самара', 'Омск', 1720.00),
(39, 'Самара', 'Томск', 2480.00),
(40, 'Пермь', 'Красноярск', 2620.00),
(41, 'Пермь', 'Омск', 1450.00),
(42, 'Пермь', 'Томск', 2020.00),
(43, 'Красноярск', 'Омск', 1420.00),
(44, 'Красноярск', 'Томск', 560.00),
(45, 'Омск', 'Томск', 900.00);

SELECT setval('city_delivery_tariffs_tariff_id_seq', 45, true);

INSERT INTO users_account (user_id, login, password_hash, role) VALUES
(1, 'admin', '$pbkdf2-sha256$29000$F2KMMaY05hxDSIlRao0xJg$QKZ3ILaj.Zaott4LFd0d2tuDLkooG0epE8R3.RE704U', 'admin'),
(2, 'operator1', '$pbkdf2-sha256$29000$KEWI0ZpzTolxbm1t7b3XOg$vTxvwLo5ewS1L9wdRnEeW3I7pNK91/1TOeXaJD52e7o', 'employee'),
(4, 'courier1', '$pbkdf2-sha256$29000$EgKAUAqhNIaQ0jqHUCrlPA$T5oy/0O1xL.qCjWC/3qQFOpNEDUzocxpXiltV3cMCLw', 'courier'),
(5, 'courier2', '$pbkdf2-sha256$29000$EgKAUAqhNIaQ0jqHUCrlPA$T5oy/0O1xL.qCjWC/3qQFOpNEDUzocxpXiltV3cMCLw', 'courier'),
(6, 'courier3', '$pbkdf2-sha256$29000$EgKAUAqhNIaQ0jqHUCrlPA$T5oy/0O1xL.qCjWC/3qQFOpNEDUzocxpXiltV3cMCLw', 'courier'),
(7, 'client1', '$pbkdf2-sha256$29000$e691rrV2jnEuZQyhdE5JyQ$vzuMLC9gSQKsPf/d3s0pXDp/9V0vsVRb1wlr2zRz5TU', 'client'),
(8, 'client2', '$pbkdf2-sha256$29000$e691rrV2jnEuZQyhdE5JyQ$vzuMLC9gSQKsPf/d3s0pXDp/9V0vsVRb1wlr2zRz5TU', 'client'),
(9, 'client3', '$pbkdf2-sha256$29000$e691rrV2jnEuZQyhdE5JyQ$vzuMLC9gSQKsPf/d3s0pXDp/9V0vsVRb1wlr2zRz5TU', 'client'),
(10, 'client4', '$pbkdf2-sha256$29000$e691rrV2jnEuZQyhdE5JyQ$vzuMLC9gSQKsPf/d3s0pXDp/9V0vsVRb1wlr2zRz5TU', 'client');

SELECT setval('users_account_user_id_seq', 10, true);

INSERT INTO persons (person_id, full_name, phone, email) VALUES
(1, 'Администратор системы', '+70000000001', 'admin@delivery.local'),
(2, 'Ольга Операторова', '+79020000001', 'operator1@example.local'),
(4, 'Иван Курьеров', '+70000000002', 'courier1@delivery.local'),
(5, 'Алексей Быстров', '+79030000001', 'courier2@example.local'),
(6, 'Никита Грузов', '+79030000002', 'courier3@example.local'),
(7, 'Анна Иванова', '+79010000001', 'anna@example.local'),
(8, 'Петр Смирнов', '+79010000002', 'petr@example.local'),
(9, 'Мария Орлова', '+79010000003', 'maria@example.local'),
(10, 'Дмитрий Волков', '+79010000004', 'dmitry@example.local');

SELECT setval('persons_person_id_seq', 10, true);

INSERT INTO clients (client_id, person_id, user_id, client_status) VALUES
(1, 7, 7, 'active'),
(2, 8, 8, 'active'),
(3, 9, 9, 'active'),
(4, 10, 10, 'inactive');

SELECT setval('clients_client_id_seq', 4, true);

INSERT INTO employees (employee_id, user_id, person_id, branch_id, employee_role, is_active) VALUES
(1, 1, 1, 1, 'admin', TRUE),
(2, 2, 2, 1, 'operator', TRUE),
(4, 4, 4, 1, 'courier', TRUE),
(5, 5, 5, 2, 'courier', TRUE),
(6, 6, 6, 3, 'courier', TRUE);

SELECT setval('employees_employee_id_seq', 6, true);

INSERT INTO couriers (employee_id, transport_type, capacity_kg) VALUES
(4, 'car', 25.00),
(5, 'bicycle', 12.50),
(6, 'truck', 250.00);

INSERT INTO delivery_statuses (status_id, code, name, description, sort_order) VALUES
(1, 'CREATED', 'Создана', 'Доставка создана клиентом', 1),
(2, 'REGISTERED', 'Зарегистрирована', 'Доставка зарегистрирована менеджером', 2),
(3, 'WAITING_COURIER', 'Ожидает курьера', 'Ожидается курьер для забора посылки', 3),
(4, 'COURIER_ASSIGNED', 'Курьер назначен', 'Курьер взял курьерскую заявку', 4),
(5, 'COURIER_PICKED_UP', 'Курьер получил посылку', 'Курьер получил посылку у отправителя', 5),
(6, 'AT_ORIGIN_BRANCH', 'В филиале отправления', 'Посылка находится в филиале отправления', 6),
(7, 'IN_TRANSIT', 'В пути', 'Посылка находится в пути между филиалами', 7),
(8, 'AT_DESTINATION_BRANCH', 'В филиале назначения', 'Посылка находится в филиале назначения', 8),
(9, 'COURIER_DELIVERING_RECIPIENT', 'Курьер доставляет получателю', 'Курьер доставляет посылку до получателя', 9),
(10, 'COURIER_DELIVERED', 'Курьер доставил посылку', 'Курьер доставил посылку получателю', 10),
(11, 'DELIVERED', 'Доставлена', 'Доставка завершена менеджером', 11),
(12, 'CANCELLED', 'Отменена', 'Доставка отменена', 12);

SELECT setval('delivery_statuses_status_id_seq', 12, true);

SELECT set_config('app.changed_by_employee_id', '2', true);
SELECT set_config('app.status_comment', 'SQL: доставка создана', true);

INSERT INTO deliveries (
    delivery_id,
    tracking_number,
    sender_client_id,
    recipient_client_id,
    origin_branch_id,
    destination_branch_id,
    sender_address_id,
    recipient_address_id,
    created_by_employee_id,
    current_status_id,
    declared_weight_kg,
    declared_value,
    description
) VALUES
(1, 'TRK-SQL-0001', 1, 2, 1, 2, 1, 2, 2, 1, 2.40, 4500.00, 'Документы и небольшой подарок'),
(2, 'TRK-SQL-0002', 2, 3, 2, 3, 12, 3, 2, 1, 5.75, 12000.00, 'Комплектующие для компьютера'),
(3, 'TRK-SQL-0003', 3, 4, 3, 1, 3, 1, 2, 1, 1.20, 800.00, 'Книги'),
(4, 'TRK-SQL-0004', 4, 1, 1, 3, 11, 3, 2, 1, 18.00, 35000.00, 'Бытовая техника'),
(5, 'TRK-SQL-0005', 1, 3, 1, 3, 1, 3, 2, 1, 0.80, 1200.00, 'Документы'),
(6, 'TRK-SQL-0006', 2, 4, 2, 1, 12, 1, 2, 1, 7.30, 5200.00, 'Одежда и аксессуары');

SELECT setval('deliveries_delivery_id_seq', 6, true);

CALL change_delivery_status(2, 2, 2, 'SQL: доставка зарегистрирована');
CALL assign_courier_to_delivery(2, 4, 2, 'pickup', 12, 250.00, 4, 'SQL: курьер взял заявку');
CALL change_delivery_status(2, 3, 2, 'SQL: ожидается курьер');
CALL change_delivery_status(2, 4, 4, 'SQL: курьер назначен');

CALL change_delivery_status(3, 2, 2, 'SQL: доставка зарегистрирована');
CALL change_delivery_status(3, 6, 1, 'SQL: посылка в филиале отправления');
CALL change_delivery_status(3, 7, 2, 'SQL: доставка передана в транспортировку');
CALL change_delivery_status(3, 8, 2, 'SQL: посылка прибыла в филиал назначения');
CALL assign_courier_to_delivery(3, 4, 3, 'delivery', 11, 350.00, 4, 'SQL: курьер взял доставку получателю');
CALL change_delivery_status(3, 9, 4, 'SQL: курьер доставляет получателю');
CALL change_delivery_status(3, 10, 4, 'SQL: курьер доставил посылку');

CALL change_delivery_status(4, 2, 2, 'SQL: доставка зарегистрирована');
CALL assign_courier_to_delivery(4, 6, 4, 'pickup', 11, 600.00, 6, 'SQL: курьер взял заявку на забор');
CALL change_delivery_status(4, 3, 2, 'SQL: ожидается курьер');
CALL change_delivery_status(4, 4, 6, 'SQL: курьер назначен');
CALL change_delivery_status(4, 5, 6, 'SQL: курьер получил посылку');
CALL change_delivery_status(4, 6, 2, 'SQL: посылка в филиале отправления');
CALL change_delivery_status(4, 7, 2, 'SQL: доставка передана в транспортировку');
CALL change_delivery_status(4, 8, 1, 'SQL: посылка прибыла в филиал назначения');
CALL assign_courier_to_delivery(4, 6, 1, 'delivery', 13, 600.00, 6, 'SQL: курьер взял доставку получателю');
CALL change_delivery_status(4, 9, 6, 'SQL: курьер доставляет получателю');
CALL change_delivery_status(4, 10, 6, 'SQL: курьер доставил посылку');
CALL change_delivery_status(4, 11, 2, 'SQL: доставка завершена');

CALL change_delivery_status(6, 2, 2, 'SQL: доставка зарегистрирована');
CALL assign_courier_to_delivery(6, 4, 2, 'pickup', 12, 400.00, 4, 'SQL: курьер взял заявку');
CALL change_delivery_status(6, 3, 2, 'SQL: ожидается курьер');
CALL change_delivery_status(6, 4, 4, 'SQL: курьер назначен');

CALL change_delivery_status(5, 12, 2, 'SQL: доставка отменена');

SELECT setval('delivery_courier_assignments_assignment_id_seq', (SELECT COALESCE(MAX(assignment_id), 1) FROM delivery_courier_assignments), true);
SELECT setval('delivery_status_history_history_id_seq', (SELECT COALESCE(MAX(history_id), 1) FROM delivery_status_history), true);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dbproj') THEN
        GRANT USAGE ON SCHEMA public TO dbproj;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dbproj;
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO dbproj;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO dbproj;
        GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA public TO dbproj;
    END IF;
END;
$$;
