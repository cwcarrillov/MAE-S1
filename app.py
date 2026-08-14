import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

CONFIG = {'page_title': 'Digital Twin | Automotriz', 'icon': '🚗', 'title': 'Digital Twin · Línea de Ensamble Automotriz', 'target': 130, 'flow_window': 30, 'unit_singular': 'Vehículo', 'unit_plural': 'Vehículos', 'rate_unit': 'veh/h', 'stations': ['Carrocería', 'Pintura', 'Ensamble', 'Inspección', 'Salida'], 'station_x': [8, 30, 54, 78, 96], 'base_dot': '#2563eb', 'twin_dot': '#7c3aed', 'reject_short': 'rechazo final', 'reject_plural': 'Rechazados', 'changeover_status': 'CAMBIO DE MODELO', 'changeover_label_short': 'cambio de modelo', 'changeover_label': 'Cambio de modelo / setup (min)', 'changeover_help': 'Tiempo planificado para cambio de modelo o preparación de la línea. En la animación ocurre desde las 10:00.', 'materials_short': 'disponibilidad de componentes', 'materials_label': 'Disponibilidad de componentes (%)', 'materials_help': 'Porcentaje de capacidad que puede sostenerse según disponibilidad de piezas y componentes críticos.', 'rate_label': 'Velocidad nominal de línea (veh/h)', 'reject_label': 'Rechazo en inspección final (%)', 'reject_help': 'Porcentaje inicial de vehículos que no supera la inspección antes de considerar retrabajo.', 'recovery_short': 'recuperación por retrabajo', 'recovery_label': 'Recuperación por retrabajo (%)', 'recovery_help': 'Porcentaje de las unidades inicialmente rechazadas que se corrige y libera dentro del mismo turno.', 'good_kpi': 'Vehículos conformes', 'reject_kpi': 'Rechazados finales', 'base': {'rate': 18, 'downtime': 30, 'changeover': 10, 'labor': 99, 'materials': 99, 'reject': 2.0, 'recovery': 30}, 'ranges': {'rate': [12, 26, 1], 'labor': [85, 100, 1], 'materials': [85, 100, 1], 'changeover': [0, 45, 5], 'reject': [0.0, 8.0, 0.5]}, 'scope_note': 'El modelo representa una línea operacional simplificada. El estado base es fijo y el gemelo digital calcula la respuesta del mismo turno ante cambios de capacidad, disponibilidad, continuidad y calidad.'}

st.set_page_config(page_title=CONFIG["page_title"], page_icon=CONFIG["icon"], layout="wide")

SHIFT_MIN = 480
SHIFT_START_HOUR = 8
FRAME_STEP = 5
FLOW_WINDOW = CONFIG["flow_window"]
CHANGEOVER_START = 120   # 10:00
DOWNTIME_START = 300     # 13:00
TARGET = CONFIG["target"]
BASE = CONFIG["base"].copy()

st.markdown("""
<style>
.block-container {padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1500px;}
.small-note {font-size: .88rem; color: #5f6b7a; line-height: 1.4;}
.section-note {font-size: .92rem; color: #52606d; margin-top: -0.35rem; margin-bottom: .55rem;}
.card {
    border-radius: 14px; padding: 14px 16px; min-height: 104px;
    border: 1px solid rgba(15,23,42,.08); box-shadow: 0 2px 9px rgba(15,23,42,.05);
}
.card-label {font-size: .80rem; font-weight: 700; letter-spacing: .035em; text-transform: uppercase; opacity: .74;}
.card-value {font-size: 1.72rem; font-weight: 780; line-height: 1.15; margin-top: 5px;}
.card-note {font-size: .82rem; opacity: .73; margin-top: 5px; line-height: 1.25;}
.panel-title {font-size: 1.03rem; font-weight: 760; margin: .15rem 0 .65rem 0;}
.interpretation {
    border-radius: 14px; padding: 16px 18px; margin-top: 4px;
    border: 1px solid rgba(15,23,42,.08); line-height: 1.55;
}
.param-band {
    padding: 11px 14px; border-radius: 11px; background: #f8fafc;
    border: 1px solid #e2e8f0; margin-bottom: 10px; font-size: .90rem; color: #475569;
}
</style>
""", unsafe_allow_html=True)


