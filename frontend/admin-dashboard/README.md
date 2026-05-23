# 🎨 Admin Dashboard - Frontend

Dashboard web para que dueños de tiendas gestionen sus negocios.

## 🚀 Quick Start

```bash
# 1. Instalar dependencias
npm install

# 2. Configurar API URL (opcional)
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local

# 3. Iniciar desarrollo
npm run dev

# 4. Abrir navegador
# http://localhost:3001
```

## 📁 Estructura Actual

```
admin-dashboard/
├── package.json          ✅ Configuración
├── tsconfig.json         ✅ TypeScript
├── tailwind.config.js    ✅ Tailwind CSS
├── next.config.js        ✅ Next.js
├── lib/
│   ├── api.ts           ✅ Cliente API completo
│   └── store.ts         ✅ State management (Zustand)
├── app/
│   ├── layout.tsx       ✅ Layout principal
│   ├── globals.css      ✅ Estilos globales
│   ├── page.tsx         ⏳ Login (crear)
│   └── dashboard/       ⏳ Dashboard pages (crear)
└── components/          ⏳ Componentes (crear)
```

## ✅ Lo que está implementado

### 1. Cliente API Completo (`lib/api.ts`)

**Métodos disponibles:**

```typescript
// Auth
api.login(email, password)
api.getMe()
api.changePassword(current, new)
api.logout()

// Restaurant
api.getRestaurant(restaurantId)
api.getRestaurantStats(restaurantId)
api.updateRestaurant(restaurantId, updates)

// Products
api.getProducts(restaurantId)
api.createProduct(restaurantId, product)
api.updateProduct(restaurantId, productId, updates)
api.deleteProduct(restaurantId, productId)
api.updateStock(restaurantId, productId, quantity, operation)

// Categories
api.getCategories(restaurantId)
api.createCategory(restaurantId, category)
api.updateCategory(restaurantId, categoryId, updates)
api.deleteCategory(restaurantId, categoryId)

// Orders
api.getOrders(restaurantId)
api.getOrder(restaurantId, orderId)
api.updateOrderStatus(restaurantId, orderId, status)
api.getOrdersStats(restaurantId, period)
api.cancelOrder(restaurantId, orderId, reason)

// Customers
api.getCustomers(restaurantId)
api.getCustomer(restaurantId, phone)
api.getCustomerOrders(restaurantId, phone)
api.getCustomerLoyalty(restaurantId, phone)
api.getCustomersStats(restaurantId)
```

### 2. State Management (`lib/store.ts`)

```typescript
import { useAuthStore } from '@/lib/store';

// En componentes:
const { user, isAuthenticated, setUser, logout } = useAuthStore();
```

### 3. Configuración

- ✅ Next.js 14 (App Router)
- ✅ TypeScript
- ✅ Tailwind CSS
- ✅ Axios para HTTP
- ✅ Zustand para estado
- ✅ React Hook Form
- ✅ Lucide React (iconos)

## ⏳ Lo que falta crear

### Páginas:
1. **Login** (`app/page.tsx`)
2. **Dashboard Home** (`app/dashboard/page.tsx`)
3. **Productos** (`app/dashboard/products/page.tsx`)
4. **Órdenes** (`app/dashboard/orders/page.tsx`)
5. **Clientes** (`app/dashboard/customers/page.tsx`)
6. **Configuración** (`app/dashboard/settings/page.tsx`)

### Componentes:
1. **Navbar** - Menú de navegación
2. **ProductForm** - Crear/editar producto
3. **OrderCard** - Tarjeta de orden
4. **StatsCard** - Tarjetas de estadísticas
5. **Table** - Tabla reutilizable

## 🎯 Próximo paso

Para continuar, necesitamos crear:

1. **Página de Login** con formulario
2. **Layout del Dashboard** con sidebar
3. **Dashboard Home** con estadísticas
4. **Gestión de Productos** con CRUD completo

¿Quieres que continúe creando estas páginas?

## 📝 Notas

- El cliente API ya está completo y listo para usar
- Solo falta crear las páginas UI
- Tiempo estimado: 2-3 horas para páginas básicas
