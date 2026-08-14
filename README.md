# Gemelos Digitales Dinámicos v3

Dos demostradores Streamlit de gemelo digital operacional:

- `01_Automotriz/app.py`: línea de ensamble automotriz.
- `02_Bebidas/app.py`: planta embotelladora de bebidas.

## Cambios principales de v3

- Se corrige la asignación de la animación: el estado base permanece fijo y los sliders afectan solo al gemelo digital.
- Las dos mitades de la animación usan ejes, colores y trazas explícitamente separados.
- Cada punto animado equivale exactamente a una unidad contabilizada en los KPI.
- Se amplían las intervenciones de 3 a 7 variables operativas, agrupadas por contexto.
- Se incorporan tarjetas de KPI con colores semánticos.
- Se añade una sección ejecutiva `Interpretación del Gemelo Digital` con lectura automática del escenario.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run 01_Automotriz/app.py
```

o bien:

```bash
streamlit run 02_Bebidas/app.py
```

## Horizonte del modelo

Ambos prototipos representan un turno de 08:00 a 16:00. La operación actual es fija; el gemelo digital comparte el mismo reloj, objetivo y secuencia de proceso, pero recibe las intervenciones configuradas en los sliders.
