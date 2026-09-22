// Configuración de entorno en tiempo de ejecución para desarrollo local.
// En despliegues con Docker/Nginx, este archivo es sobreescrito dinámicamente
// al arrancar el contenedor según las variables de entorno inyectadas.
window.__ENV__ = window.__ENV__ || {};
