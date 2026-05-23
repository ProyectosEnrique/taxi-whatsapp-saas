# Guía para Generar Iconos PWA

## Opción 1: Usar herramientas online (Recomendado)

### PWA Builder
1. Ve a https://www.pwabuilder.com/imageGenerator
2. Sube un logo o imagen (mínimo 512x512px)
3. Selecciona "Generate ZIP"
4. Descarga el ZIP
5. Extrae y copia los archivos:
   - `icon-192x192.png` → `frontend/driver-app/public/icons/`
   - `icon-512x512.png` → `frontend/driver-app/public/icons/`

### RealFaviconGenerator
1. Ve a https://realfavicongenerator.net/
2. Sube tu imagen (PNG, JPG, SVG)
3. Configura opciones:
   - Android Chrome: 192x192 y 512x512
   - iOS: 180x180
   - Color de tema: #FDB813 (driver), #10B981 (customer), #3B82F6 (admin)
4. Genera y descarga
5. Copia a las carpetas correspondientes

## Opción 2: Usar ImageMagick (Local)

```bash
# Instalar ImageMagick
# Windows: choco install imagemagick
# Mac: brew install imagemagick
# Linux: sudo apt install imagemagick

# Generar iconos desde una imagen base
convert logo.png -resize 192x192 icon-192x192.png
convert logo.png -resize 512x512 icon-512x512.png
```

## Opción 3: Iconos genéricos temporales (para pruebas)

Si no tienes un logo aún, puedes usar estos emojis como placeholder:

**Driver App**: 🚕 (emoji de taxi)
**Customer App**: 📱 (emoji de teléfono)
**Admin Panel**: 📊 (emoji de gráficos)

Para convertir emoji a PNG:
1. Ve a https://emoji.gg/
2. Busca el emoji
3. Descarga en alta resolución
4. Redimensiona a 192x192 y 512x512

## Colores de Tema por App

- **Driver App**: #FDB813 (amarillo taxi)
- **Customer App**: #10B981 (verde)
- **Admin Panel**: #3B82F6 (azul)

## Estructura de archivos requerida

```
frontend/driver-app/public/
├── icons/
│   ├── icon-192x192.png
│   └── icon-512x512.png
└── favicon.ico (opcional)

frontend/taxi-customer-app/public/
├── icons/
│   ├── icon-192x192.png
│   └── icon-512x512.png
└── favicon.ico (opcional)

frontend/admin-panel/public/
├── icons/
│   ├── icon-192x192.png
│   └── icon-512x512.png
└── favicon.ico (opcional)
```

## Verificar instalación

Después de copiar los iconos:

1. Rebuild la app: `npm run build`
2. Servir: `npm run preview`
3. Abrir Chrome DevTools → Application → Manifest
4. Verificar que los iconos aparecen correctamente
