# Customer Web App - Pedidos en Línea

Aplicación web progresiva (PWA) para que los clientes realicen pedidos en línea. Diseñada para funcionar con el sistema multi-tenant del backend.

## 🚀 Características

### ✅ FASE 1 - IMPLEMENTADO
- **Vista de Menú**: Navegación por categorías, búsqueda de productos
- **Carrito de Compras**: Agregar/quitar productos, modificar cantidades, cálculo automático
- **Multi-Tenant**: Detección automática del tenant por URL o configuración

### ⏳ FASE 2 - POR IMPLEMENTAR
- **Autenticación**: Registro, login, perfil de usuario
- **Direcciones**: Gestión de direcciones de entrega
- **Historial**: Ver pedidos anteriores con detalles
- **Tracking**: Seguimiento de pedidos en tiempo real

### ⏳ FASE 3 - POR IMPLEMENTAR
- **Promociones**: Ver y aplicar códigos promocionales
- **Reseñas**: Calificar pedidos y productos
- **Programa de Lealtad**: Acumular y canjear puntos

## 🛠️ Tecnologías

- **Vue 3** - Framework progresivo
- **Vite** - Build tool ultrarrápido
- **Vue Router** - Navegación SPA
- **Pinia** - State management
- **Tailwind CSS** - Estilos utility-first
- **Axios** - HTTP client
- **Socket.IO Client** - Tracking en tiempo real

## 📦 Instalación

### Desarrollo Local

```bash
# Instalar dependencias
npm install

# Copiar variables de entorno
cp .env.example .env

# Editar .env con tu configuración
# VITE_API_URL=http://localhost:5000
# VITE_TENANT_ID=default (opcional)

# Iniciar servidor de desarrollo
npm run dev

# La app estará disponible en http://localhost:3000
```

### Build de Producción

```bash
# Compilar para producción
npm run build

# Preview del build
npm run preview
```

### Docker

```bash
# Build de la imagen
docker build -t customer-app .

# Ejecutar container
docker run -p 3000:80 customer-app
```

### Docker Compose (Proyecto completo)

```bash
# Desde la raíz del proyecto
cd PROYECTO_B_WHATSAPP_SAAS

# Iniciar todos los servicios (incluye customer-app)
docker-compose up -d

# Customer app estará en: http://localhost:3000
# Admin panel estará en: http://localhost:8080
# Backend API estará en: http://localhost:5000
```

## 🏗️ Estructura del Proyecto

```
customer-app/
├── src/
│   ├── components/          # Componentes reutilizables
│   │   ├── layout/          # Header, Footer
│   │   ├── cart/            # CartSidebar
│   │   ├── products/        # ProductCard
│   │   └── common/          # NotificationsToast, etc.
│   │
│   ├── views/               # Vistas principales (páginas)
│   │   ├── MenuView.vue     # ✅ Implementado
│   │   ├── CheckoutView.vue # ⏳ Por implementar
│   │   ├── LoginView.vue    # ⏳ Por implementar
│   │   └── ...
│   │
│   ├── stores/              # Pinia stores
│   │   ├── tenant.js        # ✅ Multi-tenant
│   │   ├── cart.js          # ✅ Carrito
│   │   ├── auth.js          # ✅ Autenticación
│   │   ├── orders.js        # ✅ Pedidos
│   │   ├── promotions.js    # ✅ Promociones
│   │   ├── reviews.js       # ✅ Reseñas
│   │   └── loyalty.js       # ✅ Puntos
│   │
│   ├── router/              # Vue Router
│   │   └── index.js         # ✅ Rutas configuradas
│   │
│   ├── services/            # Servicios API
│   │   └── api.js           # ✅ Cliente HTTP
│   │
│   ├── styles/              # Estilos globales
│   │   └── main.css         # ✅ Tailwind + custom
│   │
│   ├── App.vue              # ✅ Componente raíz
│   └── main.js              # ✅ Entry point
│
├── public/                  # Archivos estáticos
├── index.html               # ✅ HTML template
├── vite.config.js           # ✅ Configuración Vite
├── tailwind.config.js       # ✅ Configuración Tailwind
├── Dockerfile               # ✅ Docker para producción
├── nginx.conf               # ✅ Nginx config
└── package.json             # ✅ Dependencias
```

## 🔧 Configuración Multi-Tenant

La app detecta automáticamente el tenant de 3 formas:

### 1. Variable de Entorno (Desarrollo)
```env
VITE_TENANT_ID=tenant_wine_001
```

### 2. Query Parameter (URL)
```
http://localhost:3000?tenant=tenant_pharmacy_001
```

### 3. Por Defecto
Si no se especifica, usa el tenant `default`

## 🎨 Personalización por Tenant

Cada tenant puede tener su propio:
- **Nombre y Logo**
- **Colores (branding)**
- **Mensaje de bienvenida**
- **Productos**
- **Reglas de negocio** (envío, monto mínimo, etc.)

Esto se configura desde el backend en `config/tenants.json` o Firestore.

## 📱 Responsive Design

La aplicación está optimizada para:
- 📱 **Mobile** (320px+)
- 📱 **Tablet** (768px+)
- 💻 **Desktop** (1024px+)

Usa Tailwind CSS con clases responsive:
```vue
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
  <!-- Se adapta automáticamente -->
</div>
```

## 🔐 Autenticación (FASE 2)

El sistema usa JWT tokens:
1. Login/Register envía credenciales
2. Backend retorna token JWT
3. Token se guarda en localStorage
4. Token se incluye en todas las requests (Authorization header)

## 📡 API Endpoints

### Tenant
- `GET /api/tenants/:id` - Info del tenant
- `GET /api/tenants/:id/products` - Productos del tenant

### Orders
- `POST /api/orders` - Crear pedido
- `GET /api/orders` - Listar pedidos del usuario
- `GET /api/orders/:id` - Detalles de pedido
- `POST /api/orders/:id/cancel` - Cancelar pedido

### Auth (FASE 2)
- `POST /api/auth/register` - Registro
- `POST /api/auth/login` - Login
- `GET /api/auth/profile` - Perfil del usuario

### Promotions (FASE 3)
- `GET /api/promotions` - Listar promociones
- `POST /api/promotions/validate` - Validar código

Ver `src/services/api.js` para todos los endpoints.

## 🧪 Testing (Por implementar)

```bash
# Unit tests
npm run test:unit

# E2E tests
npm run test:e2e
```

## 🚢 Deployment

### Netlify / Vercel
1. Conectar repositorio
2. Build command: `npm run build`
3. Publish directory: `dist`
4. Variables de entorno: `VITE_API_URL`, `VITE_SOCKET_URL`

### Firebase Hosting
```bash
firebase deploy --only hosting:customer-app
```

### Cloud Run (con Docker)
```bash
gcloud run deploy customer-app \
  --source . \
  --platform managed \
  --region us-central1
```

## 🐛 Troubleshooting

### El menú no carga
- Verificar que el backend esté corriendo en `VITE_API_URL`
- Verificar que el tenant_id exista en el backend
- Revisar console del navegador para errores

### Carrito no funciona
- Verificar que localStorage esté habilitado
- Limpiar localStorage: `localStorage.clear()`

### Multi-tenant no funciona
- Verificar `.env` o query param `?tenant=`
- Verificar que el tenant exista en el backend

## 📝 Tareas Pendientes

Ver archivo `CUSTOMER_APP_IMPLEMENTACION.md` para lista completa de tareas pendientes por fase.

## 📄 Licencia

Parte del proyecto PROYECTO_B_WHATSAPP_SAAS
