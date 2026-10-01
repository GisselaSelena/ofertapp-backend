# OfertApp — Backend

API para comparar precios de productos entre establecimientos. Está
construida con FastAPI y SQLAlchemy; PostgreSQL almacena los datos, Redis
sirve la caché y la cola de tareas, y Gemini genera resúmenes inteligentes
de precios.

## Requisitos

- Python 3.11 o superior
- PostgreSQL y Redis para ejecutar la aplicación completa
- Una clave de Gemini solo si se quieren generar resúmenes con IA

## Instalación y configuración

```bash
git clone https://github.com/GisselaSelena/ofertapp-backend.git
cd ofertapp-backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con la URL y credenciales de tu PostgreSQL, la dirección de
Redis y un `JWT_SECRET` propio y seguro. No subas `.env` ni claves reales al
repositorio. Para habilitar Gemini, configura `GEMINI_API_KEY`; las demás
variables de Gemini son:

| Variable | Uso | Valor de ejemplo |
|---|---|---|
| `GEMINI_API_KEY` | Clave privada del servicio Gemini; se configura solo localmente/como secreto de despliegue | *(no incluir una clave real)* |
| `GEMINI_BASE_URL` | URL base de la API de Gemini | `https://generativelanguage.googleapis.com` |
| `GEMINI_MODEL` | Modelo solicitado para generar texto | `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Tiempo máximo de espera | `10` |

También se pueden configurar `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`,
`JWT_SECRET`, `JWT_ALGORITHM` y `JWT_EXPIRE_MINUTES`. Los nombres y valores
de muestra están en [.env.example](.env.example); sus credenciales son
marcadores de posición, no deben usarse como secretos de producción.

## Ejecución

Inicia la API:

```bash
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`; Swagger UI está en
`http://localhost:8000/docs` y OpenAPI en `http://localhost:8000/openapi.json`.

Para procesar notificaciones de promociones, inicia el worker en otra
terminal:

```bash
python worker.py
```

