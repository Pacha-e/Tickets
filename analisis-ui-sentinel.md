# Analisis de UI - Routing, Shared State y Accesibilidad en Sentinel-SoftServe

## 1. Routing

### Tecnologia: React Router DOM v7

El enrutamiento se gestiona con `react-router-dom` v7.13.0, configurado en tres archivos clave:

### Estructura de rutas (`App.jsx`)

```javascript
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
  <Route path="*" element={<Navigate to="/" replace />} />
</Routes>
```

| Ruta | Componente | Proteccion | Proposito |
|------|-----------|------------|-----------|
| `/login` | `Login` | Publica | Inicio de sesion |
| `/` | `Dashboard` | `ProtectedRoute` | Panel principal |
| `*` | `Navigate` | N/A | Redireccion catch-all a `/` |

### Jerarquia de providers (`main.jsx`)

```
StrictMode
  └── BrowserRouter        ← Routing
       └── AuthProvider    ← Estado de autenticacion
            └── App        ← Rutas
```

`BrowserRouter` envuelve toda la aplicacion, lo que permite usar hooks de routing (`useNavigate`, `useSearchParams`) en cualquier componente.

### Proteccion de rutas (`ProtectedRoute.jsx`)

```javascript
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null           // Esperando verificacion
  if (!user) return <Navigate to="/login" replace />  // Sin sesion → login
  return children                    // Autenticado → mostrar contenido
}
```

- **Patron wrapper**: envuelve componentes hijos, no es un HOC.
- **`replace`**: usa `replace` en `Navigate` para no contaminar el historial del navegador.
- **Loading state**: retorna `null` mientras verifica la sesion, evitando flash de contenido no autorizado.

### Deep linking con URL params

El Dashboard usa `useSearchParams` para manejar la seleccion de incidentes via URL:

```javascript
const [searchParams, setSearchParams] = useSearchParams()
const selectedIncidentId = searchParams.get('incident')
```

Esto permite URLs como `/?incident=abc-123` que son compartibles y sobreviven recargas del navegador. Es una forma simple de deep linking sin necesidad de rutas anidadas.

### Valoracion del routing

**Fortalezas:**
- Simple y directo para una SPA de 2 vistas
- Deep linking de incidentes via query params
- Proteccion de rutas clara y desacoplada
- Catch-all evita paginas 404

**Debilidades:**
- No hay lazy loading (`React.lazy`) - todo se carga de golpe
- No hay rutas anidadas ni layouts compartidos
- No hay manejo de errores de ruta (error boundaries)
- Si la app crece, la estructura plana sera dificil de escalar

---

## 2. Shared State (Estado compartido)

### Estrategia: Context API + Supabase Realtime + Local State

El proyecto **no usa ninguna libreria de estado global** (ni Redux, ni Zustand, ni Jotai). Todo el estado se maneja con:

### 2.1 AuthContext - Estado de autenticacion (global)

```
AuthContext.Provider
  value = { user, loading, signIn, signUp, signOut }
```

| Propiedad | Tipo | Descripcion |
|-----------|------|-------------|
| `user` | object/null | Usuario autenticado de Supabase |
| `loading` | boolean | Estado de carga inicial de la sesion |
| `signIn` | function | Login con email/password |
| `signUp` | function | Registro |
| `signOut` | function | Cierre de sesion |

**Flujo de inicializacion:**
1. `getSession()` verifica si hay sesion activa al montar
2. `onAuthStateChange()` escucha cambios de sesion (login, logout, token refresh)
3. Se desuscribe al desmontar con `subscription.unsubscribe()`

**Consumo:** via `useAuth()` custom hook, que es simplemente:
```javascript
export function useAuth() {
  return useContext(AuthContext)
}
```

### 2.2 Dashboard - Estado de incidentes (local al componente)

Todo el estado de incidentes vive en `Dashboard.jsx` con `useState`:

```javascript
const [incidents, setIncidents] = useState([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)
const [showCreateModal, setShowCreateModal] = useState(false)
```

**No se comparte via Context** — el estado se pasa por props a subcomponentes inline (`SeverityBadge`, `StatusBadge`, etc.) que estan definidos dentro del mismo archivo.

### 2.3 Supabase Realtime - Sincronizacion en tiempo real

```javascript
const channel = supabase
  .channel('incidents-realtime')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'incidents' }, (payload) => {
    if (payload.eventType === 'INSERT') {
      setIncidents(prev => [...])
    } else if (payload.eventType === 'UPDATE') {
      setIncidents(prev => prev.map(...))
    } else if (payload.eventType === 'DELETE') {
      setIncidents(prev => prev.filter(...))
    }
  })
  .subscribe()
```

- Escucha INSERT, UPDATE y DELETE en la tabla `incidents`
- Actualiza el estado local inmediatamente sin re-fetch
- Se desuscribe al desmontar el componente
- Las notificaciones push se disparan en INSERT y UPDATE

### 2.4 Notificaciones - Hook custom (`useIncidentNotifications`)

Estado encapsulado en un hook dedicado que combina:
- `useState` para permisos y snooze
- `useCallback` para funciones memoizadas
- `localStorage` (via `incidentNotifications.js`) para persistir el snooze entre sesiones

### 2.5 Comunicacion con el backend

El frontend usa **dos canales de comunicacion** con el backend:

| Canal | Uso | Autenticacion |
|-------|-----|---------------|
| **Supabase Client directo** | Lectura de incidentes (`supabase.from('incidents').select(...)`) | Sesion Supabase (RLS) |
| **FastAPI REST** | Creacion de incidentes (`POST /api/incidents/`) | Bearer token JWT manual |

