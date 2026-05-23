# ================================================================================
# DEPLOY PROYECTO_B_WHATSAPP_SAAS TO CLOUD RUN
# ================================================================================
# Deploy de servicios multi-tenant (Restaurant, Farmacia, Taxis)
# Tiempo estimado: 25-30 minutos (5 servicios)
# ================================================================================

$ErrorActionPreference = "Continue"

Write-Host "========================================"
Write-Host "DEPLOY WHATSAPP SAAS TO CLOUD RUN"
Write-Host "========================================"
Write-Host ""

# Variables globales
$GCLOUD = "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
$PROJECT_ID = "restaurant-voice-system"
$REGION = "us-central1"
$REPO = "restaurant-services"  # Usar repositorio existente
$REGISTRY = "us-central1-docker.pkg.dev"
$IMAGE_PREFIX = "$REGISTRY/$PROJECT_ID/$REPO"

# Set working directory to script location
Set-Location -Path $PSScriptRoot

# Lista de servicios a deployar
$services = @(
    # Backend services
    @{
        name = "whatsapp-gateway"
        path = "./backend/whatsapp-gateway"
        port = 8000
        memory = "512Mi"
        cpu = 1
        needs_sql = $false
        needs_redis = $true
    },
    @{
        name = "sales-agent-service"
        path = "./backend/sales-agent-base"
        port = 5000
        memory = "1Gi"
        cpu = 2
        needs_sql = $false
        needs_redis = $true
    },
    @{
        name = "api-service"
        path = "./backend/api-service-base"
        port = 5011
        memory = "512Mi"
        cpu = 1
        needs_sql = $true
        needs_redis = $false
    },
    # Frontend services
    @{
        name = "customer-app-saas"
        path = "./frontend/customer-app"
        port = 80
        memory = "256Mi"
        cpu = 1
        needs_sql = $false
        needs_redis = $false
    },
    @{
        name = "admin-panel-saas"
        path = "./frontend/admin-panel"
        port = 80
        memory = "256Mi"
        cpu = 1
        needs_sql = $false
        needs_redis = $false
    }
)

$total_services = $services.Count
$deployed_count = 0
$failed_count = 0

Write-Host "Total de servicios a deployar: $total_services"
Write-Host "Arquitectura: Multi-tenant (Restaurant, Farmacia, Taxis)"
Write-Host ""

# Limpiar archivo de URLs
if (Test-Path ".\cloud_run_urls.txt") {
    Remove-Item ".\cloud_run_urls.txt"
}

$start_time = Get-Date

# ================================================================================
# DEPLOY SERVICES
# ================================================================================

foreach ($service in $services) {
    Write-Host "========================================"
    Write-Host "Deploying: $($service.name)"
    Write-Host "========================================"

    $image_name = "$IMAGE_PREFIX/$($service.name):latest"

    # Verificar Dockerfile
    if (-not (Test-Path "$($service.path)/Dockerfile")) {
        Write-Host "ERROR: Dockerfile no encontrado: $($service.path)/Dockerfile"
        $failed_count++
        continue
    }

    # STEP 1: Build
    Write-Host "[1/3] Building image with Cloud Build..."

    & $GCLOUD builds submit $service.path --tag=$image_name --timeout=20m --quiet

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to build $($service.name)"
        $failed_count++
        continue
    }

    Write-Host "SUCCESS: Image built"

    # STEP 2: Deploy
    Write-Host "[2/3] Deploying to Cloud Run..."

    # Construir comando base
    $deploy_args = @(
        "run", "deploy", $service.name,
        "--image=$image_name",
        "--platform=managed",
        "--region=$REGION",
        "--allow-unauthenticated",
        "--port=$($service.port)",
        "--memory=$($service.memory)",
        "--cpu=$($service.cpu)",
        "--timeout=300",
        "--min-instances=0",
        "--max-instances=10"
    )

    # Agregar Cloud SQL si lo necesita
    if ($service.needs_sql) {
        $deploy_args += "--add-cloudsql-instances=restaurant-voice-system:us-central1:restaurant-db"
    }

    # Agregar VPC connector para Redis si lo necesita
    if ($service.needs_redis) {
        # Nota: Asume que existe un VPC connector llamado 'whatsapp-connector'
        # Si no existe, crearlo con: gcloud compute networks vpc-access connectors create whatsapp-connector --region=us-central1
        $deploy_args += "--vpc-connector=whatsapp-connector"
    }

    # Determinar archivo de variables de entorno
    $env_file = ""
    switch ($service.name) {
        "whatsapp-gateway" { $env_file = "env-vars-whatsapp-gateway.yaml" }
        "sales-agent-service" { $env_file = "env-vars-sales-agent.yaml" }
        "api-service" { $env_file = "env-vars-api-service.yaml" }
    }

    # Agregar archivo de env vars si existe
    if ($env_file -and (Test-Path $env_file)) {
        $deploy_args += "--env-vars-file=$env_file"
    } else {
        # Variables de entorno básicas para frontends
        $env_vars = "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION"
        $deploy_args += "--set-env-vars=$env_vars"
    }

    $deploy_args += "--quiet"

    # Ejecutar deploy
    & $GCLOUD $deploy_args

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to deploy $($service.name)"
        $failed_count++
        continue
    }

    # STEP 3: Get URL
    Write-Host "[3/3] Getting service URL..."

    $service_url = & $GCLOUD run services describe $service.name --region=$REGION --format="value(status.url)" 2>&1 | Out-String
    $service_url = $service_url.Trim()

    if ($service_url -and $service_url -notmatch "ERROR") {
        Write-Host "SUCCESS: Service deployed at $service_url"
        Add-Content -Path ".\cloud_run_urls.txt" -Value "$($service.name)=$service_url"
        $deployed_count++
    }
    else {
        Write-Host "WARNING: Deployed but could not get URL"
        $deployed_count++
    }

    Write-Host ""
    Write-Host "Progress: $deployed_count/$total_services deployed, $failed_count failed"
    Write-Host ""
}

# ================================================================================
# RESUMEN FINAL
# ================================================================================
$end_time = Get-Date
$duration = $end_time - $start_time

Write-Host "========================================"
Write-Host "DEPLOY COMPLETED"
Write-Host "========================================"
Write-Host ""
Write-Host "Summary:"
Write-Host "  Total services: $total_services"
Write-Host "  Deployed successfully: $deployed_count"
Write-Host "  Failed: $failed_count"
Write-Host "  Total time: $($duration.Hours)h $($duration.Minutes)m $($duration.Seconds)s"
Write-Host ""

if (Test-Path ".\cloud_run_urls.txt") {
    Write-Host "Service URLs saved in: cloud_run_urls.txt"
    Write-Host ""
    Write-Host "URLs:"
    Get-Content ".\cloud_run_urls.txt"
}

Write-Host ""
Write-Host "========================================"
Write-Host "NEXT STEPS"
Write-Host "========================================"
Write-Host ""
Write-Host "1. Update .env.production with Cloud Run URLs"
Write-Host "2. Configure Twilio webhook: https://whatsapp-gateway-XXXXX.a.run.app/webhook/whatsapp"
Write-Host "3. Configure Meta webhook: https://whatsapp-gateway-XXXXX.a.run.app/webhook/meta"
Write-Host "4. Test each store (restaurant, farmacia, taxis)"
Write-Host ""
Write-Host "MULTI-TENANT:"
Write-Host "  - 1 deploy sirve para 3 tiendas"
Write-Host "  - Cada tienda usa su propio numero de WhatsApp"
Write-Host "  - Base de datos compartida con tenant_id"
Write-Host ""
