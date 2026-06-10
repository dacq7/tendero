"""Siembra datos de DEMOSTRACIÓN para la analítica (separado de app.seed).

- IDEMPOTENTE: borra-y-recrea el dataset de demo (no acumula). Re-ejecutar deja
  el mismo conteo de ventas.
- DETERMINISTA: un único PRNG sembrado (Random(SEED)) y una FECHA DE CORTE fija;
  no usa `now()` ni el random global. Reproducible bit a bit.
- CONSISTENTE: reutiliza las funciones puras de pricing (sale_pricing) — la misma
  matemática que create_sale — y congela costo/snapshots; el stock se descuenta y
  el kardex queda coherente; cada venta tiene su factura POS.

Uso:  python -m app.seed_demo
Genera ~18 meses de ventas (cientos) con horas pico, estacionalidad, proveedores,
reposición mensual de inventario y clientes recurrentes (junto a ventas anónimas).
La historia de 18 meses permite comparativas YoY en los meses solapados.
NOTA: las ventas por tarjeta/PSE/Nequi se marcan pagadas directamente (sin pasar
por el flujo Wompi); para la analítica solo importa el método y el total.
"""

import os
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import text
from sqlmodel import Session

from app.core.security import hash_password
from app.db.session import engine
from app.models.cash_register_session import CashRegisterSession, CashSessionStatus
from app.models.inventory_movement import InventoryMovement, MovementType
from app.models.invoice import Invoice
from app.models.invoice_sequence import InvoiceSequence
from app.models.product import IvaRate, Product, ProductUnit
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleStatus
from app.models.supplier import Supplier
from app.models.user import User, UserRole
from app.services import sale_pricing

SEED = 20260601
FECHA_CORTE = date(2026, 6, 1)  # fija → reproducible
MESES = 18  # ~1.5 años → habilita comparativas YoY en los meses solapados
SERIE = "POS"

DEMO_EMAIL_PREFIX = "demo."
DEMO_SKU_PREFIX = "DEMO-"
DEMO_NIT_PREFIX = "DEMO-"  # NIT de proveedores demo (mismo marcador para el wipe)
DEMO_PASSWORD = "Demo1234!"

CAJEROS = ["demo.cajero1@tendero.co", "demo.cajero2@tendero.co", "demo.cajero3@tendero.co"]

# Proveedores demo. El reparto desigual de productos (ver _create_products) crea
# concentración realista para el bloque de PROVEEDORES.
PROVEEDORES = [
    ("Distribuidora La 14", "DEMO-900111"),
    ("Coca-Cola FEMSA", "DEMO-900222"),
    ("Bavaria Directo", "DEMO-900333"),
    ("Surtitienda Mayorista", "DEMO-900444"),
    ("Lácteos El Pomar", "DEMO-900555"),
]

# Clientes recurrentes (CC) que vuelven a comprar; el resto de ventas son anónimas
# ("Consumidor final"), como en una tienda de barrio real.
CLIENTES = [
    ("1098765432", "María Restrepo"),
    ("1015896321", "José Gutiérrez"),
    ("43258741", "Luz Marina Ospina"),
    ("8025463", "Carlos Andrés Mejía"),
    ("1122334455", "Diana Carolina Ruiz"),
    ("71234567", "Fernando Quintero"),
    ("52369874", "Sandra Milena Torres"),
    ("1003214567", "Andrés Felipe Cardona"),
    ("39654123", "Gloria Inés Patiño"),
    ("80123456", "Wilson Ramírez"),
]
# Probabilidad de que una venta sea de un cliente recurrente (resto: anónima).
PROB_CLIENTE = 0.4

