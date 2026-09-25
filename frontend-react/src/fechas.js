export const fechaVisible = fecha => fecha ? new Date(`${fecha}T12:00:00`).toLocaleDateString('es-MX') : '—';
export const diasVisible = dias => dias == null ? 'Sin vencimiento activo' : dias < 0 ? `Vencida hace ${-dias} días` : dias === 0 ? 'Vence hoy' : `Vence en ${dias} días`;
