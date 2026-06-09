---
name: feature
description: Flujo estándar de Tendero para construir una fase o feature nueva, de plan a revisión. Invócalo explícitamente con /feature cuando vayas a empezar.
---

# Flujo de feature de Tendero

Cuando se te invoque, sigue estos pasos en orden. No te saltes ninguno.

Antes de empezar, LEE `CLAUDE.md` (raíz) y `brief-tendero-pro.md`.

1. **Planear.** Delega al subagente `architect` para que diseñe el plan técnico
   (modelos, migración Alembic, endpoints, cambios de frontend, tests, orden de
   construcción y decisiones abiertas).
2. **Confirmar.** Presenta al usuario las decisiones abiertas del plan y ESPERA su
   respuesta antes de escribir código. No asumas valores por defecto en decisiones
   que tocan el modelo de datos, el manejo de dinero o el cumplimiento legal
   (facturación DIAN, Habeas Data).
3. **Construir en pasos pequeños.** Implementa respetando las invariantes del
   `CLAUDE.md`: arquitectura en capas (router → service → repository → model),
   dinero en enteros (nunca float), migraciones siempre por Alembic, secretos solo
   en .env, integraciones externas detrás de interfaces mock/real, idempotencia en
   pagos y emisión de facturas. Cada paso debe ser verificable. El frontend sigue la
   dirección de diseño "Rótulo".
4. **Tests.** Escribe los tests del paso. Cobertura alta y obligatoria en todo lo que
   toca dinero, stock, auth, pagos o emisión fiscal.
5. **Revisar.** Antes de dar por terminado, delega al subagente `security-reviewer`
   para auditar los cambios. Corrige los hallazgos críticos y altos antes de cerrar.
6. **Resumir.** Reporta qué se construyó, qué tests pasan y qué quedó pendiente.
   Actualiza la sección de Estado del `CLAUDE.md` raíz. Haz un commit convencional.