# Catálogo de tienda de barrio: (nombre, categoria, iva, costo_centavos, venta_centavos, unidad)
CATALOGO = [
    ("Gaseosa 400ml", "Bebidas", IvaRate.tarifa_19, 120000, 200000, ProductUnit.unidad),
    ("Agua 600ml", "Bebidas", IvaRate.tarifa_19, 60000, 120000, ProductUnit.unidad),
    ("Jugo Hit 250ml", "Bebidas", IvaRate.tarifa_19, 90000, 150000, ProductUnit.unidad),
    ("Cerveza lata", "Licores", IvaRate.tarifa_19, 200000, 350000, ProductUnit.unidad),
    ("Aguardiente 375ml", "Licores", IvaRate.tarifa_19, 1800000, 2600000, ProductUnit.unidad),
    ("Papas medianas", "Snacks", IvaRate.tarifa_19, 130000, 220000, ProductUnit.unidad),
    ("Galletas saltinas", "Snacks", IvaRate.tarifa_19, 80000, 140000, ProductUnit.unidad),
    ("Chocolatina", "Dulces", IvaRate.tarifa_19, 50000, 100000, ProductUnit.unidad),
    ("Bombón x un.", "Dulces", IvaRate.tarifa_19, 5000, 20000, ProductUnit.unidad),
    ("Leche entera 1L", "Lácteos", IvaRate.exento, 280000, 380000, ProductUnit.unidad),
    ("Queso campesino", "Lácteos", IvaRate.tarifa_5, 600000, 850000, ProductUnit.unidad),
    ("Huevos x30", "Lácteos", IvaRate.exento, 1400000, 1800000, ProductUnit.unidad),
    ("Arroz 1kg", "Abarrotes", IvaRate.exento, 300000, 420000, ProductUnit.kg),
    ("Frijol 1kg", "Abarrotes", IvaRate.exento, 700000, 950000, ProductUnit.kg),
    ("Aceite 1L", "Abarrotes", IvaRate.tarifa_19, 800000, 1100000, ProductUnit.unidad),
    ("Panela 1kg", "Abarrotes", IvaRate.exento, 350000, 480000, ProductUnit.kg),
    ("Pan tajado", "Panadería", IvaRate.tarifa_19, 350000, 520000, ProductUnit.unidad),
    ("Arepa x5", "Panadería", IvaRate.exento, 200000, 320000, ProductUnit.unidad),
    ("Jabón en barra", "Aseo", IvaRate.tarifa_19, 150000, 260000, ProductUnit.unidad),
    ("Detergente 500g", "Aseo", IvaRate.tarifa_19, 400000, 650000, ProductUnit.unidad),
    ("Papel higiénico x4", "Aseo", IvaRate.tarifa_19, 450000, 720000, ProductUnit.unidad),
    (
        "Cigarrillos cajetilla",
        "Cigarrillos",
        IvaRate.tarifa_19,
        900000,
        1300000,
        ProductUnit.unidad,
    ),
    ("Café 250g", "Bebidas", IvaRate.tarifa_19, 600000, 900000, ProductUnit.unidad),
    ("Atún lata", "Abarrotes", IvaRate.tarifa_19, 350000, 560000, ProductUnit.unidad),
    ("Salchichón", "Abarrotes", IvaRate.tarifa_19, 500000, 780000, ProductUnit.unidad),
    ("Yogurt 200ml", "Lácteos", IvaRate.tarifa_5, 110000, 190000, ProductUnit.unidad),
    ("Energizante", "Bebidas", IvaRate.tarifa_19, 250000, 420000, ProductUnit.unidad),
    ("Crema dental", "Aseo", IvaRate.tarifa_19, 300000, 500000, ProductUnit.unidad),
]

# Método de pago ponderado (más efectivo, como una tienda real).
METODOS = (
    [PaymentMethod.efectivo] * 6
    + [PaymentMethod.tarjeta] * 2
    + [PaymentMethod.nequi] * 2
    + [PaymentMethod.pse] * 1
)

# Peso de cada hora del día (0..23): casi nada de madrugada, picos mañana y tarde.
HORA_WEIGHTS = [1, 1, 1, 1, 1, 2, 5, 9, 12, 11, 10, 12, 13, 10, 8, 9, 12, 16, 17, 13, 8, 5, 3, 2]
# Estacionalidad mensual (1..12): diciembre y mitad de año más altos.
MES_FACTOR = {
    1: 0.9,
    2: 0.85,
    3: 0.95,
    4: 1.0,
    5: 1.05,
    6: 1.15,
    7: 1.0,
    8: 0.95,
    9: 1.0,
    10: 1.05,
    11: 1.1,
    12: 1.4,
}
# Día de semana (lun=0..dom=6): fin de semana más movido.
DOW_FACTOR = [0.9, 0.9, 1.0, 1.05, 1.2, 1.4, 1.15]
VENTAS_BASE = 3  # media base por cajero-día antes de los factores

