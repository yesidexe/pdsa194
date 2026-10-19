# Configuración y seguridad

> Para la demo no necesitas este documento. La aplicación arranca con valores locales por defecto.

## 1. El archivo `.env`

`.env.example` es la plantilla pública del repositorio. Contiene todas las variables; las opcionales están comentadas. `.env` es tu copia local y está ignorada por Git.

Si no existe `.env`, la aplicación usa los valores por defecto. Para crear uno:

```bash
cp .env.example .env
```

Edita `.env` si necesitas cambiar algo. Los cambios requieren reiniciar la aplicación.

## 2. Variables disponibles

### Variables principales

| Variable | Valor por defecto | Qué hace |
|---|---|---|
| `ADMIN_USER` | `admin` | Usuario del panel administrador. |
| `ADMIN_PASSWORD` | `admin1234` | Contraseña en texto plano. Se ignora si existe `ADMIN_PASSWORD_HASH`. |
| `SECRET_KEY` | Aleatoria si no se define | Firma la sesión del administrador. [Ver explicación](#4-secret_key). **No cifra los votos.** |
| `SESSION_MAX_AGE_SECONDS` | `28800` | Duración de la sesión desde el inicio de sesión. `28800` = 8 horas. Al vencer, hay que iniciar sesión otra vez. |
| `AUTO_OPEN_POLLS` | `true` | Abre la urna automáticamente al arrancar. Si es `false`, se abre desde el panel. |
| `DEV_RELOAD` | `false` | Reinicia el servidor al cambiar archivos `.py`. Solo aplica con `python3 -m src.main`. [Ver explicación](#5-uvicorn-y-dev_reload). |
| `HOST` | `127.0.0.1` | Dirección donde escucha el servidor. Solo aplica con `python3 -m src.main`. |
| `PORT` | `8000` | Puerto del servidor. Solo aplica con `python3 -m src.main`. |

### Variables opcionales

| Variable | Qué hace |
|---|---|
| `ADMIN_PASSWORD_HASH` | Huella PBKDF2 de la contraseña. Si existe, reemplaza a `ADMIN_PASSWORD`. [Ver explicación](#3-admin_password_hash). |
| `DATABASE_URL` | URL de conexión de SQLAlchemy. Por defecto usa SQLite en `e_voting.db`, en la raíz del proyecto. |
| `ELECTION_MODE` | Modalidad inicial: `national` o `university`. Por defecto, `national`. |

Las variables opcionales pueden quedarse comentadas; la aplicación usa sus valores por defecto.

## 3. `ADMIN_PASSWORD_HASH`

`ADMIN_PASSWORD_HASH` es una huella de la contraseña del administrador, no la contraseña. Se genera con PBKDF2-SHA256 y no se puede convertir de vuelta a la contraseña. Sirve para no guardar la contraseña en texto plano.

La sal es un valor aleatorio que se guarda junto al hash. Las repeticiones hacen el cálculo lento a propósito, para dificultar los ataques de fuerza bruta.

Si `ADMIN_PASSWORD_HASH` está definido, el servidor lo usa e **ignora `ADMIN_PASSWORD`**. Si no está definido, usa `ADMIN_PASSWORD` en texto plano. No es una firma ni tiene relación con `SECRET_KEY`: solo comprueba la contraseña al iniciar sesión.

### Cómo generarlo

1. Ejecuta:

```bash
./venv/bin/python scripts/hash_password.py "mi-nueva-contraseña"
```

2. Copia el resultado completo. Se ve como `sal$huella`, no como la contraseña.

3. En `.env`, define:

```env
ADMIN_PASSWORD_HASH=el_resultado_del_comando
```

4. Comenta o elimina `ADMIN_PASSWORD` para no dejar la contraseña en texto plano. Reinicia la aplicación.

El hash se lee de `.env` al arrancar y no se guarda en la base de datos. Si el hash está mal formado, el inicio de sesión falla.

## 4. `SECRET_KEY`

`SECRET_KEY` es una clave secreta del servidor. Se usa para firmar la sesión del administrador; no cifra los votos, no es la contraseña y no es la firma de los jurados.

Cuando el administrador inicia sesión, el servidor crea una credencial con `admin:<hora de vencimiento>`, le calcula una firma con `SECRET_KEY` y la guarda en una **cookie**: un dato que el navegador guarda y envía en cada petición. En cada petición, el servidor comprueba la firma y la hora.

HMAC-SHA256 es una firma con clave: detecta si el contenido cambió, pero no lo cifra.

Cada inicio de sesión genera una firma distinta porque cambia la hora de vencimiento. No es una firma personal del administrador: es la firma del servidor sobre esa sesión. Solo hay una cuenta de administrador.

`SECRET_KEY` no usa la cédula del administrador. Si alguien conoce la clave, puede fabricar una credencial válida; por eso debe mantenerse privada.

- Si la clave está fija, las sesiones sobreviven a los reinicios hasta su vencimiento.
- Si la cambias, las sesiones abiertas dejan de ser válidas.
- Si falta, se genera una clave aleatoria en cada arranque.
- Si copias `.env.example`, cambia el valor de ejemplo por una clave real.

Con el valor por defecto, la sesión vence 8 horas después del inicio de sesión, no por inactividad. Al vencer, hay que iniciar sesión otra vez; no se pierden votos ni datos.

### Cómo cambiarla

Genera una clave:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Cópiala en `.env`:

```env
SECRET_KEY=la_cadena_que_imprimio_el_comando
```

Reinicia la aplicación y vuelve a entrar. No pongas la clave en `settings.py` ni en otro archivo de código: `.env` se lee al arrancar.

> Las "firmas de jurados" del acta son códigos fijos de la simulación; no usan `SECRET_KEY` ni se guardan en la base de datos.

## 5. Uvicorn y `DEV_RELOAD`

Uvicorn es el servidor que mantiene la aplicación encendida y escuchando en el puerto. FastAPI define las rutas; Uvicorn recibe las peticiones.

Arranca la demo con:

```bash
python3 -m src.main
```

Ese comando usa `HOST`, `PORT` y `DEV_RELOAD` de `.env`.

Si ejecutas `uvicorn src.main:app --host ... --port ...` directamente, esos valores de `.env` no se usan; mandan los argumentos del comando.

`DEV_RELOAD=true` reinicia el servidor cuando guardas un archivo `.py`. No recarga solo el frontend: reinicia el backend completo. Es útil para desarrollar, pero para la demo déjalo en `false`: al reiniciar se pierde el estado en memoria (por ejemplo, si la urna estaba cerrada) y, con `AUTO_OPEN_POLLS=true`, la urna se vuelve a abrir. Los votos guardados en la base no se pierden.

## 6. Scripts de apoyo

Son opcionales. Ejecútalos desde la raíz con el entorno virtual activo y, preferiblemente, con la aplicación detenida.

- `reset_db.py`: borra votos, participaciones y censo, y vuelve a sembrar el censo sintético. La base queda **sin votos, pero con las personas de demostración**.
- `cast_demo_votes.py`: usa el censo existente y emite votos de prueba con el flujo de la cabina. **No agrega personas.** Rota entre los candidatos y cada sexto elector vota en blanco.
- `hash_password.py`: genera el hash para `ADMIN_PASSWORD_HASH`. No toca la base.

Para una demo limpia:

```bash
./venv/bin/python scripts/reset_db.py
./venv/bin/python scripts/cast_demo_votes.py
python3 -m src.main
```

Para modo universitario:

```bash
ELECTION_MODE=university ./venv/bin/python scripts/cast_demo_votes.py
```

> `reset_db.py` no es lo mismo que **Reiniciar jornada**: el botón conserva el censo; el script lo borra y lo vuelve a sembrar.

## 7. Seguridad para la demo

- Usa solo datos sintéticos.
- `HOST=127.0.0.1` limita el acceso a tu equipo. No uses `0.0.0.0` sin TLS y protecciones adicionales.
- Si vas a exponer la aplicación fuera de tu computador, cambia la contraseña (mejor con `ADMIN_PASSWORD_HASH`) y `SECRET_KEY`.

Para el recorrido completo de la plataforma, consulta el [manual de uso](manual_de_uso.md).
