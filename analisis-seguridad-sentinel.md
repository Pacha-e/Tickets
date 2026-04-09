# Analisis de Seguridad - Sentinel-SoftServe FastAPI

## 1. Autenticacion utilizada

El proyecto utiliza **JWT (JSON Web Tokens) a traves de Supabase Auth** como mecanismo de autenticacion. La implementacion se encuentra en `Backend/auth.py`.

### Flujo de autenticacion completo

```
Frontend (React) --> Supabase Auth --> JWT Token --> Backend (FastAPI) --> Verificacion JWT
```

1. **Frontend**: El usuario ingresa email y password en `Login.jsx`. Se llama a `supabase.auth.signInWithPassword({ email, password })` que autentica contra Supabase.
2. **Supabase**: Emite un JWT firmado con HS256 o ES256.
3. **Backend**: Recibe el token en el header `Authorization: Bearer <token>` y lo valida en `auth.py`.

### Algoritmos soportados

El backend soporta **dos algoritmos de firma JWT**:

| Algoritmo | Tipo | Clave |
|-----------|------|-------|
| **HS256** | Simetrico | `SUPABASE_JWT_SECRET` (variable de entorno) |
| **ES256** | Asimetrico | Clave publica obtenida del endpoint JWKS de Supabase |

### Codigo clave (`Backend/auth.py`)

```python
bearer_scheme = HTTPBearer()

@lru_cache(maxsize=1)
def _get_supabase_public_key():
    response = requests.get(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", timeout=5)
    response.raise_for_status()
    keys = response.json().get("keys", [])
    return ECAlgorithm.from_jwk(keys[0])

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg == "HS256":
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"],
                             options={"verify_aud": False})
    else:
        public_key = _get_supabase_public_key()
        payload = jwt.decode(token, public_key, algorithms=["ES256"],
                             options={"verify_aud": False})
    return payload
```

---

## 2. Que se hizo para asegurar la FastAPI

### 2.1 Verificacion de JWT en el backend

- Se usa `PyJWT` (>=2.8.0) para decodificar y verificar tokens.
- Se valida la firma del token (HS256 o ES256), lo que asegura que no fue manipulado.
- Si el token es invalido o esta expirado, se lanza `HTTPException` con status `401 UNAUTHORIZED`.
- La clave publica de Supabase se cachea con `@lru_cache(maxsize=1)` para evitar llamadas HTTP repetidas al endpoint JWKS.

### 2.2 CORS (Cross-Origin Resource Sharing)

En `Backend/main.py` se configura CORS restrictivo:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Solo el frontend local
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **Solo se permite el origen** `http://localhost:5173` (el servidor de desarrollo de Vite/React).
- Esto previene que otros sitios web realicen requests al backend.

### 2.3 Validacion de datos con Pydantic

Se usan modelos Pydantic para validar la entrada de datos:

```python
class CreateIncidentManual(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    container_name: str = Field(..., min_length=1, max_length=100)
    severity: Literal["critical", "high", "medium", "low"]
    description: Optional[str] = Field(default=None, max_length=5000)
```

- **Longitudes maximas** para prevenir payloads excessivamente grandes.
- **Literal types** para restringir valores de `severity` a opciones validas.
- **Sanitizacion basica** con `.strip()` en los campos antes de insertarlos en la base de datos.

### 2.4 Esquema Bearer HTTP

Se utiliza `HTTPBearer()` de FastAPI, que:
- Automaticamente extrae el token del header `Authorization`.
- Rechaza requests sin token valido antes de llegar al endpoint.
- Genera documentacion OpenAPI con el esquema de seguridad.

### 2.5 Variables de entorno

- Secretos como `SUPABASE_JWT_SECRET`, `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` se cargan desde archivos `.env` con `python-dotenv`.
- El archivo `.env` esta en `.gitignore`, evitando que se suba al repositorio.

### 2.6 Separacion de claves (Frontend vs Backend)

