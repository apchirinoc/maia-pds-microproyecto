# Tablero conectado a la API

Configure `VITE_API_BASE_URL` con una URL accesible desde el navegador y `VITE_FORCE_MOCKS=false`. Con Docker estas variables se inyectan al arrancar; con Vite configure `.env` antes de iniciar el servidor de desarrollo.

Las imágenes cargadas y las muestras se envían como archivos multipart a `/api/v1/classifications`. La selección de muestra no envía una clase sugerida. El país acompaña a la imagen como metadato. El tablero muestra la respuesta de la API sin reemplazarla por una simulación si la red o el modelo fallan.

Al cambiar de imagen o país se invalida el resultado anterior. Las respuestas que llegan tarde no se presentan como resultado de la nueva selección. La pantalla muestra carga, errores recuperables, versión del motor y confirmación de almacenamiento. El informe descargable incluye la identidad del modelo y la huella de la imagen.

Los gráficos del dataset son información de referencia. El historial identifica registros simulados y sus miniaturas son ilustrativas. Los valores de evaluación no disponibles se muestran con `—`. Cambiar el modelo requiere configurar y reiniciar la API; los controles de activación, descarga ficticia de pesos e incorporación de imágenes al dataset no anuncian operaciones que el servicio no realiza.

## Verificación local

```sh
npm ci
npm test
npm run build
npm run lint
```

Las pruebas del servicio verifican el archivo enviado y la ausencia de `hint`. Las del gateway comprueban que los errores HTTP y de conexión se propagan y que sólo `VITE_FORCE_MOCKS=true` permite usar datos simulados.

En navegador, pruebe una carga y una muestra, cambie la selección durante una consulta, interrumpa la conexión y recupérela. Compruebe el resultado y su informe, el historial, la pantalla de modelos y los tamaños móvil y escritorio. El procedimiento completo está en `docs/PRUEBA_INTEGRACION.md`.
