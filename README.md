# Sistema de Gestión Integral para Pollería

Aplicación full-stack en **Reflex (Python)** con **PostgreSQL**, pensada para usarse desde una tablet en el punto de venta y también desde computadora o celular.

## Qué incluye

- Autenticación con roles (admin, supervisor, vendedor) y contraseñas hasheadas
- Punto de venta rápido (venta detallada y venta rápida)
- Productos, inventario, compras, gastos y cierre de caja
- Dashboard con KPIs, gráficos y reportes
- Cálculo de facturación, costo de mercadería, ganancia bruta y ganancia neta estimada

Las ventas rápidas **no inventan** costo ni ganancia: solo registran el importe.

## Requisitos

- Python 3.11+ (recomendado 3.13)
- PostgreSQL 14+ para producción
- Node.js no es necesario instalarlo a mano: Reflex lo gestiona

## Instalación local

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Base de datos

**Opción A — PostgreSQL local (recomendado)**

```powershell
docker compose up -d
copy .env.example .env
```

En `.env`:

```
DATABASE_URL=postgresql+psycopg://polleria:polleria@localhost:5432/polleria
SEED_DEMO=true
```

**Opción B — SQLite solo para desarrollo**

No definas `DATABASE_URL`. La app usará `polleria.db` en la carpeta del proyecto.

### Ejecutar

```powershell
.\run.ps1
```

O manualmente:

```powershell
.\.venv\Scripts\reflex.exe run
```

Abrí http://localhost:3000

### Error al instalar frontend (npm EOVERRIDE postcss)

Si ves `Override for postcss conflicts with direct dependency`, es un bug conocido de **Reflex 0.9 + npm 10** en proyectos dentro de **OneDrive** (Reflex fuerza npm en ese caso).

Solución incluida en el proyecto:

```powershell
.\run.ps1
```

Ese script aplica el parche y levanta el servidor. Si recreás el entorno virtual, volvé a usar `.\run.ps1` la primera vez.

**Recomendación:** mover el proyecto fuera de OneDrive (por ejemplo `C:\dev\app2-GestionP`) mejora velocidad y evita varios problemas en Windows.

## Primer acceso (producción)

1. Abrí la app: si no hay usuarios, te redirige a **Crear cuenta inicial**.
2. El primer usuario registrado es **administrador**.
3. Los demás usuarios los crea el admin desde **Usuarios** (el registro público queda cerrado).

En desarrollo local podés activar datos de prueba con `SEED_DEMO=true` en `.env` (no usar en producción).

### Gmail (verificación y recuperación de contraseña)

En `.env`:

```env
APP_BASE_URL=http://localhost:3000
GMAIL_USER=tu@gmail.com
GMAIL_APP_PASSWORD=contraseña_de_aplicacion
MAIL_FROM_NAME=La Fábrica del Pollo
```

1. En Google: **Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones**
2. Creá una contraseña para "Correo" y pegala en `GMAIL_APP_PASSWORD`
3. Al registrarse, el usuario recibe un email para **verificar la cuenta**
4. **Olvidé mi contraseña** en `/olvide-contrasena` envía un enlace válido 1 hora

Sin Gmail configurado, los usuarios existentes pueden ingresar; los nuevos se verifican automáticamente en desarrollo.

## Deploy en Reflex Cloud

Panel: **[build.reflex.dev](https://build.reflex.dev/)**

### 1. Base de datos en la nube (obligatorio)

Reflex Cloud **no puede** usar tu PostgreSQL local (`localhost`). Necesitás una URL pública, por ejemplo:

- [Neon](https://neon.tech) (gratis para empezar)
- [Supabase](https://supabase.com)
- Otro PostgreSQL con acceso desde internet

Formato:

```env
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname?sslmode=require
```

### 2. Variables de entorno

```powershell
copy .env.production.example .env
```

Completá al menos:

| Variable | Valor |
|----------|--------|
| `DATABASE_URL` | URL PostgreSQL en la nube |
| `SEED_DEMO` | `false` |
| `APP_BASE_URL` | URL de la app tras el deploy (la actualizás después del primer deploy) |

Las demás (`GMAIL_*`) son opcionales.

### 3. Cuenta y proyecto en Reflex Cloud

1. Entrá a [build.reflex.dev](https://build.reflex.dev/) e iniciá sesión (GitHub o Gmail).
2. Creá un **Project** nuevo.
3. Copiá el **Project ID** y pegalo en `cloud.yml`:

```yaml
project: tu-project-id-aqui
```

### 4. Desplegar desde la terminal

```powershell
.\.venv\Scripts\Activate.ps1
reflex login
.\deploy.ps1
```

O manualmente:

```powershell
reflex deploy --config cloud.yml
```

El comando sube el código y carga los secretos desde `.env` (nunca commitees `.env`).

### 5. Después del deploy

1. En el panel de Reflex Cloud copiá la **URL pública** de la app.
2. Actualizá `APP_BASE_URL` en **Settings → Secrets** del proyecto (o en tu `.env` y volvé a desplegar).
3. Abrí la app y **creá la cuenta admin** (primer usuario registrado = administrador).

En producción no uses SQLite ni `SEED_DEMO=true`. La base incluida de Reflex Cloud no persiste datos entre reinicios.

## Estructura

```
polleria/
  models.py          Modelos PostgreSQL
  database.py        Creación de esquema
  auth/              Sesión, hashing y permisos
  services/          Ventas, inventario, reportes, seed
  states/            Estado de cada módulo
  components/        Layout y UI reutilizable
  pages/             Páginas
  polleria.py        App y rutas
```

## Permisos

Las pantallas ocultan acciones según el rol, pero **todas las operaciones sensibles se validan en backend**. Un vendedor no puede cambiar roles ni configuraciones administrativas.
