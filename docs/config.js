// Configuración de la plataforma. Estos dos valores son PÚBLICOS por diseño:
// la seguridad la ponen las reglas de la base de datos, no esta clave.
// Supabase > Project Settings:
//   - Project URL: en "Data API" (o botón "Connect" del proyecto)
//   - Publishable key (sb_publishable_...): en "API Keys"
// NUNCA pongas aquí la secret key (sb_secret_...).
window.CONFIG = {
  SUPABASE_URL: "https://moyauyvqhhsuqgmgnmvv.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_cmHKcNq8djMX7ebMfmPSpA_paBu_etm",

  // Límite de palabras del resumen (solo avisa, no bloquea el envío).
  PALABRAS_MAX: 250,

  // Fecha límite que se muestra a los autores (texto libre; vacío = no se muestra).
  FECHA_LIMITE: "",

  // Correo de contacto del comité para dudas.
  CORREO_CONTACTO: "",
};