INITIAL_STOCK = 120_000  # milésimas por producto al arrancar (~120 unidades)
# Reposición proporcional al consumo: al cambiar de mes se repone cada producto
# hasta cubrir ~COBERTURA_MESES de la venta del mes anterior (entrada = compra al
# proveedor). Así el stock queda PROPORCIONAL a la velocidad de venta y la
# rotación sale sensata: los que más venden rotan rápido, los lentos acumulan
# capital inmovilizado. Da, además, historia de compras por proveedor.
COBERTURA_MESES = 2
STOCK_MINIMO_BUFFER = 20_000  # piso de reposición (~20 unidades)


# Sub-SELECT de las VENTAS a eliminar: las de cajeros demo Y cualquier venta que
# referencie un producto demo. Esto último cubre ventas NO-demo (p. ej. pruebas
# manuales) que apuntan a productos demo: como `sale_items.product_id` es RESTRICT,
# bloquearían el borrado de productos. seed_demo solo corre en entornos NO-producción
# (guarda APP_ENV), donde esos datos son desechables, así que se eliminan ENTERAS
# (con su cadena de dependientes) para no dejar FKs colgando ni filas corruptas.
# SQL 100% literal estático; los valores van SIEMPRE como parámetros ligados (:p, :s).
_VENTAS_A_BORRAR = (
    "SELECT id FROM sales "
    "WHERE user_id IN (SELECT id FROM users WHERE email LIKE :p) "
    "OR id IN (SELECT sale_id FROM sale_items "
    "WHERE product_id IN (SELECT id FROM products WHERE sku LIKE :s))"
)


def _wipe_demo(session: Session) -> None:
    """Borra el dataset de demo respetando las FKs (hijos antes que padres).
    Idempotencia: borra-y-recrea. Cada fila se identifica por su marcador
    (demo./DEMO-); las ventas que referencian productos demo se incluyen para que
    el borrado de productos (RESTRICT) nunca quede bloqueado.

    Orden FK-seguro:
      fiscal_emissions → payments → invoices → sales (CASCADE borra sale_items) →
      inventory_movements → products → suppliers → cash_register_sessions → users

    NO se borran sale_items por separado: hacerlo ANTES de las ventas vaciaría el
    predicado (una venta deja de "referenciar un producto demo" y sobreviviría
    huérfana). `sale_items.sale_id` es ON DELETE CASCADE, así que el borrado de las
    ventas limpia sus líneas — incluidas las que apuntan a productos demo.

    Todo el SQL es literal estático con parámetros ligados; NUNCA se interpola
    entrada (sin riesgo de inyección)."""
    p = {"p": f"{DEMO_EMAIL_PREFIX}%", "s": f"{DEMO_SKU_PREFIX}%"}

    # 1) fiscal_emissions cuelga de invoices (RESTRICT) → primero.
    session.exec(
        text(
            "DELETE FROM fiscal_emissions WHERE invoice_id IN "
            "(SELECT id FROM invoices WHERE sale_id IN (" + _VENTAS_A_BORRAR + "))"
        ),
        params=p,
    )
    # 2) payments cuelga de sales (RESTRICT).
    session.exec(
        text("DELETE FROM payments WHERE sale_id IN (" + _VENTAS_A_BORRAR + ")"),
        params=p,
    )
    # 3) invoices cuelga de sales (RESTRICT).
    session.exec(
        text("DELETE FROM invoices WHERE sale_id IN (" + _VENTAS_A_BORRAR + ")"),
        params=p,
    )
    # 4) sales: el predicado se evalúa con los sale_items aún presentes (para
    #    capturar las ventas que referencian productos demo); la CASCADE de
    #    sale_items.sale_id borra sus líneas, liberando la FK hacia products.
    session.exec(text("DELETE FROM sales WHERE id IN (" + _VENTAS_A_BORRAR + ")"), params=p)
    # 5) inventory_movements cuelga de products (RESTRICT).
    session.exec(
        text(
            "DELETE FROM inventory_movements WHERE product_id IN "
            "(SELECT id FROM products WHERE sku LIKE :s)"
        ),
        params={"s": p["s"]},
    )
    # 6) products (ya sin sale_items ni movimientos que lo referencien).
    session.exec(text("DELETE FROM products WHERE sku LIKE :s"), params={"s": p["s"]})
    # 7) suppliers DESPUÉS de products (FK products.supplier_id, RESTRICT).
    session.exec(
        text("DELETE FROM suppliers WHERE nit LIKE :n"), params={"n": f"{DEMO_NIT_PREFIX}%"}
    )
    # 8) cash_register_sessions: ya sin sales que la referencien (RESTRICT).
    session.exec(
        text(
            "DELETE FROM cash_register_sessions WHERE user_id IN "
            "(SELECT id FROM users WHERE email LIKE :p)"
        ),
        params={"p": p["p"]},
    )
    # 9) users demo (ya sin sales ni cajas que los referencien).
    session.exec(text("DELETE FROM users WHERE email LIKE :p"), params={"p": p["p"]})
    session.commit()


