import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Admin Dashboard - WhatsApp SAAS',
  description: 'Gestiona tu tienda desde un solo lugar',
}

export default function RootLayout({
  children,
}: {
  children: React.Node
}) {
  return (
    <html lang="es">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
