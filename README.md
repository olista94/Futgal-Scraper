# Partidos futgal.es — árbitros y asistentes

Web estática (GitHub Pages) que muestra, para cada jornada, equipo
local, equipo visitante, árbitro y asistentes de una competición de
[futgal.es](https://www.futgal.es). Los datos se actualizan solos cada
día mediante un workflow de GitHub Actions que ejecuta el scraper y
guarda el resultado en `docs/data/partidos.json`.

No necesitas servidor propio: todo corre en GitHub (Actions + Pages).

## Estructura

```
config.json                 -> qué competición/grupo/jornadas scrapear
scraper/futgal_scraper.py   -> el scraper (Python)
scraper/requirements.txt    -> dependencias del scraper
.github/workflows/scrape.yml-> workflow programado que lo ejecuta y hace commit
docs/                        -> la web estática (esto es lo que sirve GitHub Pages)
  index.html
  style.css
  app.js
  data/partidos.json         -> histórico acumulado de la temporada
```

## Puesta en marcha (una sola vez)

1. **Crea el repositorio en GitHub** y sube este contenido:
   ```bash
   git init
   git add .
   git commit -m "Primera versión"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```

2. **Edita `config.json`** con la competición/grupo/temporada/jornadas
   que quieras (los códigos salen de la URL de futgal.es, tal como
   viste al construir la URL original: `CodCompeticion`, `CodGrupo`,
   `CodTemporada`, `Sch_Codigo_Delegacion`, y la lista de `jornadas`
   que quieres publicar, p. ej. `[1,2,3,4,5]`).

3. **Da permiso de escritura al workflow** (para que pueda hacer commit
   del JSON actualizado):
   `Settings` → `Actions` → `General` → `Workflow permissions` →
   marca **"Read and write permissions"** → Guardar.

4. **Activa GitHub Pages**:
   `Settings` → `Pages` → en "Build and deployment" → Source:
   **Deploy from a branch** → Branch: **main**, carpeta **/docs** →
   Guardar.
   GitHub te dará una URL tipo `https://TU_USUARIO.github.io/TU_REPO/`.

5. **Lanza el workflow manualmente la primera vez** (no hace falta
   esperar al cron diario):
   pestaña `Actions` → `Actualizar datos de partidos` →
   `Run workflow`.
   Al terminar, habrá hecho commit de `docs/data/partidos.json` con
   los datos reales.

6. Entra en la URL de GitHub Pages: ya deberías ver la tabla con el
   selector de jornada, opción «Todas las jornadas» y buscador por equipo
   o colegiado. Los nombres se muestran en dos líneas: nombre y apellidos.

## Histórico de partidos

El scraper consulta las 34 jornadas configuradas y conserva los partidos
que ya estaban guardados si Futgal devuelve una jornada vacía, incompleta
o falla. Los partidos se identifican por su URL: cuando vuelven a aparecer,
se actualizan sin duplicarlos. Así se mantienen las jornadas que Futgal
deja de publicar. Se siguen consultando todas para recoger correcciones.

El campo `source` identifica competición, grupo y temporada para no mezclar
datos al cambiar la configuración. El primer histórico antiguo sin ese
campo se acepta si coinciden los nombres de competición y grupo; elimina
el JSON antiguo si cambias de temporada antes de esa primera actualización.
Si el JSON no se puede leer, la ejecución aborta sin sobrescribirlo.

Un partido que desaparece de Futgal se conserva en el histórico. Si se
anula definitivamente, su eliminación debe hacerse manualmente en el JSON.
La fecha «Actualizado» corresponde a la ejecución del scraper, incluso si
parte de los datos se ha conservado de ejecuciones anteriores.

Se han recuperado de los commits anteriores los partidos de las jornadas
2 a 5 de esta temporada. La jornada 1 no tenía partidos guardados en Git;
las siguientes se incorporarán cuando Futgal los publique y el scraper
pueda extraerlos.

## Comprobar el histórico sin consultar Futgal

```bash
python -m unittest discover -s tests
node --test tests/app.test.cjs
```

## Cambiar la frecuencia de actualización

En `.github/workflows/scrape.yml`, la línea:
```yaml
- cron: "0 6 * * *"
```
usa formato cron estándar (UTC). Por ejemplo `"0 */6 * * *"` para
cada 6 horas, o `"0 6 * * 1-5"` para solo días laborables.

También puedes lanzarlo a mano cuando quieras desde la pestaña
Actions → Run workflow.

## Ejecutarlo en local (para probar antes de subir)

```bash
cd scraper
pip install -r requirements.txt
cd ..
python3 scraper/futgal_scraper.py --config config.json --output docs/data/partidos.json
```

## Nota sobre el `robots.txt` de futgal.es

El sitio indica en su `robots.txt` que no permite acceso automatizado.
Ejecutar este scraper (aquí o en GitHub Actions) es responsabilidad
tuya: usa un `--delay` razonable entre peticiones (ya viene puesto a
1.5s en el workflow) y valora contactar con la RFGF si vas a darle un
uso continuado o público a gran escala.
