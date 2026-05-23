'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import {
  Package,
  ShoppingCart,
  Users,
  DollarSign,
  TrendingUp,
  Clock
} from 'lucide-react'

export default function DashboardPage() {
  const user = useAuthStore(state => state.user)
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    if (!user?.restaurant_id) return

    try {
      const data = await api.getRestaurantStats(user.restaurant_id)
      setStats(data)
    } catch (error: any) {
      console.error('Error loading stats:', error)
      setError('Error al cargar estadísticas')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Bienvenido de vuelta, {user?.email}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Productos"
          value={stats?.total_products || 0}
          icon={Package}
          color="blue"
          trend="+12%"
        />
        <StatCard
          title="Órdenes Hoy"
          value={stats?.orders_today || 0}
          icon={ShoppingCart}
          color="green"
          trend="+8%"
        />
        <StatCard
          title="Clientes"
          value={stats?.total_customers || 0}
          icon={Users}
          color="purple"
          trend="+23%"
        />
        <StatCard
          title="Ventas Hoy"
          value={`$${stats?.sales_today || 0}`}
          icon={DollarSign}
          color="yellow"
          trend="+15%"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <QuickActionCard
          title="Agregar Producto"
          description="Añade nuevos productos a tu catálogo"
          href="/dashboard/products"
          icon={Package}
          color="blue"
        />
        <QuickActionCard
          title="Ver Órdenes"
          description="Gestiona las órdenes pendientes"
          href="/dashboard/orders"
          icon={ShoppingCart}
          color="green"
        />
        <QuickActionCard
          title="Ver Clientes"
          description="Administra tu base de clientes"
          href="/dashboard/customers"
          icon={Users}
          color="purple"
        />
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Orders */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Órdenes Recientes</h2>
            <Clock className="h-5 w-5 text-gray-400" />
          </div>
          <div className="space-y-3">
            <p className="text-sm text-gray-500">No hay órdenes recientes</p>
          </div>
        </div>

        {/* Top Products */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Productos Más Vendidos</h2>
            <TrendingUp className="h-5 w-5 text-gray-400" />
          </div>
          <div className="space-y-3">
            <p className="text-sm text-gray-500">Datos disponibles próximamente</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, icon: Icon, color, trend }: any) {
  const colorClasses = {
    blue: {
      bg: 'bg-blue-50',
      text: 'text-blue-700',
      icon: 'text-blue-600'
    },
    green: {
      bg: 'bg-green-50',
      text: 'text-green-700',
      icon: 'text-green-600'
    },
    purple: {
      bg: 'bg-purple-50',
      text: 'text-purple-700',
      icon: 'text-purple-600'
    },
    yellow: {
      bg: 'bg-yellow-50',
      text: 'text-yellow-700',
      icon: 'text-yellow-600'
    },
  }

  const colors = colorClasses[color] || colorClasses.blue

  return (
    <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {trend && (
            <p className="text-sm text-green-600 mt-2 flex items-center">
              <TrendingUp className="h-4 w-4 mr-1" />
              {trend}
            </p>
          )}
        </div>
        <div className={`${colors.bg} p-3 rounded-lg`}>
          <Icon className={`h-8 w-8 ${colors.icon}`} />
        </div>
      </div>
    </div>
  )
}

function QuickActionCard({ title, description, href, icon: Icon, color }: any) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700',
    green: 'from-green-500 to-green-600 hover:from-green-600 hover:to-green-700',
    purple: 'from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700',
  }

  const gradient = colorClasses[color] || colorClasses.blue

  return (
    <a
      href={href}
      className={`block bg-gradient-to-br ${gradient} text-white rounded-lg shadow-md p-6 hover:shadow-lg transition-all transform hover:-translate-y-1`}
    >
      <Icon className="h-8 w-8 mb-4" />
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm opacity-90">{description}</p>
    </a>
  )
}