def card(label, value, note, bg, accent):
    st.markdown(
        f"""<div class='card' style='background:{bg}; border-left:5px solid {accent};'>
        <div class='card-label'>{label}</div><div class='card-value'>{value}</div>
        <div class='card-note'>{note}</div></div>""",
        unsafe_allow_html=True,
    )


def effective_rate(params):
    return params["rate"] * (params["labor"] / 100.0) * (params["materials"] / 100.0)


def effective_reject(params):
    return params["reject"] * (1.0 - params["recovery"] / 100.0)


def productive_minutes(params):
    return max(SHIFT_MIN - params["changeover"] - params["downtime"], 0)


def productive_clock(wall_min: float, params: dict) -> float:
    lost = 0.0
    for start, duration in ((CHANGEOVER_START, params["changeover"]), (DOWNTIME_START, params["downtime"])):
        if wall_min > start:
            lost += min(float(duration), wall_min - start)
    return max(wall_min - lost, 0.0)


def build_units(params):
    rate_eff = max(effective_rate(params), 0.01)
    active_min = productive_minutes(params)
    interval = 60.0 / rate_eff
    completion = np.arange(interval, active_min + 1e-9, interval)
    n = len(completion)
    rejected = np.zeros(n, dtype=bool)
    final_reject = effective_reject(params)
    n_rej = int(round(n * final_reject / 100.0))
    if n_rej > 0 and n > 0:
        idx = np.unique(np.linspace(0, n - 1, n_rej, dtype=int))
        rejected[idx] = True
    return completion, rejected


def state(**params):
    completion, rejected = build_units(params)
    gross = len(completion)
    reject_n = int(rejected.sum())
    good = gross - reject_n
    service = good / TARGET * 100 if TARGET else 0
    return {
        "gross": gross,
        "reject": reject_n,
        "good": good,
        "service": service,
        "gap": good - TARGET,
        "effective_rate": effective_rate(params),
        "effective_reject": effective_reject(params),
        "productive_minutes": productive_minutes(params),
        "completion": completion,
        "rejected_mask": rejected,
    }


def visible_units(wall_min, params, sim, base_side=False):
    pclock = productive_clock(wall_min, params)
    completion = sim["completion"]
    rejected = sim["rejected_mask"]
    if len(completion) == 0:
        return [], [], [], 0, 0

    active = (completion - FLOW_WINDOW <= pclock) & (pclock < completion)
    ids = np.where(active)[0]
    xs, colors, labels = [], [], []
    normal_color = CONFIG["base_dot"] if base_side else CONFIG["twin_dot"]
    for i in ids:
        progress = 1 - (completion[i] - pclock) / FLOW_WINDOW
        xpos = float(np.clip(progress * 100, 0, 100))
        is_rej = bool(rejected[i])
        xs.append(xpos)
        colors.append("#dc2626" if is_rej and xpos >= 80 else normal_color)
        suffix = f" · {CONFIG['reject_short']}" if is_rej and xpos >= 80 else ""
        labels.append(f"{CONFIG['unit_singular']} {i+1}{suffix}")

    completed = completion <= pclock
    good_done = int(np.sum(completed & ~rejected))
    reject_done = int(np.sum(completed & rejected))
    return xs, colors, labels, good_done, reject_done


def run_status(wall_min, params):
    if params["changeover"] > 0 and CHANGEOVER_START <= wall_min < CHANGEOVER_START + params["changeover"]:
        return CONFIG["changeover_status"]
    if params["downtime"] > 0 and DOWNTIME_START <= wall_min < DOWNTIME_START + params["downtime"]:
        return "PARADA NO PLANIFICADA"
    return "EN PRODUCCIÓN"


