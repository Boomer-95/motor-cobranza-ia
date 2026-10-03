const estadosTwilio = {
  queued: 'En cola', sending: 'Enviando', sent: 'Enviado; entrega no confirmada',
  delivered: 'Entregado', read: 'Leído', failed: 'Fallido', undelivered: 'No entregado',
};

export function estadoComunicacion(c) {
  let estado;
  if (c.modo === 'simulado' || c.simulada) estado = 'Simulado';
  else if (c.provider === 'twilio' && estadosTwilio[c.provider_status]) {
    estado = estadosTwilio[c.provider_status];
  } else if (c.estado === 'Enviado') {
    estado = c.provider === 'sendgrid' ? 'Enviado (aceptado; entrega no confirmada)'
      : 'Aceptado por proveedor; entrega no confirmada';
  } else estado = c.estado || 'Histórico; entrega no verificada';
  return `${c.canal} · ${estado}`;
}
