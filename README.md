# Security Guardian 🛡️

Microservicio centinela para la monitorización proactiva de vulnerabilidades (CVEs, CISA KEV, Red Hat Security Advisories) y alertas virales en Hacker News para el clúster de Kubernetes e infraestructura host.

## Características
- 📡 **Monitorización de Hacker News:** Búsqueda en Algolia HN con filtro por puntuación y palabras clave de seguridad (Linux kernel, RHEL, CRI-O, K8s, zero-days).
- 🚨 **CISA KEV / NVD Feeds:** Detección de vulnerabilidades activamente explotadas.
- 💬 **Notificaciones en Telegram:** Alertas instantáneas con botones interactivos hacia las fuentes de información.
- ⚙️ **FastAPI + Scheduler:** Endpoints REST para auditorías bajo demanda y ejecuciones periódicas automáticas.
- 🚢 **Kubernetes & GitOps Ready:** Dockerfile y manifiestos para despliegue en K8s con CI en Jenkins.

## Estructura del Proyecto
```
security-guardian/
├── app/
│   ├── config.py
│   ├── main.py
│   └── services/
│       ├── telegram_service.py
│       ├── hn_scanner.py
│       └── cisa_scanner.py
├── scripts/
│   ├── test_telegram.py
│   └── get_chat_id.py
├── requirements.txt
├── .env.example
└── README.md
```