def clock_label(minute):
    hour = SHIFT_START_HOUR + int(minute // 60)
    mins = int(minute % 60)
    return f"{hour:02d}:{mins:02d}"


def status_text(t, params, sim):
    _, _, _, good, rejected = visible_units(t, params, sim)
    return (
        f"<b>{clock_label(t)}</b> · {run_status(t, params)}"
        f"<br>{CONFIG['unit_plural']} conformes: <b>{good}</b> · {CONFIG['reject_plural']}: {rejected}"
        f"<br>Velocidad efectiva: <b>{sim['effective_rate']:.1f} {CONFIG['rate_unit']}</b>"
    )


def build_animation(base_params, twin_params, base_state, twin_state):
    stations = CONFIG["stations"]
    sx = CONFIG["station_x"]
    wall_times = np.arange(0, SHIFT_MIN + FRAME_STEP, FRAME_STEP)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("OPERACIÓN ACTUAL · ESTADO BASE", "GEMELO DIGITAL · ESCENARIO"),
        horizontal_spacing=0.08,
    )

    # Fondos diferenciados por lado.
    fig.add_shape(type="rect", x0=0, x1=100, y0=0, y1=1, fillcolor="#f4f9ff", opacity=1,
                  line=dict(color="#dbeafe", width=1), layer="below", row=1, col=1)
    fig.add_shape(type="rect", x0=0, x1=100, y0=0, y1=1, fillcolor="#faf7ff", opacity=1,
                  line=dict(color="#e9d5ff", width=1), layer="below", row=1, col=2)

    # Base: estaciones, unidades dinámicas, texto dinámico.
    fig.add_shape(type="line", x0=0, x1=100, y0=.55, y1=.55,
                  line=dict(width=5, color="#bfdbfe"), row=1, col=1)
    fig.add_trace(go.Scatter(x=sx, y=[.17]*len(sx), mode="markers+text", text=stations,
                             textposition="bottom center", marker=dict(size=17, symbol="square", color="#2563eb"),
                             hoverinfo="skip", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", marker=dict(size=13), customdata=[],
                             hovertemplate="%{customdata}<extra></extra>", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=[50], y=[.88], mode="text", text=[status_text(0, base_params, base_state)],
                             textfont=dict(size=13, color="#1e3a8a"), hoverinfo="skip", showlegend=False), row=1, col=1)

    # Gemelo: estaciones, unidades dinámicas, texto dinámico.
    fig.add_shape(type="line", x0=0, x1=100, y0=.55, y1=.55,
                  line=dict(width=5, color="#ddd6fe"), row=1, col=2)
    fig.add_trace(go.Scatter(x=sx, y=[.17]*len(sx), mode="markers+text", text=stations,
                             textposition="bottom center", marker=dict(size=17, symbol="square", color="#7c3aed"),
                             hoverinfo="skip", showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=[], y=[], mode="markers", marker=dict(size=13), customdata=[],
                             hovertemplate="%{customdata}<extra></extra>", showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=[50], y=[.88], mode="text", text=[status_text(0, twin_params, twin_state)],
                             textfont=dict(size=13, color="#5b21b6"), hoverinfo="skip", showlegend=False), row=1, col=2)

    frames = []
    for t in wall_times:
        bx, bc, bl, _, _ = visible_units(t, base_params, base_state, base_side=True)
        tx, tc, tl, _, _ = visible_units(t, twin_params, twin_state, base_side=False)
        frames.append(go.Frame(
            name=str(int(t)),
            data=[
                go.Scatter(x=bx, y=[.55]*len(bx), mode="markers", marker=dict(size=13, color=bc),
                           customdata=bl, hovertemplate="%{customdata}<extra></extra>", xaxis="x", yaxis="y"),
                go.Scatter(x=[50], y=[.88], mode="text", text=[status_text(t, base_params, base_state)],
                           textfont=dict(size=13, color="#1e3a8a"), hoverinfo="skip", xaxis="x", yaxis="y"),
                go.Scatter(x=tx, y=[.55]*len(tx), mode="markers", marker=dict(size=13, color=tc),
                           customdata=tl, hovertemplate="%{customdata}<extra></extra>", xaxis="x2", yaxis="y2"),
                go.Scatter(x=[50], y=[.88], mode="text", text=[status_text(t, twin_params, twin_state)],
                           textfont=dict(size=13, color="#5b21b6"), hoverinfo="skip", xaxis="x2", yaxis="y2"),
            ],
            traces=[1, 2, 4, 5],
        ))

    fig.frames = frames
    fig.update_xaxes(range=[0, 100], showgrid=False, showticklabels=False, zeroline=False)
    fig.update_yaxes(range=[0, 1], showgrid=False, showticklabels=False, zeroline=False)
    fig.update_layout(
        height=470, margin=dict(l=10, r=10, t=92, b=60), paper_bgcolor="white",
        updatemenus=[dict(
            type="buttons", direction="left", x=.5, xanchor="center", y=1.15, yanchor="top",
            buttons=[
                dict(label="▶ Play", method="animate", args=[None, {
                    "frame": {"duration": 90, "redraw": True}, "transition": {"duration": 0},
                    "fromcurrent": True, "mode": "immediate"}]),
                dict(label="⏸ Pause", method="animate", args=[[None], {
                    "frame": {"duration": 0, "redraw": True}, "transition": {"duration": 0}, "mode": "immediate"}]),
            ]
        )],
        sliders=[dict(
            active=0, x=.08, len=.84, y=-.08, currentvalue={"prefix": "Hora del turno · "},
            steps=[dict(method="animate", label=clock_label(t), args=[[str(int(t))], {
                "mode": "immediate", "frame": {"duration": 0, "redraw": True}, "transition": {"duration": 0}
            }]) for t in wall_times]
        )]
    )
    return fig