En macOS, si RQ necesita el ajuste de fork del sistema:

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES python worker.py
```

## Roles y acceso

Hay dos roles: `usuario` y `administrador`. El registro público siempre
crea una cuenta con rol `usuario`; el cliente no puede elegir el rol en el
formulario de registro. Las rutas de lectura públicas no requieren token,
las rutas de usuario requieren `Authorization: Bearer <token>`, y las
operaciones administrativas requieren un token válido con rol
`administrador`.

Para promover una cuenta existente, ejecuta el siguiente SQL con una
conexión administrativa a PostgreSQL y reemplaza el correo de ejemplo:

```sql
UPDATE usuarios
SET rol = 'administrador'
WHERE email = 'admin@example.com';
```

Los tokens incluyen el rol al iniciar sesión. Después de cambiarlo en la
base de datos, la persona debe iniciar sesión de nuevo para obtener un
token con el rol actualizado.

## Precios e historial

Cada reporte crea un registro en `precios` con `vigente_desde` y
`vigente_hasta`. Al registrar un precio para el mismo producto y
establecimiento, el precio anterior deja de estar vigente (`vigente_hasta`
se establece a la fecha del nuevo reporte) y se crea un registro nuevo que
permanece vigente hasta el siguiente cambio. El endpoint de comparación
devuelve precios actuales; el de historial devuelve registros anteriores
y actuales, ordenados desde el más reciente.

`PrecioCreate` acepta estos campos opcionales relacionados con evidencia:

- `reportado_lat` y `reportado_lng`: coordenadas de ubicación; ambos son
  numéricos y opcionales.
- `tiene_foto_evidencia`: booleano opcional (por defecto `false`) que
  indica si existe evidencia fotográfica. Actualmente el API guarda el
  indicador, no una imagen o URL de archivo.

## Endpoints

Las rutas de esta tabla corresponden a los routers registrados en
`app/main.py`. Para las rutas protegidas, una solicitud sin autenticación
responde `401`; si el endpoint requiere administrador, un token válido de
usuario normal responde `403`. Los cuerpos que no superen la validación
Pydantic responden `422`.

| Método | Ruta | Acceso | Respuestas documentadas por la implementación |
|---|---|---|---|
| GET | `/health` | Público | `200` |
| POST | `/api/auth/register` | Público | `201`, `409` (correo existente), `422` |
| POST | `/api/auth/login` | Público | `200`, `401` (credenciales incorrectas), `422` |
| GET | `/api/productos` | Público | `200` |
| POST | `/api/productos` | Administrador | `201`, `401`, `403`, `422` |
| PUT | `/api/productos/{producto_id}` | Administrador | `200`, `401`, `403`, `404`, `422` |
| DELETE | `/api/productos/{producto_id}` | Administrador | `204`, `401`, `403`, `404`, `409` si tiene relaciones y no se fuerza el borrado |
| GET | `/api/establecimientos` | Público | `200` |
| POST | `/api/establecimientos` | Administrador | `201`, `401`, `403`, `422` |
| PUT | `/api/establecimientos/{establecimiento_id}` | Administrador | `200`, `401`, `403`, `404`, `422` |
| DELETE | `/api/establecimientos/{establecimiento_id}` | Administrador | `204`, `401`, `403`, `404`, `409` si tiene relaciones y no se fuerza el borrado |
| POST | `/api/precios` | Administrador | `201`, `401`, `403`, `422` |
| GET | `/api/productos/{producto_id}/precios` | Usuario autenticado | `200`, `401` |
| GET | `/api/productos/{producto_id}/precios/historial` | Usuario autenticado | `200`, `401`; filtro opcional `establecimiento_id` |
| GET | `/api/productos/{producto_id}/resumen-ia` | Usuario autenticado | `200`, `401`; si no hay precios o Gemini no está disponible, devuelve `disponible: false` |
| GET | `/api/favoritos` | Usuario autenticado | `200`, `401` |
| POST | `/api/favoritos` | Usuario autenticado | `201`, `401`, `409` (ya existe), `422` |
| DELETE | `/api/favoritos/{favorito_id}` | Usuario autenticado; solo puede borrar sus favoritos | `204`, `401`, `403`, `404` |
| POST | `/api/promociones` | Administrador | `201`, `401`, `403`, `422` |

Los borrados de productos y establecimientos aceptan el parámetro de
consulta `forzar`, que por defecto es `false`:

```text
DELETE /api/productos/{producto_id}?forzar=true
DELETE /api/establecimientos/{establecimiento_id}?forzar=true
```

Sin forzar, una entidad con relaciones responde `409` con `detail` que
incluye `mensaje`, `nombre` y los conteos de `precios`, `favoritos` y
`promociones`. Con `forzar=true`, el backend elimina las relaciones dentro
de la transacción antes de borrar la entidad; responde `204` si tiene
éxito. También invalida las cachés de precios y del resumen inteligente
afectadas.

## Resumen inteligente con Gemini

`GET /api/productos/{producto_id}/resumen-ia` reúne los precios vigentes y
parte del historial reciente del producto, y pide a Gemini un resumen
corto en español sobre la mejor opción actual y la tendencia observada.
Los resultados se almacenan en Redis durante cinco minutos. Si no hay
precios vigentes o Gemini no está configurado/no responde, el endpoint
indica que el resumen no está disponible; los precios reales siguen
consultándose desde la API.

Configura `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL` y
`GEMINI_TIMEOUT_SECONDS` en el entorno del proceso. No guardes la clave en
README, `.env.example`, código, logs ni commits.

## Pruebas

Instala las dependencias de desarrollo y ejecuta pytest:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas automatizadas usan dobles/fakes para sesiones de base de datos
y Redis. No necesitan PostgreSQL ni Redis corriendo. Cubren autenticación,
permisos de administrador, CRUD del catálogo, borrado forzado y rollback,
conteos de relaciones, invalidación de caché y rutas relevantes.

GitHub Actions ejecuta la misma suite en cada `push` y `pull_request`.
