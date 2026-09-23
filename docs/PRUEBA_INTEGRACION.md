# Verificar imagen → tablero → API → modelo → resultado

Ejecute esta prueba en una instalación aislada con el paquete que se va a entregar. Para desarrollar la integración puede usar el paquete sintético de `ml_project/tests/create_fixture_package.py`; ese resultado no valida los pesos ni la precisión del modelo del equipo.

1. Arranque desde un volumen nuevo con el Compose de la raíz. Compruebe los tres servicios y `/ready`. Registre la revisión del código, versión del paquete, SHA-256 de los pesos y huella del preprocesamiento.
2. Abra el tablero y cargue una MRI JPG o PNG. Seleccione un país y clasifique. En la red del navegador, compruebe que el POST contiene el archivo y no contiene `hint`.
3. Compare `imageSha256` con la huella del archivo original. Ejecute ese mismo archivo directamente sobre el paquete y compare sus probabilidades con `confidenceByClass`, multiplicadas por 100 y redondeadas a dos decimales.
4. Repita con una muestra del tablero. Compruebe que viajan los bytes del archivo mostrado y que seleccionar otra clase de muestra no fuerza la predicción.
5. Envíe dos veces la misma imagen y cambie sólo el país. Las probabilidades deben mantenerse para un modelo determinista; cada consulta debe recibir un identificador propio en el historial.
6. Inicie sesión, abra el historial y compruebe identificador, versión, procedencia y CSV. Reinicie la API y compruebe que el registro sigue disponible.
7. Pruebe archivo corrupto, formato incorrecto, archivo excesivo, fallo del motor y fallo de base. Ninguno debe anunciar éxito ni mostrar resultados de reemplazo.
8. Interrumpa la conexión desde el navegador. Compruebe el mensaje de error y la recuperación al restaurarla. Cambie de imagen mientras una solicitud está pendiente y compruebe que su respuesta no se atribuye a la nueva imagen.
9. Revise análisis, historial y modelos en escritorio y móvil. No debe haber controles recortados, superposiciones ni métricas inventadas.

Registre por separado las pruebas con paquete sintético, con pesos entrenados y en el despliegue público. No dé por comprobado un entorno por haber probado otro. Consulte `api/INFERENCIA.md` y `web/INFERENCIA.md` para las suites automáticas.

Para verificar el servicio por HTTP, incluida la reutilización de conexiones al exportar CSV, defina `BNS_TEST_PASSWORD` y ejecute en un entorno aislado:

```sh
python scripts/verify_inference.py --api http://127.0.0.1:8000 --image web/public/samples/Te-gl_0023.jpg --username USUARIO_DE_PRUEBAS
```

El script crea dos predicciones y comprueba sus huellas, probabilidades, identificadores diferentes y aparición en tres exportaciones consecutivas. No lo ejecute contra producción sin autorización para crear esos registros.