def cumulative_chart(base_params, twin_params, base_state, twin_state):
    wall_times = np.arange(0, SHIFT_MIN + FRAME_STEP, FRAME_STEP)
    def series(params, sim):
        out = []
        for t in wall_times:
            pclock = productive_clock(t, params)
            complete = sim["completion"] <= pclock
            out.append(int(np.sum(complete & ~sim["rejected_mask"])))
        return out
    b = series(base_params, base_state)
    tw = series(twin_params, twin_state)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wall_times/60 + SHIFT_START_HOUR, y=b, mode="lines", name="Operación actual",
                             line=dict(color="#2563eb", width=3)))
    fig.add_trace(go.Scatter(x=wall_times/60 + SHIFT_START_HOUR, y=tw, mode="lines", name="Gemelo digital",
                             line=dict(color="#7c3aed", width=3)))
    fig.add_hline(y=TARGET, line_dash="dash", line_color="#16a34a", annotation_text=f"Objetivo: {TARGET} {CONFIG['unit_plural'].lower()}")
    fig.update_layout(height=310, margin=dict(l=15, r=15, t=30, b=20), xaxis_title="Hora del turno",
                      yaxis_title=f"{CONFIG['unit_plural']} conformes acumulados", legend=dict(orientation="h"),
                      plot_bgcolor="white")
    fig.update_xaxes(gridcolor="#eef2f7")
    fig.update_yaxes(gridcolor="#eef2f7")
    return fig


def changed_drivers(base, twin):
    drivers = []
    specs = [
        ("rate", "velocidad nominal", True, CONFIG["rate_unit"]),
        ("downtime", "parada no planificada", False, "min"),
        ("changeover", CONFIG["changeover_label_short"], False, "min"),
        ("labor", "disponibilidad de personal", True, "%"),
        ("materials", CONFIG["materials_short"], True, "%"),
        ("reject", CONFIG["reject_short"], False, "%"),
        ("recovery", CONFIG["recovery_short"], True, "%"),
    ]
    for key, label, higher_good, unit in specs:
        diff = twin[key] - base[key]
        if abs(diff) < 1e-9:
            continue
        favorable = diff > 0 if higher_good else diff < 0
        sign = "+" if diff > 0 else ""
        drivers.append((favorable, f"{label} {sign}{diff:g}{unit}"))
    return drivers


