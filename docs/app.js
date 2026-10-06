async function main() {
  const estadoEl = document.getElementById("estado");
  const tituloEl = document.getElementById("titulo");
  const actualizadoEl = document.getElementById("actualizado");
  const selectEl = document.getElementById("jornada");
  const tbody = document.getElementById("tabla-body");
  const busquedaEl = document.getElementById("busqueda");

  let data;

  try {
    const res = await fetch("data/partidos.json", { cache: "no-store" });

    if (!res.ok) {
      throw new Error("HTTP " + res.status);
    }

    data = await res.json();
  } catch (err) {
    estadoEl.textContent =
      "No se han podido cargar los datos todavía. " +
      "Si acabas de configurar el repositorio, lanza el workflow " +
      "'Actualizar datos de partidos' desde la pestaña Actions.";

    return;
  }

  tituloEl.textContent =
    [data.competicion, data.grupo]
      .filter(Boolean)
      .join(" · ") || "Partidos";

  if (data.generated_at) {
    const fecha = new Date(data.generated_at);

    actualizadoEl.textContent =
      "Actualizado: " + fecha.toLocaleString("es-ES");
  }

  const jornadas = Object.keys(data.jornadas || {}).sort(
    (a, b) => Number(a) - Number(b)
  );

  if (jornadas.length === 0) {
    estadoEl.textContent = "Todavía no hay jornadas con datos.";
    return;
  }

  const optTodas = document.createElement("option");
  optTodas.value = "todas";
  optTodas.textContent = "Todas las jornadas";
  selectEl.appendChild(optTodas);
  for (const j of jornadas) {
    const opt = document.createElement("option");

    opt.value = j;
    opt.textContent = "Jornada " + j;

    selectEl.appendChild(opt);
  }

  /*
   * Futgal devuelve los colegiados así:
   *
   * QUINTAS GARCIA, MIGUEL
   *
   * Y nosotros lo mostramos así:
   *
   * MIGUEL
   * QUINTAS GARCIA
   *
   * El JSON original no se modifica.
   */
  function renderOfficialName(td, value) {
    if (!value) {
      td.textContent = "—";
      return;
    }

    const commaIndex = value.indexOf(",");

    /*
     * Si por algún motivo Futgal devuelve un nombre
     * sin coma, lo mostramos tal cual para no romper nada.
     */
    if (commaIndex === -1) {
      td.textContent = value;
      return;
    }

    const apellidos = value.slice(0, commaIndex).trim();
    const nombre = value.slice(commaIndex + 1).trim();

    if (!nombre || !apellidos) {
      td.textContent = value;
      return;
    }

    const nombreEl = document.createElement("div");
    nombreEl.textContent = nombre;

    const apellidosEl = document.createElement("div");
    apellidosEl.textContent = apellidos;

    td.appendChild(nombreEl);
    td.appendChild(apellidosEl);
  }

  function render(jornada) {
    const seleccionadas = jornada === "todas" ? jornadas : [jornada];
    const normalizar = (texto) => String(texto || "").normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es-ES");
    const consulta = normalizar(busquedaEl.value).trim();
    const partidos = seleccionadas.flatMap((j) =>
      (data.jornadas[j] || []).map((partido) => ({ ...partido, jornada: j }))
    ).filter((partido) => !consulta || normalizar([
      partido.equipo_local, partido.equipo_visitante, partido.arbitro,
      partido.asistente1, partido.asistente2
    ].join(" ")).includes(consulta));

    tbody.innerHTML = "";

    if (partidos.length === 0) {
      estadoEl.textContent = consulta ? "No hay partidos que coincidan con la búsqueda."
        : "No hay partidos guardados para esta selección.";
      return;
    }

    estadoEl.textContent = partidos.length + " partidos";

    for (const p of partidos) {
      const tr = document.createElement("tr");

      const campos = [
        "jornada",
        "equipo_local",
        "equipo_visitante",
        "arbitro",
        "asistente1",
        "asistente2"
      ];

      for (const campo of campos) {
        const td = document.createElement("td");

        if (
          campo === "arbitro" ||
          campo === "asistente1" ||
          campo === "asistente2"
        ) {
          renderOfficialName(td, p[campo]);
        } else {
          td.textContent = p[campo] || "—";
        }

        tr.appendChild(td);
      }

      tbody.appendChild(tr);
    }
  }

  selectEl.addEventListener("change", () => {
    render(selectEl.value);
  });
  busquedaEl.addEventListener("input", () => render(selectEl.value));

  /*
   * IMPORTANTE:
   *
   * Ahora que existen 34 jornadas, no podemos seleccionar
   * automáticamente la última porque normalmente estará vacía.
   *
   * Buscamos la última jornada que tenga partidos.
   */
  const jornadasConPartidos = jornadas.filter(
    (j) => (data.jornadas[j] || []).length > 0
  );

  const inicial =
    jornadasConPartidos.length > 0
      ? jornadasConPartidos[jornadasConPartidos.length - 1]
      : jornadas[0];

  selectEl.value = inicial;

  render(inicial);
}

main();