def _create_suppliers(session: Session) -> list[Supplier]:
    suppliers = []
    for nombre, nit in PROVEEDORES:
        s = Supplier(nombre=nombre, nit=nit)
        session.add(s)
        suppliers.append(s)
    session.flush()
    return suppliers


def _create_cajeros(session: Session) -> list[User]:
    cajeros = []
    for i, email in enumerate(CAJEROS, start=1):
        user = User(
            email=email,
            full_name=f"Cajero Demo {i}",
            hashed_password=hash_password(DEMO_PASSWORD),
            role=UserRole.cajero,
        )
        session.add(user)
        cajeros.append(user)
    session.flush()
    return cajeros


def _supplier_para(idx: int, n_suppliers: int) -> int:
    """Reparto desigual: el primer proveedor concentra ~40% de los productos, el
    resto se reparte. Genera dependencia de proveedor (bloque PROVEEDORES)."""
    return 0 if idx % 5 < 2 else (1 + (idx % (n_suppliers - 1)))


def _create_products(session: Session, suppliers: list[Supplier]) -> list[Product]:
    products = []
    for idx, (nombre, cat, iva, costo, venta, unidad) in enumerate(CATALOGO, start=1):
        proveedor = suppliers[_supplier_para(idx, len(suppliers))]
        p = Product(
            nombre=nombre,
            sku=f"{DEMO_SKU_PREFIX}{idx:03d}",
            categoria=cat,
            iva=iva,
            unidad=unidad,
            supplier_id=proveedor.id,
            precio_costo_centavos=costo,
            precio_venta_centavos=venta,
            stock_milesimas=INITIAL_STOCK,
            stock_minimo_milesimas=30_000,  # ~30 unidades, a escala del stock real
        )
        session.add(p)
        products.append(p)
    session.flush()
    # Movimiento de carga inicial (entrada) por producto, para que el kardex cuadre.
    base_dt = datetime.combine(FECHA_CORTE - timedelta(days=MESES * 31), time(7, 0))
    for p in products:
        session.add(
            InventoryMovement(
                product_id=p.id,
                tipo=MovementType.entrada,
                cantidad_milesimas=INITIAL_STOCK,
                costo_unitario_centavos=p.precio_costo_centavos,
                stock_resultante_milesimas=INITIAL_STOCK,
                motivo="Carga inicial (demo)",
                created_at=base_dt,
            )
        )
    session.flush()
    return products


def _hora(rng: random.Random) -> time:
    h = rng.choices(range(24), weights=HORA_WEIGHTS, k=1)[0]
    return time(h, rng.randint(0, 59), rng.randint(0, 59))


