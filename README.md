# OfertApp — Backend

API backend de OfertApp, una aplicación móvil para comparar precios de
productos entre distintos establecimientos comerciales. Construida con
FastAPI y SQLAlchemy, con PostgreSQL como base de datos y Redis para
caché y procesamiento de tareas asíncronas.

## Descripción del proyecto

OfertApp permite a los usuarios registrar productos, consultar sus
precios en diferentes establecimientos, marcar productos como favoritos
y recibir notificaciones cuando se publican promociones. La operación
principal del sistema —comparar precios de un mismo producto entre
varios establecimientos— requiere optimización cuidadosa de consultas,
ya que involucra relaciones entre las tablas `precios` y
`establecimientos`.

## Entidades del dominio

- **Usuario**: cuentas de la aplicación, con autenticación por token.
- **Producto**: artículos que pueden compararse entre establecimientos.
- **Establecimiento**: comercios donde se registran precios.
- **Precio**: relación entre un producto y un establecimiento, con su
  valor y fecha de actualización.
- **Favorito**: productos guardados por un usuario para seguimiento.
- **Promoción**: ofertas asociadas a un producto y establecimiento.

## Optimizaciones implementadas

| Optimización | Ubicación |
|---|---|
| Caché (cache-aside) | `app/cache.py` |
| Corrección de consulta N+1 | `app/routers/precios.py` (`comparar_precios`) |
| Tarea asíncrona (cola) | `app/queue.py`, `app/tasks.py`, `worker.py` |
| Lazy / Eager loading | `app/routers/favoritos.py` (lazy), `app/routers/precios.py` (eager) |
| Autenticación sin consultas redundantes | `app/auth.py` |

La operación de comparación de precios es la más costosa del sistema:
por cada precio es necesario conocer su establecimiento asociado. Sin
optimizar, esto genera una consulta adicional por cada precio (problema
N+1). La solución implementada usa `joinedload` de SQLAlchemy para
resolverlo con una sola consulta, combinado con un caché en Redis que
evita consultar la base de datos en solicitudes repetidas dentro de una
ventana de 60 segundos.

---

## Requisitos

- Python 3.11+
- PostgreSQL
- Redis
- VS Code (o cualquier editor)

## Instalación

```bash
cd ofertapp-backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# completar las credenciales de PostgreSQL en .env
```

## Ejecución

Servidor API:
```bash
uvicorn app.main:app --reload
```
Disponible en `http://localhost:8000`, con documentación interactiva en
`http://localhost:8000/docs`.

Worker de la cola de tareas (proceso independiente):
```bash
python worker.py
```

## Endpoints

| Método | Ruta | Descripción | Protegida |
|--------|------|-------------|-----------|
| POST | /api/auth/register | Registro de usuario | No |
| POST | /api/auth/login | Inicio de sesión | No |
| GET/POST | /api/productos | Listar/crear productos | POST sí |
| GET/POST | /api/establecimientos | Listar/crear establecimientos | POST sí |
| POST | /api/precios | Registrar precio | Sí |
| GET | /api/productos/{id}/precios | Comparar precios de un producto | Sí |
| GET/POST | /api/favoritos | Ver/crear favoritos | Sí |
| POST | /api/promociones | Crear promoción | Sí |

Las rutas protegidas requieren el header `Authorization: Bearer <token>`.

## Pruebas

Las pruebas se realizaron con Postman, cubriendo:
- Registro, login y acceso a rutas protegidas con JWT.
- Comparación de precios: verificación de HIT/MISS de caché y de la
  consulta SQL generada (una sola consulta con JOIN).
- Invalidación de caché al registrar un nuevo precio.
- Procesamiento asíncrono de notificaciones al crear una promoción.

## Notas técnicas

- Passlib requiere fijar bcrypt en la versión 4.0.1 por un conflicto de
  compatibilidad con versiones más recientes de la librería bcrypt.
- En macOS, el worker de RQ requiere la variable de entorno
  OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES para evitar un conflicto con
  el manejo de procesos del sistema operativo:
  OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES python worker.py