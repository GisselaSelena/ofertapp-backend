# OfertApp — Backend (FastAPI + SQLAlchemy) — Taller Semana 8

Backend de OfertApp (comparador de precios) implementado según TU elección
justificada de la Semana 5: **FastAPI + SQLAlchemy**, con PostgreSQL y
Redis. Flutter (tu app móvil) consumirá esta API por HTTP.

Cumple los 6 requisitos del taller:

1. **Caché (cache-aside)** → `app/cache.py`
2. **Corrección de N+1** → `app/routers/precios.py` (`comparar_precios`)
3. **Tarea asíncrona (cola)** → `app/queue.py` + `app/tasks.py` + `worker.py`
4. **Lazy vs Eager loading justificado** → `app/routers/favoritos.py` (lazy) y `app/routers/precios.py` (eager)
5. **Autenticación sin consultas redundantes** → `app/auth.py`
6. **Comparación antes/después** → ver sección de pruebas

## Por qué este caso de uso encaja con OfertApp

La operación más costosa de tu app es **comparar los precios de un
producto entre distintos establecimientos**. Por cada precio hay que saber
a qué establecimiento pertenece — si eso se hace con una consulta por
precio, es un N+1 clásico. Por eso ese es el endpoint optimizado:
`GET /api/productos/{id}/precios`.

---

## 1. Requisitos previos

- Python 3.11+ instalado
- PostgreSQL activo con una base de datos creada (ej. `ofertapp`)
- Redis corriendo (`redis-server`, o Docker: `docker run -d -p 6379:6379 redis`)
- VS Code (recomendado)

## 2. Instalación (en la terminal de VS Code)

```bash
cd ofertapp-backend
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edita .env con tus credenciales de PostgreSQL
```

## 3. Ejecución (necesitas DOS terminales en VS Code)

**Terminal 1 — servidor API:**
```bash
uvicorn app.main:app --reload
```
La API queda en `http://localhost:8000` y la documentación interactiva
(Swagger) en `http://localhost:8000/docs` — esto también te sirve para
mostrar los endpoints en el video.

**Terminal 2 — worker de la cola:**
```bash
python worker.py
```

## 4. Endpoints

| Método | Ruta                              | Descripción                            | Protegida |
|--------|-------------------------------------|-------------------------------------------|-----------|
| POST   | /api/auth/register                  | Registra usuario, devuelve token          | No        |
| POST   | /api/auth/login                     | Login, devuelve token                     | No        |
| GET/POST | /api/productos                    | Listar/crear productos                    | POST sí   |
| GET/POST | /api/establecimientos             | Listar/crear establecimientos             | POST sí   |
| POST   | /api/precios                        | Registrar precio (invalida caché)         | Sí        |
| GET    | /api/productos/{id}/precios         | **Comparar precios** (cache + eager)      | Sí        |
| GET/POST | /api/favoritos                    | Ver/crear favoritos (lazy loading)        | Sí        |
| POST   | /api/promociones                    | Crear promo (invalida caché + encola job) | Sí        |

Rutas protegidas: header `Authorization: Bearer <token>`

## 5. Guía de pruebas para el video (Postman/Insomnia o /docs de Swagger)

### a) Datos base
1. `POST /api/auth/register` → `{ "nombre", "email", "password" }` → guarda el `access_token`.
2. Con el token: crea 1 producto (`POST /api/productos`) y 3-4 establecimientos.
3. Crea varios precios del mismo producto en distintos establecimientos con `POST /api/precios`.

### b) Corrección del N+1 (comparación antes/después)
1. Llama `GET /api/productos/{id}/precios` y mira la consola del
   servidor (Terminal 1): SQLAlchemy con `echo`/logging activado te
   muestra **una sola consulta SQL con JOIN**, sin importar cuántos
   precios haya.
2. Para el "antes": descomenta temporalmente `obtener_precios_con_n1` en
   `precios.py`, pruébala en una ruta temporal, y verás **1 + N
   consultas** en consola (una por cada precio). Captura ambas consolas
   — esa es tu evidencia de comparación de rendimiento.

### c) Caché (cache-aside)
1. Llama `GET /api/productos/{id}/precios` dos veces seguidas.
   - 1ª vez → `🔴 CACHE MISS` (consulta real a PostgreSQL).
   - 2ª vez (dentro de 60s) → `🟢 CACHE HIT` (responde desde Redis).
     Compara el tiempo de respuesta en Postman ("Time") entre ambas.
2. Registra un nuevo precio (`POST /api/precios`) → verás `🗑️ Cache invalidado`.
3. Vuelve a llamar el comparador → nuevo MISS, con el precio actualizado.

### d) Tarea asíncrona
1. Crea una promoción (`POST /api/promociones`) para un producto que
   algún usuario tenga en favoritos.
2. La respuesta HTTP regresa inmediata. En la Terminal 2 (worker) verás
   el job procesándose y las notificaciones "enviándose", sin haber
   bloqueado la petición.

### e) Autenticación sin consultas redundantes
- Llama varias veces a cualquier endpoint protegido con el mismo token y
  observa que **no** se ejecuta ningún `SELECT` sobre `usuarios` (el
  payload ya viene del JWT).

---

## 6. Subir el proyecto a GitHub (desde la terminal de VS Code)

```bash
git init
git add .
git commit -m "Backend OfertApp: cache, N+1, cola, auth"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/ofertapp-backend.git
git push -u origin main
```

Si aún no tienes el repositorio: entra a github.com → "New repository" →
nómbralo (ej. `ofertapp-backend`) → copia la URL → úsala en el
`git remote add origin ...` de arriba.

**No subas tu `.env` real** (ya está en `.gitignore`) — solo el
`.env.example` con valores de ejemplo.

## 7. Qué mostrar en el video (según la rúbrica)

- Presenta OfertApp y el modelo de datos (Usuario, Producto,
  Establecimiento, Precio, Favorito, Promoción).
- Explica el flujo de autenticación (registro → login → token → rutas
  protegidas) y por qué no genera consultas redundantes.
- Muestra `cache.py` y demuestra HIT/MISS en vivo sobre el comparador de precios.
- Muestra el código "antes" (N+1) vs "después" (`joinedload`) y compara
  las consultas SQL en consola.
- Muestra el worker en su propia terminal procesando la notificación de
  promoción, sin bloquear la creación de la promo.
- Explica la justificación lazy (favoritos) vs eager (establecimiento en
  precios).
- Menciona dificultades encontradas — sé honesta, es parte de la evaluación.