En `CreateIncidentModal.jsx`, el token se obtiene y envia manualmente:
```javascript
const { data: { session } } = await supabase.auth.getSession()
const response = await fetch(`${API_URL}/api/incidents/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${session.access_token}`,
  },
  body: JSON.stringify(payload),
})
```

### Valoracion del estado compartido

**Fortalezas:**
- Minimalista y facil de entender
- Realtime con Supabase evita polling
- Hook dedicado para notificaciones (separacion de concerns)
- Sin dependencias externas de estado (bundle pequeno)

**Debilidades:**
- Estado de incidentes no compartido — si se agregan mas paginas, habra que duplicar logica o moverlo a Context
- No hay capa de servicios centralizada para API calls (fetch manual en componentes)
- No hay cache de datos (cada mount del Dashboard re-fetches todo)
- No hay optimistic updates — depende de Realtime para reflejar cambios propios
- Mixing de canales (Supabase directo + FastAPI REST) puede causar inconsistencias

---

## 3. Accesibilidad (A11y)

### 3.1 Lo que SI se implemento

| Aspecto | Implementacion | Archivo |
|---------|----------------|---------|
| **`aria-label`** en boton cerrar | `aria-label="Cerrar"` y `aria-label="Cerrar detalle"` | `CreateIncidentModal.jsx`, `Dashboard.jsx` |
| **Cierre con Escape** | `useEffect` escuchando `keydown` para cerrar modal | `CreateIncidentModal.jsx` |
| **Labels en formularios** | `<label>` asociados a inputs con `htmlFor` implicito (label envuelve input) | `CreateIncidentModal.jsx`, `Login.jsx` |
| **Atributos `required`** | Campos obligatorios marcados con `required` | Formularios |
| **HTML5 email validation** | `type="email"` en el campo de correo | `Login.jsx` |
| **Texto semantico** | Headers `<h1>`, `<h2>`, `<header>` | `Dashboard.jsx` |
| **Indicadores visuales de estado** | Puntos de color con `animate-pulse` para estados criticos | `Dashboard.jsx` |

### 3.2 Lo que NO se implemento

| Aspecto faltante | Impacto | Severidad |
|------------------|---------|-----------|
| **`role="dialog"` y `aria-modal="true"`** en modales | Screen readers no identifican el modal como tal | Alta |
| **Focus trapping** en modales | El foco puede escapar al contenido detras del modal | Alta |
| **`aria-live` regions** | Los cambios realtime en la lista de incidentes no se anuncian | Media |
| **`role="alert"`** en errores | Los mensajes de error no se anuncian automaticamente | Media |
| **Skip navigation links** | No hay forma de saltar al contenido principal | Baja |
| **Focus management** al abrir/cerrar paneles | Al seleccionar un incidente, el foco no se mueve al detalle | Media |
| **Contrast ratio** sin verificar | El tema dark con colores como `text-slate-600` puede no cumplir WCAG AA (4.5:1) | Media |
| **Keyboard navigation** en lista de incidentes | Los items usan `<button>` (bien), pero no hay navegacion con flechas ni `aria-selected` | Baja |
| **`alt` text** | No hay imagenes, pero los iconos de estado son puramente visuales (dots) sin texto alternativo | Media |
| **Responsive / mobile** | No hay breakpoints `sm:` / `md:` en el header — los botones se desbordan en pantallas pequenas | Alta |

### 3.3 Responsive Design

El enfoque responsive es **limitado**:

```css
/* index.css - Solo una linea */
@import "tailwindcss";
```

No hay custom media queries. La responsividad depende unicamente de clases Tailwind inline:

| Elemento | Comportamiento responsive | Adecuado? |
|----------|--------------------------|-----------|
| Layout general | `min-h-screen flex flex-col` | Basico, OK |
| Panel lateral | `w-[420px]` fijo cuando hay seleccion | No responsive |
| Placeholder vacio | `hidden lg:flex` (solo visible en pantallas grandes) | Unico breakpoint usado |
| Header | `flex items-center justify-between px-8` | Se desborda en mobile |
| Modal | `max-w-md mx-4` | Adaptable, OK |
| Texto truncado | `truncate` en titulos | OK |

**Solo se usa un breakpoint (`lg:`) en todo el proyecto.** No hay vistas mobile-first ni adaptaciones para tablets.

### 3.4 Herramientas de accesibilidad

- **No hay libreria de a11y** en las dependencias (`react-aria`, `radix-ui`, `headlessui`, etc.)
- **No hay `axe-core`** ni pruebas automatizadas de accesibilidad
- **No hay ESLint plugin** de accesibilidad (`eslint-plugin-jsx-a11y`)

### Valoracion de accesibilidad

**Score estimado: ~40/100 (WCAG 2.1 AA)**

El proyecto tiene los elementos basicos (labels, botones semanticos, aria-labels puntuales), pero le faltan patrones criticos para accesibilidad real: focus management, ARIA roles en modales, live regions para contenido dinamico, y responsive design para mobile.

---

## 4. Resumen ejecutivo

| Dimension | Enfoque | Madurez | Escalabilidad |
|-----------|---------|---------|---------------|
| **Routing** | React Router v7, 2 rutas + proteccion | Funcional | Baja (plano) |
| **Shared State** | Context API + Supabase Realtime | Funcional | Media (sin cache, sin capa de servicios) |
| **Accesibilidad** | Basica (labels, escape key) | Minima | Baja (sin framework a11y) |
| **Responsive** | Tailwind sin breakpoints | Insuficiente | Baja (desktop-only) |

El frontend esta disenado para funcionar como un dashboard de escritorio de uso interno. Es mantenible en su escala actual (2 vistas, 2 componentes, 1 hook), pero necesitaria refactorizacion significativa para crecer (mas vistas, mobile support, multi-usuario con roles).
