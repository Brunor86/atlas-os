# Aprobaciones de un solo uso

Esta corrección parte de `feature/atlas-operator`, commit
`6fe9e30ec802ab71897981674d3dd0da5cb4eb9d`.

## Problema

Dos solicitudes podían consultar una aprobación válida y un historial vacío
simultáneamente, y ejecutar ambas la operación. También era posible repetirla
después de una interrupción entre la orden y la escritura del resultado.

## Comportamiento nuevo

Antes de llamar al handler, `ActionExecutorService` exige una reserva persistente
y atómica de la aprobación. SQLite conserva una fila por aprobación en
`action_execution_claims`, con su fecha de reserva. La clave primaria impide que
dos procesos adquieran la misma reserva.

La reserva verifica en la misma sentencia que la aprobación siga en `APPROVED`
y no exista un intento anterior en `action_history`. Se confirma en una conexión
independiente antes de emitir cualquier orden; no se mantiene una transacción
abierta durante la operación remota.

- Una aprobación produce como máximo un intento de ejecución a través del
  ejecutor supervisado. Se conservan las comprobaciones de integridad e historial.
- Las solicitudes concurrentes o repetidas quedan `BLOCKED`.
- Si falta la capacidad de reservar o la persistencia falla, no se llama al handler.
- La API conserva el resultado `BLOCKED` cuando el ejecutor lo devuelve.
- Un fallo o una interrupción no elimina la reserva.
- Las bases existentes reciben la tabla adicional al inicializar `Database`.
  No se modifican ni eliminan las aprobaciones y los historiales existentes.

Esto garantiza como máximo un intento por aprobación; no garantiza que la orden
remota termine ni que tenga un efecto conocido. Una interrupción justo después
de reservar puede dejar cero órdenes emitidas. Un resultado incierto requiere
comprobación antes de proponer y aprobar otra operación con un identificador nuevo.

Se conserva el contrato actual de estados de las solicitudes: una ejecución
interrumpida puede seguir figurando `APPROVED` aunque su reserva ya exista.
La reserva, junto con el historial, determina que no puede repetirse. La interfaz
de recuperación y los estados adicionales de ejecución quedan para otro cambio.

Los repositorios inyectados en el ejecutor deben implementar
`claim_action_execution(approval_id) -> bool` con una reserva duradera y atómica.
Si no lo hacen, el ejecutor bloquea la operación. Una base SQLite `:memory:` no
puede proporcionar esta reserva duradera.

## Verificación

Desde la raíz del proyecto, con sus dependencias de ejecución y pytest/HTTPX:

```bash
PYTHONPATH=src python -m pytest -q \
  tests/services/intelligence/test_execution_claims.py \
  tests/services/intelligence/test_action_pipeline.py \
  tests/api/test_operator_approval.py
```

Estas pruebas usan SQLite temporal y handlers simulados. Cubren conexiones
separadas, una conexión compartida por solicitudes, persistencia antes de la
orden, reapertura después de interrupciones, errores al guardar el resultado,
aprobaciones antiguas y la respuesta pública del endpoint.

## Actualización del servidor

Publicar esta rama o abrir su pull request no actualiza el servidor. La aplicación
se actualiza después de revisar e integrar el cambio.

1. Comprobar la rama, el commit y los cambios locales en `/opt/atlas`. Resolver
   cualquier diferencia antes de actualizar; no usar un reset destructivo.
2. Detener nuevas aprobaciones y esperar las operaciones en curso. Detener todos
   los procesos de ATLAS que puedan ejecutar acciones durante el reemplazo.
3. Hacer una copia consistente de la base indicada por `ATLAS_DB_PATH` o, si no
   está configurada, de `atlas.db` en el directorio de trabajo del servicio.
   Usar la API de backup de SQLite, o una copia con todos los escritores detenidos;
   una copia aislada del archivo principal puede omitir datos que estén en WAL.
4. Actualizar al commit revisado e integrado. Ejecutar las pruebas anteriores en
   el entorno de ATLAS y reiniciar los servicios que correspondan a la instalación.
5. Confirmar que todos los ejecutores usan la versión nueva antes de habilitar
   aprobaciones. Un proceso antiguo no conoce ni respeta las reservas.

No se requieren cambios de credenciales o configuración para esta corrección.
La autenticación de la API y el reinicio ordenado de VM se abordarán por separado.

## Operaciones interrumpidas

No borrar ni caducar reservas para intentar otra vez una orden. Primero consultar
el estado real del recurso, la reserva y `action_history`. La ausencia de un
resultado no demuestra que la orden no haya sido enviada.

Si corresponde otra operación, crear una nueva propuesta y obtener una nueva
aprobación explícita. Una reserva antigua nunca vuelve a habilitarse automáticamente.

Si se necesita volver a una versión anterior del código, mantener deshabilitadas
las aprobaciones hasta reconciliar los intentos inciertos: la versión anterior
ignorará `action_execution_claims`. La tabla es aditiva y puede conservarse.