def seed_demo(db_engine=None, meses: int = MESES) -> dict:
    """Siembra el dataset de demo. `db_engine`/`meses` parametrizables para tests
    (un rango corto produce un dataset chico pero igual de consistente)."""
    if os.getenv("APP_ENV", "development") == "production":
        raise RuntimeError("seed_demo NO debe ejecutarse en producción (borra/crea datos).")
    rng = random.Random(SEED)
    with Session(db_engine or engine) as session:
        _wipe_demo(session)
        cajeros = _create_cajeros(session)
        suppliers = _create_suppliers(session)
        products = _create_products(session, suppliers)
        stock = {p.id: INITIAL_STOCK for p in products}

        seq = session.get(InvoiceSequence, SERIE)
        if seq is None:
            seq = InvoiceSequence(serie=SERIE, last_numero=0)
            session.add(seq)
            session.flush()
        numero = seq.last_numero

        inicio = FECHA_CORTE - timedelta(days=meses * 30)
        total_ventas = 0
        dia = inicio
        mes_visto = (inicio.year, inicio.month)
        consumo_mes = dict.fromkeys(stock, 0)  # milésimas vendidas en el mes en curso
        while dia < FECHA_CORTE:
            # Reposición al cambiar de mes: repone cada producto hasta cubrir
            # ~COBERTURA_MESES del consumo del mes anterior (entrada = compra).
            if (dia.year, dia.month) != mes_visto:
                mes_visto = (dia.year, dia.month)
                restock_dt = datetime.combine(dia, time(6, 0))
                for prod in products:
                    objetivo = max(STOCK_MINIMO_BUFFER, consumo_mes[prod.id] * COBERTURA_MESES)
                    falta = objetivo - stock[prod.id]
                    if falta > 0:
                        stock[prod.id] += falta
                        session.add(
                            InventoryMovement(
                                product_id=prod.id,
                                tipo=MovementType.entrada,
                                cantidad_milesimas=falta,
                                costo_unitario_centavos=prod.precio_costo_centavos,
                                stock_resultante_milesimas=stock[prod.id],
                                motivo="Reposición mensual (demo)",
                                created_at=restock_dt,
                            )
                        )
                    consumo_mes[prod.id] = 0
                session.flush()
            factor = MES_FACTOR[dia.month] * DOW_FACTOR[dia.weekday()]
            # Cajeros que "trabajan" ese día (1-2).
            trabajan = rng.sample(cajeros, k=rng.randint(1, 2))
            for cajero in trabajan:
                n = max(0, int(round(VENTAS_BASE * factor * rng.uniform(0.6, 1.4))))
                if n == 0:
                    continue
                caja = CashRegisterSession(
                    user_id=cajero.id,
                    status=CashSessionStatus.cerrada,
                    monto_inicial_centavos=10_000_000,
                    abierta_at=datetime.combine(dia, time(7, 30)),
                    cerrada_at=datetime.combine(dia, time(21, 0)),
                    closed_by_user_id=cajero.id,
                )
                session.add(caja)
                session.flush()
                efectivo_caja = 0
                for _ in range(n):
                    dt = datetime.combine(dia, _hora(rng))
                    metodo = rng.choice(METODOS)
                    n_lineas = rng.randint(1, 5)
                    elegidos = rng.sample(products, k=n_lineas)
                    lts = []
                    items_data = []
                    for prod in elegidos:
                        # Cantidad: granel en fracciones, resto en unidades.
                        if prod.unidad == ProductUnit.kg:
                            cant = rng.choice([250, 500, 1000, 1500, 2000])
                        else:
                            cant = rng.randint(1, 4) * 1000
                        if stock[prod.id] < cant:
                            continue
                        stock[prod.id] -= cant
                        consumo_mes[prod.id] += cant
                        lt = sale_pricing.line_totals(prod.precio_venta_centavos, prod.iva, cant)
                        lts.append(lt)
                        items_data.append((prod, cant, lt))
                    if not items_data:
                        continue
                    # Cliente recurrente (CC) o anónimo ("Consumidor final").
                    if rng.random() < PROB_CLIENTE:
                        cliente_doc, cliente_nombre = rng.choice(CLIENTES)
                    else:
                        cliente_doc, cliente_nombre = None, None
                    totals = sale_pricing.sale_totals(lts)
                    sale = Sale(
                        cash_session_id=caja.id,
                        user_id=cajero.id,
                        subtotal_centavos=totals.subtotal_centavos,
                        iva_total_centavos=totals.iva_total_centavos,
                        total_centavos=totals.total_centavos,
                        status=SaleStatus.pagada,
                        metodo_pago=metodo,
                        customer_doc=cliente_doc,
                        customer_nombre=cliente_nombre,
                        created_at=dt,
                        paid_at=dt,
                    )
                    session.add(sale)
                    session.flush()
                    for prod, cant, lt in items_data:
                        session.add(
                            SaleItem(
                                sale_id=sale.id,
                                product_id=prod.id,
                                nombre_snapshot=prod.nombre,
                                sku_snapshot=prod.sku,
                                cantidad_milesimas=cant,
                                precio_unitario_centavos=prod.precio_venta_centavos,
                                costo_unitario_snapshot_centavos=prod.precio_costo_centavos,
                                iva_rate_snapshot=prod.iva,
                                iva_bps_snapshot=lt.iva_bps,
                                base_centavos=lt.base_centavos,
                                iva_centavos=lt.iva_centavos,
                                total_linea_centavos=lt.total_linea_centavos,
                            )
                        )
                        session.add(
                            InventoryMovement(
                                product_id=prod.id,
                                tipo=MovementType.salida,
                                cantidad_milesimas=cant,
                                costo_unitario_centavos=prod.precio_costo_centavos,
                                stock_resultante_milesimas=stock[prod.id],
                                motivo="Venta (demo)",
                                user_id=cajero.id,
                                created_at=dt,
                            )
                        )
                    numero += 1
                    session.add(
                        Invoice(
                            sale_id=sale.id,
                            serie=SERIE,
                            numero=numero,
                            numero_completo=f"{SERIE}-{numero:06d}",
                            subtotal_centavos=totals.subtotal_centavos,
                            iva_total_centavos=totals.iva_total_centavos,
                            total_centavos=totals.total_centavos,
                            metodo_pago=metodo,
                            created_at=dt,
                        )
                    )
                    total_ventas += 1
                    if metodo == PaymentMethod.efectivo:
                        efectivo_caja += totals.total_centavos
                # Arqueo de la caja con una pequeña diferencia determinista.
                esperado = caja.monto_inicial_centavos + efectivo_caja
                dif = rng.choice([0, 0, 0, -50000, 50000, -100000])
                caja.efectivo_esperado_centavos = esperado
                caja.efectivo_contado_centavos = esperado + dif
                caja.diferencia_centavos = dif
                session.add(caja)
            dia += timedelta(days=1)

        # Reposición de cierre: deja el inventario final en una foto realista y
        # DESIGUAL (cada producto a una cobertura distinta del último mes). Evita
        # medir la rotación sobre el "diente de sierra" vacío de fin de mes y crea
        # variedad: algunos quedan sobre-stockeados (capital lento), otros bajo el
        # mínimo (entran a recompra).
        cierre_dt = datetime.combine(FECHA_CORTE - timedelta(days=1), time(20, 0))
        for prod in products:
            # Algunos productos quedan sobre-comprados (>6 meses de cobertura):
            # capital inmovilizado realista, sin hundir la rotación global.
            cobertura = rng.uniform(6.5, 8.0) if rng.random() < 1 / 16 else rng.uniform(0.4, 2.6)
            # El float solo vive en el PRNG; el stock SIEMPRE es entero (milésimas).
            objetivo = int(round(consumo_mes[prod.id] * cobertura))
            falta = objetivo - stock[prod.id]
            if falta > 0:
                stock[prod.id] += falta
                session.add(
                    InventoryMovement(
                        product_id=prod.id,
                        tipo=MovementType.entrada,
                        cantidad_milesimas=falta,
                        costo_unitario_centavos=prod.precio_costo_centavos,
                        stock_resultante_milesimas=stock[prod.id],
                        motivo="Reposición de cierre (demo)",
                        created_at=cierre_dt,
                    )
                )
        session.flush()

        # Persistir el stock final de cada producto y la secuencia POS.
        for p in products:
            p.stock_milesimas = stock[p.id]
            session.add(p)
        seq.last_numero = numero
        session.add(seq)
        session.commit()
    return {
        "ventas": total_ventas,
        "productos": len(products),
        "cajeros": len(cajeros),
        "proveedores": len(suppliers),
        "clientes": len(CLIENTES),
    }


if __name__ == "__main__":
    resultado = seed_demo()
    print(
        f"Seed de demo: {resultado['ventas']} ventas, {resultado['productos']} productos, "
        f"{resultado['cajeros']} cajeros, {resultado['proveedores']} proveedores, "
        f"{resultado['clientes']} clientes recurrentes."
    )
