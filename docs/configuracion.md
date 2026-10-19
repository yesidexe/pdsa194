# Configuración y seguridad

> Para la demo no necesitas este documento. La aplicación arranca con valores locales por defecto.

## 1. El archivo `.env`

- `.env.example` es la plantilla pública que está en el repositorio.
- `.env` es tu configuración local y está ignorado por Git.
- Si no existe `.env`, la aplicación usa valores por defecto.
- Los cambios en `.env` requieren reiniciar la aplicación.

Para crear tu archivo local:

```bash
cp .env.example .env
```

El cargador es sencillo: una variable por línea, con la forma `CLAVE=valor`. Los comentarios van en su propia línea, comenzando con `#`. Si una variable ya existe en el entorno del sistema, esa tiene prioridad sobre `.env`.

## 2. Variables disponibles

### Variables principales

| Variable | Valor por defecto | Qué hace |
|---|---|---|
| `APP_ENV` | `local` | Etiqueta del entorno. **Hoy no cambia el comportamiento de la aplicación.** |
| `ADMIN_USER` | `admin` | Usuario del panel administrador. |
| `ADMIN_PASSWORD` | `admin1234` | Contraseña del administrador en texto plano. Se ignora si existe `ADMIN_PASSWORD_HASH`. |
| `SECRET_KEY` | Se genera aleatoriamente si falta | Firma la cookie de sesión del administrador con HMAC-SHA256. **No cifra los votos.** |
| `SESSION_MAX_AGE_SECONDS` | `28800` | Duración de la sesión del administrador. `28800` segundos = 8 horas. |
| `AUTO_OPEN_POLLS` | `true` | Abre la urna automáticamente al arrancar. Si es `false`, el administrador debe abrirla desde el panel. |
| `DEV_RELOAD` | `false` | Recarga automática de Uvicorn al cambiar el código. Solo aplica con `python3 -m src.main`. |
| `HOST` | `127.0.0.1` | Dirección donde escucha el servidor. Solo aplica con `python3 -m src.main`. |
| `PORT` | `8000` | Puerto del servidor. Solo aplica con `python3 -m src.main`. |

### Variables opcionales

| Variable | Qué hace |
|---|---|
| `ADMIN_PASSWORD_HASH` | Hash PBKDF2 de la contraseña. Si existe, reemplaza a `ADMIN_PASSWORD`. |
| `DATABASE_URL` | Ruta de la base de datos. Por defecto usa `e_voting.db` en la raíz del proyecto. |
| `ELECTION_MODE` | Modalidad inicial: `national` o `university`. Por defecto, `national`. |

## 3. Cambiar la contraseña del administrador

### Opción simple

Edita `.env`:

```env
ADMIN_PASSWORD=mi-nueva-contraseña
```

Reinicia la aplicación y entra con el usuario `admin` y esa contraseña.

Si tienes `ADMIN_PASSWORD_HASH` definido, elimínalo o coméntalo; el hash tiene prioridad.

### Opción con hash

Genera el hash:

```bash
./venv/bin/python scripts/hash_password.py "mi-nueva-contraseña"
```

Copia el resultado en `.env`:

```env
ADMIN_PASSWORD_HASH=el_resultado_del_comando
```

Elimina o comenta `ADMIN_PASSWORD` para no dejar la contraseña en texto plano. Reinicia la aplicación.

## 4. `SECRET_KEY`

`SECRET_KEY` es la clave con la que el servidor firma la cookie del administrador. La cookie contiene algo como `admin:<fecha de expiración>` y una firma HMAC-SHA256. En cada petición, el servidor comprueba que la firma sea válida.

En corto:

- **No cifra los votos.**
- **No cifra la base de datos.**
- **No es la contraseña del administrador.**
- **Sirve para que nadie falsifique una sesión de administrador.**

Si alguien conoce `SECRET_KEY`, puede fabricar una cookie de administrador válida. Por eso debe mantenerse privada.

### Qué pasa si la cambias

- Las sesiones de administrador abiertas dejan de ser válidas.
- Tienes que volver a iniciar sesión.
- No se pierden votos, censo ni resultados.
- El cambio no se aplica hasta reiniciar la aplicación.

Si `SECRET_KEY` no está definida, el sistema genera una clave aleatoria nueva en cada arranque. En local funciona, pero cada reinicio invalida las sesiones anteriores.

### Cómo cambiarla

1. Genera una clave nueva:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

2. Copia la cadena que aparece en la terminal.

3. Abre `.env` y busca la línea:

```env
SECRET_KEY=cambia-esta-clave-por-una-aleatoria
```

4. Reemplaza toda la línea por:

```env
SECRET_KEY=la_cadena_que_imprimio_el_comando
```

Debe quedar una sola línea `SECRET_KEY`, sin comillas y sin espacios alrededor del `=`.

5. Guarda `.env` y reinicia la aplicación:

```bash
python3 -m src.main
```

6. Vuelve a entrar al panel con `admin` y tu contraseña.

No pegues la clave en `settings.py` ni en otro archivo de código: el archivo `.env` se lee automáticamente al arrancar.

## 5. Uvicorn y `DEV_RELOAD`

Uvicorn es el servidor web que ejecuta FastAPI. FastAPI define las rutas; Uvicorn escucha en un puerto y recibe las peticiones HTTP.

La forma recomendada para la demo es:

```bash
python3 -m src.main
```

Ese comando ya arranca Uvicorn internamente y usa `HOST`, `PORT` y `DEV_RELOAD` de `.env`.

La alternativa directa es:

```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

En ese caso, `HOST`, `PORT` y `DEV_RELOAD` de `.env` se ignoran; mandan los argumentos de Uvicorn. Si quieres recarga automática con este comando, añade `--reload`.

`DEV_RELOAD=true` reinicia el servidor cada vez que guardas un archivo `.py`. Es útil para desarrollar, pero para una demo es mejor `false`, porque al reiniciar se pierde el estado en memoria y, si `AUTO_OPEN_POLLS=true`, la urna se vuelve a abrir.

## 6. Seguridad para la demo

- Usa solo datos sintéticos; no cargues datos personales reales.
- `HOST=127.0.0.1` limita el acceso a tu equipo. No uses `0.0.0.0` sin TLS y protecciones adicionales.
- Si vas a exponer la aplicación fuera de tu computador, cambia `ADMIN_PASSWORD` y `SECRET_KEY`.
- `APP_ENV=production` no activa protecciones adicionales; hoy es solo una etiqueta.

Para el recorrido completo de la plataforma, consulta el [manual de uso](manual_de_uso.md).
