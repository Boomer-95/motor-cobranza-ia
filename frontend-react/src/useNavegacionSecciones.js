import { useCallback, useEffect, useRef, useState } from 'react';

export const SECCIONES = [
  { id: 'resumen', titulo: 'Resumen' },
  { id: 'operacion', titulo: 'Operación de Cobranza' },
  { id: 'cartera', titulo: 'Cartera' },
  { id: 'historial', titulo: 'Historial' },
];

export default function useNavegacionSecciones(autenticado) {
  const seccionesRef = useRef({});
  const inicioRef = useRef(null);
  const destinoRef = useRef(null);
  const [seccionActiva, setSeccionActiva] = useState('resumen');

  const navegar = useCallback((id, actualizarUrl = true, enfocar = false) => {
    const seccion = seccionesRef.current[id];
    if (!seccion) return;
    destinoRef.current = id;
    setSeccionActiva(id);
    if (actualizarUrl && window.location.hash !== `#${id}`) {
      window.history.pushState(null, '', `#${id}`);
    }
    // Desplazamiento inmediato: sin animaciones y compatible con movimiento reducido.
    const destino = id === 'resumen' ? inicioRef.current : seccion;
    destino?.scrollIntoView({ behavior: 'auto', block: 'start' });
    if (enfocar) seccion.focus({ preventScroll: true });
  }, []);

  useEffect(() => {
    if (!autenticado) return;
    let frame = 0;
    const leerHash = () => {
      const id = window.location.hash.slice(1);
      navegar(SECCIONES.some(s => s.id === id) ? id : 'resumen', false);
    };
    const actualizarActiva = () => {
      frame = 0;
      if (destinoRef.current) return;
      const secciones = SECCIONES.filter(s => seccionesRef.current[s.id]);
      // La sección que cruza la parte superior prevalece sobre las visibles debajo.
      let activa = 'resumen';
      for (const { id } of secciones) {
        if (seccionesRef.current[id].getBoundingClientRect().top <= 80) activa = id;
      }
      const alFinal = window.scrollY > 0 &&
        window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 2;
      if (alFinal) activa = secciones.at(-1)?.id || activa;
      setSeccionActiva(activa);
      if (window.location.hash !== `#${activa}`) {
        window.history.replaceState(null, '', `#${activa}`);
      }
    };
    const programarActualizacion = () => {
      if (!frame) frame = window.requestAnimationFrame(actualizarActiva);
    };
    const liberarDestino = () => { destinoRef.current = null; };
    const alTeclado = (event) => {
      if (['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) {
        liberarDestino();
      }
    };
    // Mantiene el enlace directo cuando la cartera termina de cargar y cambia la altura.
    const observer = new ResizeObserver(() => {
      if (destinoRef.current) navegar(destinoRef.current, false);
      else programarActualizacion();
    });
    for (const { id } of SECCIONES) {
      if (seccionesRef.current[id]) observer.observe(seccionesRef.current[id]);
    }
    leerHash();
    window.addEventListener('hashchange', leerHash);
    window.addEventListener('scroll', programarActualizacion, { passive: true });
    window.addEventListener('resize', programarActualizacion);
    window.addEventListener('wheel', liberarDestino, { passive: true });
    window.addEventListener('touchmove', liberarDestino, { passive: true });
    window.addEventListener('pointerdown', liberarDestino, { passive: true });
    window.addEventListener('keydown', alTeclado);
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
      window.removeEventListener('hashchange', leerHash);
      window.removeEventListener('scroll', programarActualizacion);
      window.removeEventListener('resize', programarActualizacion);
      window.removeEventListener('wheel', liberarDestino);
      window.removeEventListener('touchmove', liberarDestino);
      window.removeEventListener('pointerdown', liberarDestino);
      window.removeEventListener('keydown', alTeclado);
    };
  }, [autenticado, navegar]);

  return { seccionesRef, inicioRef, seccionActiva, navegar };
}
