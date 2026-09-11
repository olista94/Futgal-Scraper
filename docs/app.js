async function main() {
  const estadoEl = document.getElementById("estado");
  const tituloEl = document.getElementById("titulo");
  const actualizadoEl = document.getElementById("actualizado");
  const selectEl = document.getElementById("jornada");
  const tbody = document.getElementById("tabla-body");

  let data;
  try {
    const res = await fetch("data/partidos.json", { cache: "no-store" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    data = await res.json();
  } catch (err) {
    estadoEl.textContent = "No se han podido cargar los datos todavía. " +
      "Si acabas de configurar el repositorio, lanza el workflow 'Actualizar datos de partidos' " +
      "desde la pestaña Actions.";
    return;
  }

  tituloEl.textContent = [data.competicion, data.grupo].filter(Boolean).join(" · ") || "Partidos";
  if (data.generated_at) {
    const fecha = new Date(data.generated_at);
    actualizadoEl.textContent = "Actualizado: " + fecha.toLocaleString("es-ES");
  }

  const jornadas = Object.keys(data.jornadas || {}).sort((a, b) => Number(a) - Number(b));
  if (jornadas.length === 0) {
    estadoEl.textContent = "Todavía no hay jornadas con datos.";
    return;
  }

  for (const j of jornadas) {
    const opt = document.createElement("option");
    opt.value = j;
    opt.textContent = "Jornada " + j;
    selectEl.appendChild(opt);
  }

  function render(jornada) {
    const partidos = data.jornadas[jornada] || [];
    tbody.innerHTML = "";

    if (partidos.length === 0) {
      estadoEl.textContent = "No hay partidos para esta jornada.";
      return;
    }
    estadoEl.textContent = "";

    for (const p of partidos) {
      const tr = document.createElement("tr");
      for (const campo of ["equipo_local", "equipo_visitante", "arbitro", "asistente1", "asistente2"]) {
        const td = document.createElement("td");
        td.textContent = p[campo] || "—";
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
  }

  selectEl.addEventListener("change", () => render(selectEl.value));

  // Última jornada con partidos por defecto
  const inicial = jornadas[jornadas.length - 1];
  selectEl.value = inicial;
  render(inicial);
}

main();
