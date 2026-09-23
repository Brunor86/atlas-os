> **Historical document.** This file captures an earlier ATLAS roadmap and
> contains branch names, versions and future plans that are no longer the
> authoritative description of the current system.
>
> Current v1.0 documentation:
>
> - `README.md`
> - `docs/RELEASE_CONTRACT_V1.md`
> - `docs/BACKUP_RESTORE_V1.md`
> - `docs/BOOT_RECOVERY_V1.md`
> - `docs/OPERATOR_SINGLE_EXECUTION.md`
>
> The content below is retained as project evolution history.

# ATLAS Project Context

## 1. Descripción general

ATLAS es una plataforma de inteligencia y operación para homelab, infraestructura y aplicaciones personales.

El objetivo final es que ATLAS sea un **NOC inteligente autónomo**, capaz de observar, analizar, razonar y eventualmente ejecutar acciones sobre toda la infraestructura.

No debe ser solamente un dashboard de métricas. Debe convertirse en un asistente operativo que conozca:

* Servidores físicos
* Proxmox
* VM
* LXC
* Docker
* Aplicaciones desplegadas
* Bases de datos
* Servicios IoT
* Home Assistant
* Raspberry Pi
* Dispositivos de red
* Código fuente y versiones
* Historial de cambios
* Estado operativo de aplicaciones

La meta final es llegar a:

**ATLAS v1.0.0**

Una plataforma estable donde el usuario pueda delegar tareas de monitoreo, análisis y operación.

---

# 2. Estado actual del proyecto

Repositorio:

```
atlas
```

Branch principal de desarrollo actual:

```
feature/noc-dashboard
```

Última versión relevante:

```
v0.27.6
```

Estado actual:

* Dashboard web funcionando
* NOC Intelligence funcionando
* Correlación de eventos funcionando
* Inteligencia sobre logs integrada
* Root Cause Engine agregado
* Métricas Docker desde Prometheus funcionando
* Dashboard mostrando información de containers
* Infraestructura documentada mediante snapshots

---

# 3. Arquitectura actual

## Core

Ubicación:

```
src/atlas/core
```

Responsable de modelos centrales de infraestructura.

---

## Models

Ubicación:

```
src/atlas/models
```

Contiene:

* system
* docker
* container
* storage
* network
* proxmox
* events
* health
* noc
* insights

---

## Services

Ubicación:

```
src/atlas/services
```

Principales módulos:

### Health

Evalúa salud de infraestructura.

```
services/health
```

### Events

Sistema de eventos:

```
services/events
```

Incluye:

* analytics
* correlation
* event history

### AI

```
services/ai
```

Actualmente contiene:

* reasoning engine
* change intelligence
* context

### Intelligence

```
services/intelligence
```

Capa de análisis inteligente.

### Logs

```
services/logs
```

Analiza logs de containers.

### NOC

```
services/noc
```

Actualmente contiene:

* NOCService
* correlation
* intelligence
* log intelligence
* root cause
* scorer
* orchestrator

### Metrics

```
services/metrics
```

Actualmente:

* Prometheus client
* Docker CPU metrics
* Docker RAM metrics

---

# 4. Visión del NOC

El NOC no debe crecer solamente agregando widgets.

Debe evolucionar hacia un sistema de inteligencia.

La información debe estar organizada:

## Dashboard

Debe mostrar:

1. Estado general
2. Alertas importantes
3. Causas probables
4. Recomendaciones
5. Aplicaciones críticas
6. Containers
7. Infraestructura

Los containers deben permanecer como sección independiente.

No mezclar:

* Estado NOC
* Métricas Docker

Ejemplo correcto:

```
NOC Intelligence

CRITICAL
Score 70
Priority HIGH

Reason:
Infrastructure degradation


Docker Containers

24 / 25 running

syncthing
CPU
RAM
```

---

# 5. Visión futura IA

ATLAS debe incorporar un agente inteligente real.

No solamente un chat.

Debe poder responder preguntas como:

## Infraestructura

Ejemplos:

"¿Por qué está lenta la aplicación de cata de aceite?"

Respuesta esperada:

"La aplicación presenta degradación porque:

* MariaDB tiene 85% de conexiones ocupadas
* El LXC 102 tiene solamente 512 MB RAM
* El consumo promedio supera el 90%

Recomiendo aumentar RAM a 1 GB."

---

## Aplicaciones

ATLAS debe conocer servicios:

Ejemplo:

```json
{
 "service": "cata-aceite",
 "type": "application",
 "location": "lxc-102",
 "database": "mariadb",
 "owner": "Bruno",
 "criticality": "high"
}
```

Debe poder:

* Leer bases de datos
* Analizar información
* Generar reportes
* Entender aplicaciones nuevas

Ejemplos:

"¿Cuántas muestras de aceite se cataron en 2026?"

"¿Cuál fue el promedio de atributos de Arbequina?"

"Generame el informe de temporada."

---

# 6. Integraciones futuras

## Proxmox

ATLAS debe poder:

Leer:

* VM
* LXC
* CPU
* RAM
* discos
* snapshots

Futuro:

Ejecutar acciones:

"Subir RAM del LXC 102 a 1 GB"

"Asignar más CPU a la VM Home Assistant"

Siempre con:

* registro
* autorización
* rollback

---

## Docker

Debe poder:

* Detectar containers nuevos automáticamente
* Guardar versiones
* Detectar cambios
* Relacionar problemas con actualizaciones

Ejemplo:

"Después de actualizar Immich comenzó el problema"

ATLAS debería consultar:

* Git
* cambios
* Docker image
* logs
* métricas

---

## Git Intelligence

ATLAS debe conocer:

* commits
* tags
* versiones

Debe permitir:

"Volver a la versión anterior"

Ejemplo:

```
Rollback a v0.27.5
```

Si una actualización rompe algo:

* identificar cambio
* sugerir rollback
* ejecutar restauración

---

## Home Assistant

Integración futura:

ATLAS debe poder consultar:

* luces
* sensores
* alarmas
* automatizaciones

Ejemplos:

"¿Qué luces están encendidas?"

"¿La alarma está armada?"

"Apaga las luces del living"

---

## Raspberry Pi / IoT

Debe poder manejar múltiples nodos.

Actualmente:

* Raspberry Pi
* Wemos D1
* sensores MQTT

Futuro:

Agregar nuevos dispositivos sin modificar ATLAS.

---

# 7. Principio de diseño

ATLAS debe ser extensible.

No crear módulos específicos para cada dispositivo.

Debe existir un modelo de:

```
Asset
```

donde cualquier recurso pueda registrarse:

Ejemplo:

```
Asset
 |
 + Server
 |
 + VM
 |
 + LXC
 |
 + Container
 |
 + Raspberry
 |
 + Database
 |
 + Application
 |
 + Sensor
```

Cada nuevo elemento debe incorporarse mediante descubrimiento o registro.

---

# 8. Base de conocimiento

ATLAS debe tener memoria.

Debe almacenar:

* infraestructura actual
* historial
* cambios
* relaciones
* dependencias

Ejemplo:

```
Aplicación cata aceite
 |
 + LXC 102
 |
 + MariaDB
 |
 + Backend
 |
 + Usuarios
 |
 + Datos históricos
```

---

# 9. Seguridad

Las acciones destructivas requieren:

* confirmación
* registro
* backup
* rollback

Nunca ejecutar:

* eliminar
* apagar
* modificar recursos críticos

sin autorización.

---

# 10. Objetivo final ATLAS v1.0.0

ATLAS v1.0.0 debe ser:

Un operador inteligente personal.

Debe poder:

✓ Ver infraestructura completa
✓ Detectar problemas
✓ Explicar causas
✓ Analizar aplicaciones
✓ Leer datos de negocio
✓ Generar informes
✓ Interactuar con IoT
✓ Gestionar recursos
✓ Mantener historial
✓ Recuperarse de errores
✓ Escalar con nuevos servicios

La idea es que ATLAS reduzca la administración manual del homelab y permita que la infraestructura crezca sin aumentar la complejidad operativa.

---

# Próxima evolución recomendada

No seguir agregando paneles.

Siguiente etapa:

1. Consolidar modelo de conocimiento de infraestructura.
2. Crear Asset Registry.
3. Crear Knowledge Graph.
4. Integrar IA local.
5. Crear sistema de permisos de acciones.
6. Crear Action Engine con rollback.
7. Evolucionar hacia ATLAS v1.0.0.


# Milestones históricos

## v0.100.0 — Local AI Brain Online

**Fecha:** 2026-08-03

ATLAS ejecutó por primera vez una inferencia utilizando un modelo de inteligencia artificial completamente local.

Stack: GMKtec Ryzen 7 8845HS + Proxmox + VM atlas-ai + Debian 13 + Ollama + Qwen2.5 7B Q4_K_M.

Resultado: ATLAS AI CONNECTED.