def interpretation_html(base_params, twin_params, base_state, twin_state):
    delta_good = twin_state["good"] - base_state["good"]
    delta_service = twin_state["service"] - base_state["service"]
    delta_rej = twin_state["reject"] - base_state["reject"]
    rate_delta = twin_state["effective_rate"] - base_state["effective_rate"]
    prod_delta = twin_state["productive_minutes"] - base_state["productive_minutes"]
    drivers = changed_drivers(base_params, twin_params)

    if not drivers:
        label, color, bg = "ESCENARIO EQUIVALENTE", "#64748b", "#f8fafc"
        body = (f"El gemelo reproduce la configuración actual: {twin_state['good']} {CONFIG['unit_plural'].lower()} conformes, "
                f"{twin_state['reject']} {CONFIG['reject_plural'].lower()} y {twin_state['service']:.1f}% de cumplimiento. "
                "No existe todavía una intervención que genere divergencia frente al estado base.")
    else:
        if delta_good >= 5 and delta_service >= 0:
            label, color, bg = "ESCENARIO FAVORABLE", "#15803d", "#f0fdf4"
        elif delta_good <= -5 or twin_state["service"] < 90:
            label, color, bg = "ESCENARIO CON RIESGO OPERATIVO", "#b91c1c", "#fef2f2"
        else:
            label, color, bg = "ESCENARIO DE COMPROMISO", "#b45309", "#fff7ed"
        driver_text = "; ".join(d[1] for d in drivers[:4])
        body = (
            f"El escenario proyecta <b>{twin_state['good']} {CONFIG['unit_plural'].lower()} conformes</b>, "
            f"<b>{delta_good:+d}</b> frente a la operación actual. El cumplimiento cambia "
            f"{delta_service:+.1f} puntos porcentuales y los {CONFIG['reject_plural'].lower()} cambian {delta_rej:+d}. "
            f"La capacidad efectiva varía {rate_delta:+.1f} {CONFIG['rate_unit']} y el tiempo productivo {prod_delta:+.0f} min. "
            f"Los principales cambios introducidos son: {driver_text}."
        )
    return f"""<div class='interpretation' style='background:{bg}; border-left:5px solid {color};'>
        <div class='card-label' style='color:{color};'>{label}</div>
        <div style='margin-top:7px; color:#263238;'>{body}</div></div>"""


st.title(CONFIG["title"])
st.caption("Comparación sincronizada de una operación de 08:00 a 16:00: el estado base permanece fijo y solo el gemelo digital recibe intervenciones.")

# Contexto: pocas tarjetas, con semántica visual distinta.
c1, c2, c3, c4 = st.columns(4)
with c1: card("Horizonte", "8 horas", "Turno 08:00–16:00", "#eff6ff", "#2563eb")
with c2: card("Objetivo", f"{TARGET}", f"{CONFIG['unit_plural'].lower()} conformes", "#f0fdf4", "#16a34a")
with c3: card("Unidad animada", "1 punto", f"= 1 {CONFIG['unit_singular'].lower()}", "#faf5ff", "#9333ea")
with c4: card("Estado base", f"{BASE['rate']} {CONFIG['rate_unit']}", f"{BASE['downtime']} min de parada no planificada", "#fff7ed", "#ea580c")

st.subheader("Intervenciones del escenario digital")
st.markdown(
    f"""<div class='param-band'><b>Lógica del modelo:</b> la capacidad efectiva combina velocidad nominal, disponibilidad de personal y {CONFIG['materials_short']}. "
    El tiempo productivo descuenta {CONFIG['changeover_label_short']} y parada no planificada. La calidad final combina {CONFIG['reject_short']} y {CONFIG['recovery_short']}.</div>""",
    unsafe_allow_html=True,
)

st.markdown("**Capacidad y continuidad**")
st.markdown(f"<div class='section-note'>Modifican cuántas unidades puede procesar la línea y cuántos minutos permanece realmente disponible.</div>", unsafe_allow_html=True)
a, b, c, d = st.columns(4)
with a:
    rate = st.slider(CONFIG["rate_label"], CONFIG["ranges"]["rate"][0], CONFIG["ranges"]["rate"][1], BASE["rate"], CONFIG["ranges"]["rate"][2],
                     help="Capacidad nominal de salida de la línea cuando opera sin restricciones.")
with b:
    labor = st.slider("Disponibilidad de personal (%)", CONFIG["ranges"]["labor"][0], 100, BASE["labor"], 1,
                      help="Porcentaje de la capacidad nominal que puede sostenerse con la dotación disponible.")
with c:
    materials = st.slider(CONFIG["materials_label"], CONFIG["ranges"]["materials"][0], 100, BASE["materials"], 1,
                          help=CONFIG["materials_help"])
