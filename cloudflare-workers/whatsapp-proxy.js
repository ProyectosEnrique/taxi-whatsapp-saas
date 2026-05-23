// ================================================================================
// CLOUDFLARE WORKER - WHATSAPP WEBHOOK PROXY
// ================================================================================
// Proxy seguro para webhooks de WhatsApp con protección DDoS y rate limiting
// Beneficios:
//   - DDoS protection automático de Cloudflare
//   - Edge caching global
//   - Rate limiting integrado
//   - Analytics y logging
// ================================================================================

// Backend URL - Actualizar después del deployment
const BACKEND_URL = 'https://whatsapp-gateway-XXXXXXXXXX-uc.a.run.app';

// Rate limiting configuration (opcional)
const RATE_LIMIT = {
  enabled: true,
  requestsPerMinute: 60,
  burstSize: 10
};

// Allowed origins for CORS (opcional)
const ALLOWED_ORIGINS = [
  'https://whatsapp-saas-prod.web.app',
  'https://whatsapp-saas-prod.firebaseapp.com'
];

/**
 * Main handler for incoming requests
 */
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // =========================================================================
    // HEALTH CHECK
    // =========================================================================
    if (url.pathname === '/health') {
      return new Response('OK', {
        status: 200,
        headers: {
          'Content-Type': 'text/plain',
          'Cache-Control': 'no-cache'
        }
      });
    }

    // =========================================================================
    // WHATSAPP WEBHOOK VERIFICATION (GET)
    // =========================================================================
    // Meta/Twilio envían GET request para verificar el webhook
    if (url.pathname === '/webhook/meta' && request.method === 'GET') {
      return handleWebhookVerification(request, url);
    }

    // =========================================================================
    // WHATSAPP WEBHOOK MESSAGES (POST)
    // =========================================================================
    // Mensajes entrantes de WhatsApp
    if (url.pathname === '/webhook/meta' && request.method === 'POST') {
      return handleWebhookMessage(request, env, ctx);
    }

    // Twilio webhook
    if (url.pathname === '/webhook/twilio' && request.method === 'POST') {
      return handleWebhookMessage(request, env, ctx);
    }

    // =========================================================================
    // NOT FOUND
    // =========================================================================
    return new Response('Not Found', { status: 404 });
  }
};

/**
 * Handle webhook verification (GET request from Meta/Twilio)
 */
async function handleWebhookVerification(request, url) {
  // Meta Cloud API verification
  const mode = url.searchParams.get('hub.mode');
  const token = url.searchParams.get('hub.verify_token');
  const challenge = url.searchParams.get('hub.challenge');

  console.log(`Webhook verification: mode=${mode}, token=${token}`);

  // Forward to backend for verification
  const backendUrl = `${BACKEND_URL}/webhook/meta${url.search}`;

  const response = await fetch(backendUrl, {
    method: 'GET',
    headers: {
      'X-Forwarded-For': request.headers.get('CF-Connecting-IP'),
      'X-Real-IP': request.headers.get('CF-Connecting-IP')
    }
  });

  return response;
}

/**
 * Handle incoming webhook messages (POST request)
 */
async function handleWebhookMessage(request, env, ctx) {
  const url = new URL(request.url);
  const ip = request.headers.get('CF-Connecting-IP');

  // -------------------------
  // Rate Limiting (opcional)
  // -------------------------
  if (RATE_LIMIT.enabled && env.RATE_LIMITER) {
    const rateLimitKey = `rate_limit:${ip}`;
    const isAllowed = await checkRateLimit(env.RATE_LIMITER, rateLimitKey);

    if (!isAllowed) {
      console.warn(`Rate limit exceeded for IP: ${ip}`);
      return new Response('Too Many Requests', {
        status: 429,
        headers: {
          'Retry-After': '60'
        }
      });
    }
  }

  // -------------------------
  // Forward to Backend
  // -------------------------
  const backendUrl = `${BACKEND_URL}${url.pathname}`;

  console.log(`Forwarding webhook to: ${backendUrl}`);

  try {
    const response = await fetch(backendUrl, {
      method: request.method,
      headers: {
        'Content-Type': request.headers.get('Content-Type'),
        'X-Forwarded-For': ip,
        'X-Real-IP': ip,
        'X-Forwarded-Proto': 'https',
        'User-Agent': request.headers.get('User-Agent')
      },
      body: request.body
    });

    // Log status
    console.log(`Backend response: ${response.status}`);

    return response;

  } catch (error) {
    console.error('Error forwarding to backend:', error);

    return new Response('Service Temporarily Unavailable', {
      status: 503,
      headers: {
        'Retry-After': '10'
      }
    });
  }
}

/**
 * Check rate limit using KV storage
 */
async function checkRateLimit(kvStore, key) {
  const current = await kvStore.get(key);
  const count = current ? parseInt(current) : 0;

  if (count >= RATE_LIMIT.requestsPerMinute) {
    return false;
  }

  // Increment counter
  await kvStore.put(key, (count + 1).toString(), {
    expirationTtl: 60 // 1 minute
  });

  return true;
}

/**
 * Handle CORS preflight requests (opcional)
 */
function handleCors(request) {
  const origin = request.headers.get('Origin');

  if (ALLOWED_ORIGINS.includes(origin)) {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': origin,
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400'
      }
    });
  }

  return new Response('Forbidden', { status: 403 });
}