| Lado | Clave usada | Privilegios |
|------|-------------|-------------|
| Frontend | `VITE_SUPABASE_ANON_KEY` | Solo lectura limitada (RLS) |
| Backend | `SUPABASE_SERVICE_KEY` | Acceso completo (admin) |

La clave de servicio (service role key) solo se usa en el backend, nunca se expone al cliente.

### 2.7 Rutas protegidas en el frontend

El componente `ProtectedRoute.jsx` protege el dashboard:

```javascript
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return children
}
```

- Si no hay usuario autenticado, redirige a `/login`.
- Las rutas no reconocidas redirigen a `/` (que requiere autenticacion).

---

## 3. Control de acceso en los REST endpoints

### Endpoints protegidos (requieren autenticacion)

Todos los endpoints en `Backend/routers/incidents.py` usan `Depends(get_current_user)`:

| Metodo | Ruta | Protegido | Descripcion |
|--------|------|-----------|-------------|
| `GET` | `/api/incidents/` | Si | Listar todos los incidentes |
| `GET` | `/api/incidents/{id}` | Si | Obtener un incidente especifico |
| `PATCH` | `/api/incidents/{id}/status` | Si | Actualizar estado de un incidente |
| `POST` | `/api/incidents/` | Si | Crear un incidente manual |

Ejemplo de como se aplica:
```python
@router.get("/")
async def list_incidents(user=Depends(get_current_user)):
    # Solo se ejecuta si el token JWT es valido
    ...
```

### Endpoint NO protegido (sin autenticacion)

| Metodo | Ruta | Protegido | Descripcion |
|--------|------|-----------|-------------|
| `POST` | `/api/alerts` | **NO** | Recibir webhooks de Alertmanager |
| `GET` | `/` | **NO** | Mensaje de bienvenida |
| `GET` | `/health` | **NO** | Health check |

El endpoint `/api/alerts` esta **intencionalmente abierto** porque recibe webhooks automaticos de Prometheus Alertmanager (comunicacion servicio-a-servicio dentro de la red Docker). Sin embargo, **no tiene ninguna validacion de origen ni firma del webhook**, lo que es un punto debil.

### Modelo de control de acceso

El control de acceso sigue un modelo **binario (autenticado vs. no autenticado)**:

- **No hay roles ni permisos diferenciados**: cualquier usuario autenticado puede realizar cualquier operacion (listar, crear, actualizar incidentes).
- **No hay RBAC (Role-Based Access Control)**: no existen roles como "admin", "viewer" u "operator".
- **No hay control de propiedad**: un usuario puede ver y modificar incidentes creados por otros usuarios.

### Resumen del flujo de control de acceso

```
Request entrante
    |
    v
[HTTPBearer] --> Extrae token del header Authorization
    |
    v
[get_current_user] --> Decodifica y verifica JWT
    |                   - Verifica firma (HS256/ES256)
    |                   - Verifica expiracion
    |
    v
[Token valido?]
    |-- NO --> 401 Unauthorized
    |-- SI --> Ejecuta la logica del endpoint
```

---

## 4. Observaciones y areas de mejora

| Area | Estado actual | Recomendacion |
|------|---------------|---------------|
| Autenticacion JWT | Implementada correctamente | Considerar habilitar `verify_aud` para mayor seguridad |
| CORS | Restringido a localhost | Actualizar para produccion con dominios reales |
| Endpoint `/api/alerts` | Sin autenticacion | Agregar validacion de firma o API key para webhooks |
| Control de roles | No implementado | Implementar RBAC para diferenciar permisos |
| Rate limiting | No implementado | Agregar limitacion de tasa para prevenir abuso |
| Auditoria | No implementada | Registrar quien realiza cada accion |
| `docker-compose.yml` | Credenciales hardcodeadas | Mover a secrets o vault (Grafana: `sentinel123`, Langfuse: credenciales visibles) |
| cAdvisor | Modo privilegiado | Evaluar si es estrictamente necesario |