with d:
    changeover = st.slider(CONFIG["changeover_label"], 0, CONFIG["ranges"]["changeover"][1], BASE["changeover"], 5,
                           help=CONFIG["changeover_help"])

st.markdown("**Continuidad y calidad**")
st.markdown("<div class='section-note'>Representan pérdidas del turno y el efecto de calidad sobre las unidades que finalmente se liberan como conformes.</div>", unsafe_allow_html=True)
a, b, c = st.columns(3)
with a:
    downtime = st.slider("Parada no planificada (min)", 0, 90, BASE["downtime"], 5,
                         help="Tiempo acumulado de detenciones imprevistas durante el turno. En la animación ocurre desde las 13:00.")
with b:
    reject = st.slider(CONFIG["reject_label"], CONFIG["ranges"]["reject"][0], CONFIG["ranges"]["reject"][1], BASE["reject"], CONFIG["ranges"]["reject"][2],
                       help=CONFIG["reject_help"])
with c:
    recovery = st.slider(CONFIG["recovery_label"], 0, 80, BASE["recovery"], 5,
                         help=CONFIG["recovery_help"])

base_params = BASE.copy()
twin_params = {
    "rate": rate, "downtime": downtime, "changeover": changeover,
    "labor": labor, "materials": materials, "reject": reject, "recovery": recovery,
}
base_state = state(**base_params)
twin_state = state(**twin_params)

st.subheader("Operación sincronizada")
st.plotly_chart(build_animation(base_params, twin_params, base_state, twin_state), use_container_width=True,
                config={"displayModeBar": False})
st.caption(f"Azul = operación actual · Violeta = gemelo digital · Rojo = {CONFIG['reject_short']}. Cada punto representa exactamente 1 {CONFIG['unit_singular'].lower()} y el acumulado coincide con los KPI del turno.")

left, right = st.columns(2, gap="large")
with left:
    st.markdown("<div class='panel-title' style='color:#1d4ed8;'>OPERACIÓN ACTUAL · RESULTADO</div>", unsafe_allow_html=True)
    r1, r2 = st.columns(2)
    with r1: card(CONFIG["good_kpi"], f"{base_state['good']}", "Resultado conforme del turno", "#eff6ff", "#2563eb")
    with r2: card(CONFIG["reject_kpi"], f"{base_state['reject']}", f"Tasa efectiva {base_state['effective_reject']:.2f}%", "#fef2f2", "#dc2626")
    r3, r4 = st.columns(2)
    with r3: card("Cumplimiento", f"{base_state['service']:.1f}%", f"Objetivo {TARGET}", "#f0fdf4", "#16a34a")
    with r4: card("Capacidad efectiva", f"{base_state['effective_rate']:.1f}", CONFIG["rate_unit"], "#fff7ed", "#ea580c")
with right:
    st.markdown("<div class='panel-title' style='color:#7e22ce;'>GEMELO DIGITAL · RESULTADO SIMULADO</div>", unsafe_allow_html=True)
    r1, r2 = st.columns(2)
    with r1: card(CONFIG["good_kpi"], f"{twin_state['good']}", f"{twin_state['good']-base_state['good']:+d} vs. base", "#faf5ff", "#9333ea")
    with r2: card(CONFIG["reject_kpi"], f"{twin_state['reject']}", f"{twin_state['reject']-base_state['reject']:+d} vs. base", "#fff1f2", "#e11d48")
    r3, r4 = st.columns(2)
    with r3: card("Cumplimiento", f"{twin_state['service']:.1f}%", f"{twin_state['service']-base_state['service']:+.1f} pp", "#ecfdf5", "#059669")
    with r4: card("Capacidad efectiva", f"{twin_state['effective_rate']:.1f}", f"{twin_state['effective_rate']-base_state['effective_rate']:+.1f} {CONFIG['rate_unit']}", "#f5f3ff", "#7c3aed")

st.subheader("Interpretación del Gemelo Digital")
st.markdown(interpretation_html(base_params, twin_params, base_state, twin_state), unsafe_allow_html=True)

st.subheader("Evolución acumulada del mismo turno")
st.plotly_chart(cumulative_chart(base_params, twin_params, base_state, twin_state), use_container_width=True,
                config={"displayModeBar": False})

st.caption(CONFIG["scope_note"])
