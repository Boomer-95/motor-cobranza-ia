// Iconos locales de presentación; no requieren fuentes ni recursos externos.
const trazos = {
  resumen: <><path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z" /></>,
  operacion: <><path d="M3 6h18v12H3zM7 18v3h10" /><circle cx="12" cy="12" r="3" /></>,
  cartera: <><path d="M20 7V4H4v16h16V7H4M16 10h5v6h-5z" /></>,
  analitica: <><path d="M4 3v17h17M8 16v-5M13 16V7M18 16V4" /></>,
  historial: <><path d="M3 4v5h5M3 9a9 9 0 1 1 0 7M12 7v5l3 2" /></>,
  usuario: <><circle cx="12" cy="7" r="3" /><path d="M5 21v-3a7 7 0 0 1 14 0v3z" /></>,
  salir: <><path d="M9 4H4v16h5M10 12h11M17 8l4 4-4 4" /></>,
  actualizar: <><path d="M20 4v6h-6M20 10a8 8 0 1 0 0 6" /></>,
};

export default function Icono({ nombre }) {
  return <svg className="icono" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {trazos[nombre]}
  </svg>;
}
