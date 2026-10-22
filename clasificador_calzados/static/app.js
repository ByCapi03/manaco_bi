/**
 * app.js
 * Lógica Frontend y Control Operativo para MANACO BI.
 * 6 Vistas: Resumen, Costos y precios, Inventario, Productos, Predicciones y Ventas.
 * Fuente de datos directa de BDatos_MANACO.xlsx y PostgreSQL.
 */

const AppState = {
    sonidoHabilitado: true,
    camaraActiva: false,
    intervaloEscaneo: null,
    scannerAbierto: false,
    bloqueadoPorRegistro: false,
    audioCtx: null,
    charts: {},
    monedaActual: "USD",
    tasaCambio: 6.96,
    resumenMedida: "USD",
    catalogoProductos: [],
    inventarioCategorias: [],
    ultimoCalculoCostos: null,
    productoSeleccionadoReposicion: null,
    ultimaCategoriaDetectada: null,
    productos: {
        datos: null,
        origenVentas: "sintetico", // "sintetico" o "registrado"
        rankingMetrica: "pares", // "pares" o "contribucion"
        productoSeleccionadoId: 1,
        filtroCategoriaDecision: "TODAS"
    },
    contextoExterno: {
        anio: "TODOS",
        flujo: "TODOS",
        medida: "USD",
        datos: null
    },
    demanda: {
        datos: null,
        productoSeleccionadoId: null,
        leadTimeFiltro: null,
        stockSeguridadFiltro: null
    }
};

// ==========================================================================
// INICIALIZACIÓN AL CARGAR EL DOM
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    configurarTabs();
    configurarControlesMoneda();
    configurarModales();
    configurarFiltrosResumen();
    configurarCamaraInventario();
    configurarCalculadoraCostos();
    configurarTabProductos();
    configurarTabDemanda();

    // Cargar datos iniciales
    cargarOpcionesFiltrosResumen();
    cargarDashboardResumen();
    cargarDatosGenerales();
    cargarDatosProductos();
    cargarMetricasCanales();
    cargarPrediccionesExcel();
    cargarPrediccionesOperativas();

    // Actualización periódica silenciosa de inventario cada 10s si la cámara no está activa
    setInterval(() => {
        if (!AppState.camaraActiva) {
            cargarDatosGenerales(false);
        }
    }, 10000);
});

// ==========================================================================
// GESTIÓN DE NAVEGACIÓN (6 PESTAÑAS EXACTAS)
// ==========================================================================
function configurarTabs() {
    const botones = document.querySelectorAll(".nav-tab-btn");
    const paneles = document.querySelectorAll(".tab-pane");

    botones.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            if (!targetId) return;

            botones.forEach(b => b.classList.remove("active"));
            paneles.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }

            // Si se activa la pestaña Productos, refrescar o redimensionar
            if (targetId === "tab-productos") {
                if (!AppState.productos.datos) {
                    cargarDatosProductos();
                } else {
                    setTimeout(() => {
                        if (AppState.charts.prodCostoPrecio) AppState.charts.prodCostoPrecio.resize();
                        if (AppState.charts.prodRanking) AppState.charts.prodRanking.resize();
                        if (AppState.charts.extPart) AppState.charts.extPart.resize();
                    }, 120);
                }
            }

            // Si se activa la pestaña Planificación de demanda, refrescar o redimensionar
            if (targetId === "tab-predicciones") {
                if (!AppState.demanda || !AppState.demanda.datos) {
                    cargarPrediccionesOperativas();
                } else {
                    setTimeout(() => {
                        if (AppState.charts.planHistoricoPronostico) AppState.charts.planHistoricoPronostico.resize();
                        if (AppState.charts.planDisponibilidadNecesidad) AppState.charts.planDisponibilidadNecesidad.resize();
                        if (AppState.charts.planExcel) AppState.charts.planExcel.resize();
                    }, 120);
                }
            }

            // Redibujar gráficos si se abren pestañas con canvas
            setTimeout(() => {
                Object.values(AppState.charts).forEach(ch => {
                    if (ch && typeof ch.resize === "function") ch.resize();
                });
            }, 100);
        });
    });
}

// ==========================================================================
// CONTROL DE MONEDA GLOBAL
// ==========================================================================
function configurarControlesMoneda() {
    const btnUsd = document.getElementById("btn-currency-usd");
    const btnBob = document.getElementById("btn-currency-bob");
    const inputTc = document.getElementById("input-tc-global");

    if (btnUsd && btnBob) {
        btnUsd.addEventListener("click", () => {
            AppState.monedaActual = "USD";
            btnUsd.classList.add("active");
            btnBob.classList.remove("active");
            actualizarVisualizacionMonedas();
            cargarDashboardResumen();
        });

        btnBob.addEventListener("click", () => {
            AppState.monedaActual = "BOB";
            btnBob.classList.add("active");
            btnUsd.classList.remove("active");
            actualizarVisualizacionMonedas();
            cargarDashboardResumen();
        });
    }

    if (inputTc) {
        inputTc.addEventListener("change", (e) => {
            const nuevoTc = parseFloat(e.target.value);
            if (nuevoTc > 0) {
                AppState.tasaCambio = nuevoTc;
                actualizarVisualizacionMonedas();
                cargarDashboardResumen();
            }
        });
    }
}

function formatearMoneda(valUsd, valBob = null) {
    if (valUsd === null || valUsd === undefined) return "--";
    const u = parseFloat(valUsd) || 0;
    if (AppState.monedaActual === "BOB") {
        const b = valBob !== null ? parseFloat(valBob) : (u * AppState.tasaCambio);
        return `Bs. ${b.toLocaleString("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return `$ ${u.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
}

function actualizarVisualizacionMonedas() {
    cargarDatosGenerales(false);
    if (AppState.ultimoCalculoCostos) {
        actualizarKpisYGraficosCostos(AppState.ultimoCalculoCostos);
    }
    if (AppState.productos && AppState.productos.datos) {
        actualizarKpisProductosTab();
        renderizarGraficoCostoPrecio();
        renderizarGraficoRanking();
        renderizarTablaDecisionProductos();
    }
}

// ==========================================================================
// MODALES (METODOLOGÍA Y CONFIGURACIÓN)
// ==========================================================================
function configurarModales() {
    // Modal Metodología
    const modalMet = document.getElementById("modal-metodologia");
    const btnVerMet = document.getElementById("btn-ver-metodologia");
    const btnCerrarMet = document.getElementById("btn-cerrar-metodologia");
    const btnEntendidoMet = document.getElementById("btn-entendido-metodologia");

    if (btnVerMet && modalMet) {
        btnVerMet.addEventListener("click", () => modalMet.style.display = "flex");
    }
    if (btnCerrarMet && modalMet) {
        btnCerrarMet.addEventListener("click", () => modalMet.style.display = "none");
    }
    if (btnEntendidoMet && modalMet) {
        btnEntendidoMet.addEventListener("click", () => modalMet.style.display = "none");
    }

    // Modal Configuración
    const modalConf = document.getElementById("modal-config-estado");
    const btnAbrirConf = document.getElementById("btn-abrir-config-modal");
    const btnCerrarConf = document.getElementById("btn-cerrar-config-modal");
    const btnGuardarConf = document.getElementById("btn-guardar-config-modal");

    if (btnAbrirConf && modalConf) {
        btnAbrirConf.addEventListener("click", () => modalConf.style.display = "flex");
    }
    if (btnCerrarConf && modalConf) {
        btnCerrarConf.addEventListener("click", () => modalConf.style.display = "none");
    }
    if (btnGuardarConf && modalConf) {
        btnGuardarConf.addEventListener("click", () => modalConf.style.display = "none");
    }

    // Modal Reposición
    const modalRep = document.getElementById("modal-reposicion-overlay");
    const btnCerrarRep = document.getElementById("btn-cancelar-reposicion");
    const btnCancelModalRep = document.getElementById("btn-cancelar-modal-rep");
    const btnConfirmarRep = document.getElementById("btn-confirmar-reposicion-action");

    if (btnCerrarRep && modalRep) {
        btnCerrarRep.addEventListener("click", () => modalRep.style.display = "none");
    }
    if (btnCancelModalRep && modalRep) {
        btnCancelModalRep.addEventListener("click", () => modalRep.style.display = "none");
    }
    if (btnConfirmarRep) {
        btnConfirmarRep.addEventListener("click", ejecutarConfirmacionReposicion);
    }
}

// ==========================================================================
// 1. DASHBOARD RESUMEN
// ==========================================================================
async function cargarOpcionesFiltrosResumen() {
    try {
        const res = await fetch("/api/comercio/opciones");
        const json = await res.json();
        if (!json.exito) return;

        const selSocio = document.getElementById("filtro-resumen-socio");
        if (selSocio && json.socios) {
            selSocio.innerHTML = `<option value="TODOS">Todos</option>` +
                json.socios.map(s => `<option value="${s}">${s}</option>`).join("");
        }
    } catch (e) {
        console.warn("Error cargando opciones de socios:", e);
    }
}

function configurarFiltrosResumen() {
    const selAnio = document.getElementById("filtro-resumen-anio");
    const selSocio = document.getElementById("filtro-resumen-socio");
    const selCat = document.getElementById("filtro-resumen-categoria");
    const btnLimpiar = document.getElementById("btn-limpiar-filtros-resumen");

    const btnMedUsd = document.getElementById("btn-medida-usd");
    const btnMedPares = document.getElementById("btn-medida-pares");

    const dispararCarga = () => cargarDashboardResumen();

    if (selAnio) selAnio.addEventListener("change", dispararCarga);
    if (selSocio) selSocio.addEventListener("change", dispararCarga);
    if (selCat) selCat.addEventListener("change", dispararCarga);

    if (btnLimpiar) {
        btnLimpiar.addEventListener("click", () => {
            if (selAnio) selAnio.value = "TODOS";
            if (selSocio) selSocio.value = "TODOS";
            if (selCat) selCat.value = "TODOS";
            cargarDashboardResumen();
        });
    }

    if (btnMedUsd && btnMedPares) {
        btnMedUsd.addEventListener("click", () => {
            AppState.resumenMedida = "USD";
            btnMedUsd.classList.add("active");
            btnMedPares.classList.remove("active");
            cargarDashboardResumen();
        });

        btnMedPares.addEventListener("click", () => {
            AppState.resumenMedida = "PARES";
            btnMedPares.classList.add("active");
            btnMedUsd.classList.remove("active");
            cargarDashboardResumen();
        });
    }
}

async function cargarDashboardResumen() {
    const selAnio = document.getElementById("filtro-resumen-anio");
    const selSocio = document.getElementById("filtro-resumen-socio");
    const selCat = document.getElementById("filtro-resumen-categoria");

    const anio = selAnio ? selAnio.value : "TODOS";
    const socio = selSocio ? selSocio.value : "TODOS";
    const cat = selCat ? selCat.value : "TODOS";
    const medida = AppState.resumenMedida || "USD";

    const params = new URLSearchParams();
    if (anio !== "TODOS") params.append("anio", anio);
    if (socio !== "TODOS") params.append("socio", socio);
    if (cat !== "TODOS") params.append("codigo_sa6", cat);
    params.append("medida", medida);

    try {
        const res = await fetch(`/api/resumen/metricas?${params.toString()}`);
        const json = await res.json();
        if (!json.exito) return;

        actualizarTarjetasResumen(json);
        renderizarGraficosResumen(json);
    } catch (e) {
        console.error("Error al cargar métricas de resumen:", e);
    }
}

function actualizarTarjetasResumen(data) {
    const elValImp = document.getElementById("val-resumen-importado");
    const elValExp = document.getElementById("val-resumen-exportado");
    const elValPar = document.getElementById("val-resumen-pares");

    if (!data.hay_datos || data.total_registros === 0) {
        if (elValImp) elValImp.textContent = "Sin datos";
        if (elValExp) elValExp.textContent = "Sin datos";
        if (elValPar) elValPar.textContent = "Sin datos";
        return;
    }

    const kpis = data.kpis || {};

    if (elValImp) {
        if (AppState.monedaActual === "BOB") {
            const bob = (kpis.valor_importado_usd || 0) * AppState.tasaCambio;
            elValImp.textContent = `Bs. ${bob.toLocaleString("es-BO", { maximumFractionDigits: 0 })}`;
        } else {
            elValImp.textContent = `$ ${(kpis.valor_importado_usd || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })} USD`;
        }
        elValImp.title = formatearMoneda(kpis.valor_importado_usd);
    }

    if (elValExp) {
        if (AppState.monedaActual === "BOB") {
            const bob = (kpis.valor_exportado_usd || 0) * AppState.tasaCambio;
            elValExp.textContent = `Bs. ${bob.toLocaleString("es-BO", { maximumFractionDigits: 0 })}`;
        } else {
            elValExp.textContent = `$ ${(kpis.valor_exportado_usd || 0).toLocaleString("en-US", { maximumFractionDigits: 0 })} USD`;
        }
        elValExp.title = formatearMoneda(kpis.valor_exportado_usd);
    }

    if (elValPar) {
        elValPar.textContent = `${(kpis.pares_registrados || 0).toLocaleString()} pares`;
        elValPar.title = `Importación: ${(kpis.pares_importados || 0).toLocaleString()} pares | Exportación: ${(kpis.pares_exportados || 0).toLocaleString()} pares`;
    }
}

function renderizarGraficosResumen(data) {
    const esPares = (AppState.resumenMedida === "PARES");
    const sufijo = esPares ? " pares" : " USD";
    const prefijo = esPares ? "" : "$ ";

    const colorImp = "#0ea5e9";
    const colorExp = "#f59e0b";

    const emptyAnios = document.getElementById("empty-anios");
    const emptySocios = document.getElementById("empty-socios");
    const emptyCats = document.getElementById("empty-categorias");

    if (!data.hay_datos || data.total_registros === 0) {
        if (emptyAnios) emptyAnios.style.display = "flex";
        if (emptySocios) emptySocios.style.display = "flex";
        if (emptyCats) emptyCats.style.display = "flex";
        return;
    }

    if (emptyAnios) emptyAnios.style.display = "none";
    if (emptySocios) emptySocios.style.display = "none";
    if (emptyCats) emptyCats.style.display = "none";

    // 1. Gráfico: Importaciones vs Exportaciones por año
    const ctxAnios = document.getElementById("chart-resumen-anios");
    if (ctxAnios) {
        if (AppState.charts.resumenAnios) AppState.charts.resumenAnios.destroy();

        const labels = data.grafico_anios.anios;
        const impData = esPares ? data.grafico_anios.importacion_pares : data.grafico_anios.importacion_usd;
        const expData = esPares ? data.grafico_anios.exportacion_pares : data.grafico_anios.exportacion_usd;

        AppState.charts.resumenAnios = new Chart(ctxAnios, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Importación",
                        data: impData,
                        backgroundColor: colorImp,
                        borderRadius: 4
                    },
                    {
                        label: "Exportación",
                        data: expData,
                        backgroundColor: colorExp,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            callback: (v) => prefijo + v.toLocaleString() + sufijo
                        }
                    },
                    x: { grid: { color: "rgba(255,255,255,0.06)" } }
                },
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, color: "#94a3b8" } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${prefijo}${ctx.parsed.y.toLocaleString()}${sufijo}`
                        }
                    }
                }
            }
        });
    }

    // 2. Gráfico: Principales socios comerciales (Top 10 agrupadas horizontalmente)
    const ctxSocios = document.getElementById("chart-resumen-socios");
    if (ctxSocios) {
        if (AppState.charts.resumenSocios) AppState.charts.resumenSocios.destroy();

        const labels = data.grafico_socios.socios;
        const impData = esPares ? data.grafico_socios.importacion_pares : data.grafico_socios.importacion_usd;
        const expData = esPares ? data.grafico_socios.exportacion_pares : data.grafico_socios.exportacion_usd;

        AppState.charts.resumenSocios = new Chart(ctxSocios, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Importación",
                        data: impData,
                        backgroundColor: colorImp,
                        borderRadius: 4
                    },
                    {
                        label: "Exportación",
                        data: expData,
                        backgroundColor: colorExp,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            callback: (v) => prefijo + v.toLocaleString() + sufijo
                        }
                    },
                    y: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { color: "#f8fafc", font: { size: 11 } } }
                },
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, color: "#94a3b8" } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${prefijo}${ctx.parsed.x.toLocaleString()}${sufijo}`
                        }
                    }
                }
            }
        });
    }

    // 3. Gráfico: Comparación por categoría
    const ctxCats = document.getElementById("chart-resumen-categorias");
    if (ctxCats) {
        if (AppState.charts.resumenCategorias) AppState.charts.resumenCategorias.destroy();

        const labels = data.grafico_categorias.categorias;
        const impData = esPares ? data.grafico_categorias.importacion_pares : data.grafico_categorias.importacion_usd;
        const expData = esPares ? data.grafico_categorias.exportacion_pares : data.grafico_categorias.exportacion_usd;

        AppState.charts.resumenCategorias = new Chart(ctxCats, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Importación",
                        data: impData,
                        backgroundColor: colorImp,
                        borderRadius: 4
                    },
                    {
                        label: "Exportación",
                        data: expData,
                        backgroundColor: colorExp,
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            callback: (v) => prefijo + v.toLocaleString() + sufijo
                        }
                    },
                    x: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { font: { size: 11 } } }
                },
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, color: "#94a3b8" } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${prefijo}${ctx.parsed.y.toLocaleString()}${sufijo}`
                        }
                    }
                }
            }
        });
    }
}

// ==========================================================================
// 2. COSTOS Y PRECIOS
// ==========================================================================
// ==========================================================================
// 1. COSTOS Y MÁRGENES (¿Fabricar o importar?)
// ==========================================================================

function parsearNumeroFormulario(val, def = 0) {
    if (val === null || val === undefined) return def;
    if (typeof val === "number") return Number.isFinite(val) ? val : def;
    let s = String(val).trim();
    if (!s) return def;
    s = s.replace(",", ".");
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : def;
}

function invalidarCalculoCostos(motivo = "Parámetros modificados. Presiona 'Calcular decisión y precio'.") {
    AppState.ultimoCalculoCostos = null;
    const btnAplicar = document.getElementById("btn-aplicar-precio-catalogo");
    if (btnAplicar) btnAplicar.disabled = true;

    const badge = document.getElementById("badge-estado-parametros");
    if (badge) {
        badge.textContent = "Parámetros modificados";
        badge.className = "badge-tag tag-amber";
    }

    const msg = document.getElementById("calc-status-msg");
    if (msg) msg.textContent = motivo;
}

function configurarCalculadoraCostos() {
    const btnCalc = document.getElementById("btn-ejecutar-calculo-costos");
    const btnAplicar = document.getElementById("btn-aplicar-precio-catalogo");
    const selProd = document.getElementById("calc-producto-dest");
    const selCat = document.getElementById("calc-categoria");

    const referenciasBaseSA6 = {
        640411: 27.80,
        640399: 26.15,
        640420: 45.53
    };

    if (selProd) {
        selProd.addEventListener("change", () => {
            const opt = selProd.selectedOptions[0];
            if (opt) {
                const sa6 = opt.getAttribute("data-sa6");
                const cv = opt.getAttribute("data-cv");
                const gastos = opt.getAttribute("data-gastos");
                const margen = opt.getAttribute("data-margen");

                if (sa6 && selCat) selCat.value = sa6;
                if (cv && document.getElementById("calc-costo-var-fab")) {
                    document.getElementById("calc-costo-var-fab").value = cv;
                }
                if (gastos && document.getElementById("calc-gastos-importacion")) {
                    document.getElementById("calc-gastos-importacion").value = gastos;
                }
                if (margen && document.getElementById("calc-margen-objetivo")) {
                    document.getElementById("calc-margen-objetivo").value = margen;
                }
                if (sa6 && document.getElementById("calc-ref-comercial")) {
                    document.getElementById("calc-ref-comercial").value = (referenciasBaseSA6[sa6] || 27.80).toFixed(2);
                }
            }
            invalidarCalculoCostos();
        });
    }

    if (selCat) {
        selCat.addEventListener("change", () => {
            const sa6 = selCat.value;
            const refInput = document.getElementById("calc-ref-comercial");
            if (refInput && referenciasBaseSA6[sa6]) {
                refInput.value = referenciasBaseSA6[sa6].toFixed(2);
            }
            invalidarCalculoCostos();
        });
    }

    const inputsMonitoreados = [
        "calc-volumen-pares",
        "calc-costo-var-fab",
        "calc-costo-fijo-evitable",
        "calc-gastos-importacion",
        "calc-ref-comercial",
        "calc-costo-fijo-permanente",
        "calc-margen-objetivo",
        "calc-alternativa-precio"
    ];

    inputsMonitoreados.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("input", () => invalidarCalculoCostos());
            el.addEventListener("change", () => invalidarCalculoCostos());
        }
    });

    if (btnCalc) btnCalc.addEventListener("click", ejecutarCalculoCostos);
    if (btnAplicar) btnAplicar.addEventListener("click", aplicarPrecioPropuestoAlCatalogo);

    // Ejecución inicial automática para que la pestaña abra con datos válidos
    ejecutarCalculoCostos();
}

async function ejecutarCalculoCostos() {
    const statusMsg = document.getElementById("calc-status-msg");
    const badge = document.getElementById("badge-estado-parametros");
    const btnAplicar = document.getElementById("btn-aplicar-precio-catalogo");

    const sa6 = parseInt(document.getElementById("calc-categoria")?.value || "640411");
    const idProd = parseInt(document.getElementById("calc-producto-dest")?.value || "1");
    const q = parsearNumeroFormulario(document.getElementById("calc-volumen-pares")?.value, 0);
    const cvFab = parsearNumeroFormulario(document.getElementById("calc-costo-var-fab")?.value, -1);
    const cfEvit = parsearNumeroFormulario(document.getElementById("calc-costo-fijo-evitable")?.value, -1);
    const gastosImp = parsearNumeroFormulario(document.getElementById("calc-gastos-importacion")?.value, -1);
    const refComercial = parsearNumeroFormulario(document.getElementById("calc-ref-comercial")?.value, -1);
    const cfPerm = parsearNumeroFormulario(document.getElementById("calc-costo-fijo-permanente")?.value, 0);
    const margen = parsearNumeroFormulario(document.getElementById("calc-margen-objetivo")?.value, -1);
    const altPrecio = document.getElementById("calc-alternativa-precio")?.value || "recomendada";

    // 1. Validaciones requeridas
    if (q <= 0) {
        mostrarEstadoInvalidoCostos("Completa los parámetros: la cantidad de pares debe ser mayor que 0.");
        return;
    }
    if (cvFab < 0 || cfEvit < 0 || gastosImp < 0 || refComercial < 0 || cfPerm < 0) {
        mostrarEstadoInvalidoCostos("Completa los parámetros: los costos no pueden ser negativos.");
        return;
    }
    if (margen < 0 || margen >= 100) {
        mostrarEstadoInvalidoCostos("Completa los parámetros: el margen objetivo debe estar entre 0% y menos de 100%.");
        return;
    }

    const payload = {
        codigo_sa6: sa6,
        id_producto: idProd,
        cantidad_pares: q,
        costo_variable_unitario_fab: cvFab,
        costos_fijos_evitables: cfEvit,
        costos_fijos_permanentes: cfPerm,
        gastos_importacion: gastosImp,
        referencia_comercial: refComercial,
        margen_objetivo_pct: margen,
        alternativa_precio: altPrecio,
        moneda: "USD",
        tasa_cambio: AppState.tasaCambio
    };

    try {
        if (statusMsg) statusMsg.textContent = "Calculando escenario...";
        const res = await fetch("/api/escenarios/calcular", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!res.ok || !data.exito) {
            mostrarEstadoInvalidoCostos(data.error || "Completa los parámetros.");
            return;
        }

        AppState.ultimoCalculoCostos = data;
        actualizarKpisYGraficosCostos(data);

        if (btnAplicar) btnAplicar.disabled = false;
        if (badge) {
            badge.textContent = "Cálculo actualizado";
            badge.className = "badge-tag tag-emerald";
        }
        if (statusMsg) statusMsg.textContent = "Cálculo actualizado con éxito.";
    } catch (e) {
        console.error("Error en cálculo de costos:", e);
        mostrarEstadoInvalidoCostos("Error de conexión al calcular costos.");
    }
}

function mostrarEstadoInvalidoCostos(mensaje) {
    AppState.ultimoCalculoCostos = null;

    const btnAplicar = document.getElementById("btn-aplicar-precio-catalogo");
    if (btnAplicar) btnAplicar.disabled = true;

    const badge = document.getElementById("badge-estado-parametros");
    if (badge) {
        badge.textContent = "Parámetros incompletos";
        badge.className = "badge-tag tag-amber";
    }

    const statusMsg = document.getElementById("calc-status-msg");
    if (statusMsg) statusMsg.textContent = mensaje;

    document.getElementById("kpi-costo-fab-unit").textContent = "--";
    document.getElementById("kpi-costo-fab-total").textContent = "Lote: --";
    document.getElementById("kpi-costo-imp-unit").textContent = "--";
    document.getElementById("kpi-costo-imp-total").textContent = "Lote: --";

    const decEl = document.getElementById("kpi-decision-estrategica");
    if (decEl) {
        decEl.textContent = "COMPLETA LOS PARÁMETROS";
        decEl.className = "kpi-decision-text";
        decEl.style.color = "#94a3b8";
    }

    const ahorroEl = document.getElementById("kpi-ahorro-estimado");
    if (ahorroEl) ahorroEl.textContent = "No se recomienda fabricar ni importar hasta completar los parámetros.";

    document.getElementById("kpi-precio-propuesto").textContent = "--";
    document.getElementById("kpi-precio-sub").textContent = "Alternativa utilizada: --";

    // Mostrar overlays en gráficos
    const emptyComp = document.getElementById("empty-costos-comp");
    if (emptyComp) emptyComp.style.display = "flex";
    const emptyIndiff = document.getElementById("empty-costos-indiff");
    if (emptyIndiff) emptyIndiff.style.display = "flex";

    if (AppState.charts.costosComp) {
        AppState.charts.costosComp.destroy();
        AppState.charts.costosComp = null;
    }
    if (AppState.charts.costosIndiff) {
        AppState.charts.costosIndiff.destroy();
        AppState.charts.costosIndiff = null;
    }
}

function actualizarKpisYGraficosCostos(data) {
    if (!data || !data.fabricacion || !data.importacion) return;

    // Ocultar overlays
    const emptyComp = document.getElementById("empty-costos-comp");
    if (emptyComp) emptyComp.style.display = "none";
    const emptyIndiff = document.getElementById("empty-costos-indiff");
    if (emptyIndiff) emptyIndiff.style.display = "none";

    const fab = data.fabricacion;
    const imp = data.importacion;
    const diff = data.analisis_diferencial;
    const precio = data.precio_propuesto;
    const q = data.configuracion.cantidad_pares;

    // 1. Tarjetas de Resultados
    // Card 1: Fabricar
    document.getElementById("kpi-costo-fab-unit").textContent = `${formatearMoneda(fab.costo_unitario_total_usd, fab.costo_unitario_total_bob)} / par`;
    document.getElementById("kpi-costo-fab-total").textContent = `Lote (${q.toLocaleString()} p): ${formatearMoneda(fab.costo_total_lote_usd, fab.costo_total_lote_bob)}`;

    // Card 2: Importar
    document.getElementById("kpi-costo-imp-unit").textContent = `${formatearMoneda(imp.costo_unitario_total_usd, imp.costo_unitario_total_bob)} / par`;
    document.getElementById("kpi-costo-imp-total").textContent = `Lote (${q.toLocaleString()} p): ${formatearMoneda(imp.costo_total_lote_usd, imp.costo_total_lote_bob)}`;

    // Card 3: Decisión / Diferencia
    const decEl = document.getElementById("kpi-decision-estrategica");
    decEl.textContent = (diff.decision_texto || diff.decision_recomendada).toUpperCase();
    if (diff.decision_recomendada === "FABRICAR") {
        decEl.className = "kpi-decision-text text-emerald";
    } else if (diff.decision_recomendada === "IMPORTAR") {
        decEl.className = "kpi-decision-text text-cyan";
    } else {
        decEl.className = "kpi-decision-text text-amber";
    }

    const ahorroFmt = formatearMoneda(diff.ahorro_lote_usd, diff.ahorro_lote_bob);
    const difFmt = formatearMoneda(diff.diferencia_costo_usd, diff.diferencia_costo_bob);
    if (diff.decision_recomendada === "EQUIVALENTE") {
        document.getElementById("kpi-ahorro-estimado").textContent = `Diferencia de ${difFmt} dentro de tolerancia (±$5.00 USD).`;
    } else {
        document.getElementById("kpi-ahorro-estimado").textContent = `${diff.conclusion_texto} (Ahorro lote: ${ahorroFmt})`;
    }

    // Card 4: Precio Propuesto
    document.getElementById("kpi-precio-propuesto").textContent = `${formatearMoneda(precio.precio_sugerido_usd, precio.precio_sugerido_bob)}`;
    document.getElementById("kpi-precio-sub").textContent = `Alternativa: ${precio.alternativa_label} (Margen: ${precio.margen_objetivo_pct}%)`;

    // 2. Gráficos
    renderizarGraficosCostos(data);
}

function renderizarGraficosCostos(data) {
    const fab = data.fabricacion;
    const imp = data.importacion;
    const diff = data.analisis_diferencial;
    const q = data.configuracion.cantidad_pares;
    const esBob = (AppState.monedaActual === "BOB");
    const tc = AppState.tasaCambio;

    // ==========================================
    // Gráfico 1: Desglose de componentes unitarios
    // ==========================================
    const ctxComp = document.getElementById("chart-costos-comparacion");
    if (ctxComp) {
        if (AppState.charts.costosComp) AppState.charts.costosComp.destroy();

        // Valores unitarios por componente
        const cvFabVal = esBob ? fab.costo_variable_unitario_bob : fab.costo_variable_unitario_usd;
        const cfEvitUnitVal = esBob ? (fab.costos_fijos_evitables_bob / q) : (fab.costos_fijos_evitables_usd / q);

        const refImpVal = esBob ? imp.referencia_comercial_bob : imp.referencia_comercial_usd;
        const gastosImpVal = esBob ? imp.gastos_adicionales_bob : imp.gastos_adicionales_usd;

        const subBar = document.getElementById("chart-subtitulo-barras");
        if (subBar) {
            subBar.textContent = `Costos por par para lote de ${q.toLocaleString()} pares en ${AppState.monedaActual}`;
        }

        AppState.charts.costosComp = new Chart(ctxComp, {
            type: "bar",
            data: {
                labels: ["Fabricar localmente", "Importar calzado"],
                datasets: [
                    {
                        label: "Costo variable directo / Compra base",
                        data: [cvFabVal, refImpVal],
                        backgroundColor: "#0ea5e9",
                        borderRadius: 4
                    },
                    {
                        label: "Costos fijos evitables / Gastos importación",
                        data: [cfEvitUnitVal, gastosImpVal],
                        backgroundColor: "#f59e0b",
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true,
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: { color: "#e2e8f0", font: { weight: "600" } }
                    },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            color: "#94a3b8",
                            callback: v => (esBob ? "Bs. " : "$ ") + v.toFixed(2)
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: { boxWidth: 12, color: "#94a3b8" }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                const val = ctx.parsed.y;
                                return `  ${ctx.dataset.label}: ${formatearMoneda(esBob ? val / tc : val, esBob ? val : val * tc)} / par`;
                            },
                            footer: tooltipItems => {
                                let total = 0;
                                tooltipItems.forEach(item => total += item.parsed.y);
                                return `Total unitario: ${formatearMoneda(esBob ? total / tc : total, esBob ? total : total * tc)} / par`;
                            }
                        }
                    }
                }
            }
        });
    }

    // ==========================================
    // Gráfico 2: Costo según cantidad (Eje X numérico {x, y})
    // ==========================================
    const ctxIndiff = document.getElementById("chart-costos-indiferencia");
    if (ctxIndiff) {
        if (AppState.charts.costosIndiff) AppState.charts.costosIndiff.destroy();

        const curva = data.curva_volumen || [];
        const datosFab = curva.map(pt => ({
            x: pt.x,
            y: esBob ? pt.costo_fabricar_bob : pt.costo_fabricar_usd
        }));
        const datosImp = curva.map(pt => ({
            x: pt.x,
            y: esBob ? pt.costo_importar_bob : pt.costo_importar_usd
        }));

        const subIndiff = document.getElementById("chart-subtitulo-indiff");
        if (subIndiff) {
            subIndiff.textContent = diff.mensaje_indiferencia || "Costo total acumulado por volumen";
        }

        AppState.charts.costosIndiff = new Chart(ctxIndiff, {
            type: "line",
            data: {
                datasets: [
                    {
                        label: "Costo Total Fabricar",
                        data: datosFab,
                        borderColor: "#0ea5e9",
                        backgroundColor: "rgba(14, 165, 233, 0.12)",
                        borderWidth: 2,
                        tension: 0.05,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    },
                    {
                        label: "Costo Total Importar",
                        data: datosImp,
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.12)",
                        borderWidth: 2,
                        tension: 0.05,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: "linear",
                        title: {
                            display: true,
                            text: "Cantidad de pares (volumen numérico)",
                            color: "#94a3b8",
                            font: { size: 11 }
                        },
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            color: "#94a3b8",
                            callback: v => v.toLocaleString() + " pares"
                        }
                    },
                    y: {
                        type: "linear",
                        title: {
                            display: true,
                            text: `Costo total del lote (${esBob ? "Bs." : "$us."})`,
                            color: "#94a3b8",
                            font: { size: 11 }
                        },
                        grid: { color: "rgba(255,255,255,0.06)" },
                        ticks: {
                            color: "#94a3b8",
                            callback: v => (esBob ? "Bs. " : "$ ") + v.toLocaleString()
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        labels: { boxWidth: 12, color: "#94a3b8" }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => {
                                const val = ctx.parsed.y;
                                return `${ctx.dataset.label}: ${formatearMoneda(esBob ? val / tc : val, esBob ? val : val * tc)} (para ${ctx.parsed.x.toLocaleString()} pares)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

async function aplicarPrecioPropuestoAlCatalogo() {
    if (!AppState.ultimoCalculoCostos) {
        alert("Primero ejecuta el cálculo de costos para obtener un precio propuesto válido.");
        return;
    }

    const data = AppState.ultimoCalculoCostos;
    const precioObj = data.precio_propuesto;
    const idProd = parseInt(document.getElementById("calc-producto-dest")?.value || "1");
    const selProd = document.getElementById("calc-producto-dest");
    const nombreProd = selProd?.selectedOptions[0]?.text || `Producto #${idProd}`;

    const precioUsd = precioObj.precio_sugerido_usd;
    const precioBob = precioObj.precio_sugerido_bob;

    const confirma = confirm(
        `¿Deseas aplicar el precio sugerido de $ ${precioUsd.toFixed(2)} USD (Bs. ${precioBob.toFixed(2)}) a "${nombreProd}"?\n\n` +
        `Esta acción actualiza únicamente el catálogo de este producto; las existencias actuales y las ventas históricas no se modificarán.`
    );
    if (!confirma) return;

    try {
        const res = await fetch("/api/inventario/aplicar-precio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id_producto: idProd,
                nuevo_precio_usd: precioUsd,
                nuevo_precio_bs: precioBob,
                responsable: "Gerente Comercial Manaco"
            })
        });
        const respJson = await res.json();
        if (respJson.exito) {
            reproducirSonido("exito");
            alert(`Precio de catálogo para ${nombreProd} actualizado exitosamente a $ ${precioUsd.toFixed(2)} USD (Bs. ${precioBob.toFixed(2)}). Existencias y ventas históricas no modificadas.`);
            cargarDatosGenerales(false);
        } else {
            alert(`Error al actualizar precio: ${respJson.error || 'Desconocido'}`);
        }
    } catch (e) {
        console.error("Error aplicando precio:", e);
        alert("Ocurrió un error de conexión al aplicar el precio al catálogo.");
    }
}

// ==========================================================================
// 3. INVENTARIO (CON CÁMARA INTEGRADA)
// ==========================================================================
function configurarCamaraInventario() {
    const btnToggleScanner = document.getElementById("btn-toggle-escanear-calzado");
    const panelScanner = document.getElementById("panel-escanear-calzado");
    const btnToggleCam = document.getElementById("btn-toggle-camara");

    if (btnToggleScanner && panelScanner) {
        btnToggleScanner.addEventListener("click", () => {
            AppState.scannerAbierto = !AppState.scannerAbierto;
            panelScanner.style.display = AppState.scannerAbierto ? "block" : "none";
            btnToggleScanner.textContent = AppState.scannerAbierto ? "✖ Cerrar Escáner" : "📷 Escanear calzado";

            if (!AppState.scannerAbierto && AppState.camaraActiva) {
                detenerCamara();
            }
        });
    }

    if (btnToggleCam) {
        btnToggleCam.addEventListener("click", () => {
            if (AppState.camaraActiva) {
                detenerCamara();
            } else {
                iniciarCamara();
            }
        });
    }
}

async function iniciarCamara() {
    const videoEl = document.getElementById("webcam-video");
    const btnToggle = document.getElementById("btn-toggle-camara");
    const badgeEstado = document.getElementById("badge-cam-estado");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "environment" },
            audio: false
        });

        videoEl.srcObject = stream;
        await videoEl.play();

        AppState.camaraActiva = true;
        if (badgeEstado) {
            badgeEstado.textContent = "Cámara activa";
            badgeEstado.className = "badge-tag tag-emerald";
        }
        if (btnToggle) {
            btnToggle.textContent = "Detener Cámara";
            btnToggle.classList.add("btn-danger-soft");
        }

        AppState.intervaloEscaneo = setInterval(capturarYClasificarFrame, 400);
    } catch (err) {
        console.error("Error al acceder a la cámara:", err);
        alert("No se pudo iniciar la cámara web. Verifica los permisos de video en tu navegador.");
    }
}

function detenerCamara() {
    const videoEl = document.getElementById("webcam-video");
    const btnToggle = document.getElementById("btn-toggle-camara");
    const badgeEstado = document.getElementById("badge-cam-estado");
    const infoDetectada = document.getElementById("cam-info-detectada");
    const compatSec = document.getElementById("cam-productos-compatibles");

    if (AppState.intervaloEscaneo) {
        clearInterval(AppState.intervaloEscaneo);
        AppState.intervaloEscaneo = null;
    }

    if (videoEl && videoEl.srcObject) {
        videoEl.srcObject.getTracks().forEach(t => t.stop());
        videoEl.srcObject = null;
    }

    AppState.camaraActiva = false;
    AppState.ultimaCategoriaDetectada = null;

    if (badgeEstado) {
        badgeEstado.textContent = "Cámara apagada";
        badgeEstado.className = "badge-tag";
    }
    if (btnToggle) {
        btnToggle.textContent = "Iniciar Cámara";
        btnToggle.classList.remove("btn-danger-soft");
    }

    // Ocultar categoría y productos cuando la cámara está apagada
    if (infoDetectada) infoDetectada.style.display = "none";
    if (compatSec) compatSec.style.display = "none";
}

async function capturarYClasificarFrame() {
    if (!AppState.camaraActiva || AppState.bloqueadoPorRegistro) return;

    const videoEl = document.getElementById("webcam-video");
    const canvas = document.getElementById("canvas-captura");
    if (!videoEl || videoEl.videoWidth === 0) return;

    canvas.width = 224;
    canvas.height = 224;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, 224, 224);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);

    try {
        const res = await fetch("/clasificar_frame", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: dataUrl })
        });
        const pred = await res.json();
        procesarDeteccionCamara(pred);
    } catch (e) {
        console.warn("Fallo frame inferencia:", e);
    }
}

function procesarDeteccionCamara(pred) {
    const infoDetectada = document.getElementById("cam-info-detectada");
    const nombreCatEl = document.getElementById("cam-categoria-nombre");
    const sa6El = document.getElementById("cam-categoria-sa6");
    const compatSec = document.getElementById("cam-productos-compatibles");
    const botonesContainer = document.getElementById("cam-botones-modelos");

    if (!pred || pred.clase === "sin_calzado" || pred.confianza < 0.35) {
        if (infoDetectada) infoDetectada.style.display = "none";
        if (compatSec) compatSec.style.display = "none";
        AppState.ultimaCategoriaDetectada = null;
        return;
    }

    const sa6 = pred.codigo_sa6;
    AppState.ultimaCategoriaDetectada = sa6;

    if (infoDetectada) infoDetectada.style.display = "block";
    if (nombreCatEl) nombreCatEl.textContent = pred.clase_nombre || "Calzado detectado";
    if (sa6El) sa6El.textContent = `SA6: ${sa6} • Confianza: ${Math.round(pred.confianza * 100)}%`;

    // Filtrar productos compatibles
    const prodsCompatibles = AppState.catalogoProductos.filter(p => p.codigo_sa6 === sa6);

    if (compatSec && botonesContainer && prodsCompatibles.length > 0) {
        compatSec.style.display = "block";
        botonesContainer.innerHTML = prodsCompatibles.map(p => `
            <button class="compatible-btn" onclick="confirmarIngresoCalzado(${p.id_producto}, '${p.nombre_producto}')">
                <span>+1 par: <strong>${p.nombre_producto}</strong></span>
                <span class="text-muted-sm">Stock: ${p.stock_actual}</span>
            </button>
        `).join("");
    }
}

async function confirmarIngresoCalzado(idProducto, nombreProducto) {
    if (AppState.bloqueadoPorRegistro) return;
    AppState.bloqueadoPorRegistro = true;

    try {
        const res = await fetch("/api/inventario/movimiento", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id_producto: idProducto,
                tipo_accion: "INGRESO_IA",
                cantidad: 1,
                canal_venta: "Almacén Central Manaco",
                responsable: "Cámara IA Almacén"
            })
        });
        const respJson = await res.json();

        if (respJson.exito) {
            reproducirSonido("exito");

            // Mostrar confirmación breve
            const banner = document.getElementById("cam-confirmacion-banner");
            const texto = document.getElementById("cam-confirmacion-texto");
            const nuevoStock = respJson.nuevo_stock ?? respJson.stock_resultante ?? respJson.datos?.stock_resultante ?? "--";

            if (banner && texto) {
                texto.textContent = `✓ Ingreso confirmado: +1 par de ${nombreProducto}. Nuevo stock: ${nuevoStock} pares.`;
                banner.style.display = "block";
                setTimeout(() => { banner.style.display = "none"; }, 3500);
            }

            // Actualizar stock local y tablas
            cargarDatosGenerales(false);
        } else {
            alert(`Error: ${respJson.error || 'No se pudo registrar el ingreso'}`);
        }
    } catch (e) {
        console.error("Error confirmando ingreso:", e);
    } finally {
        setTimeout(() => { AppState.bloqueadoPorRegistro = false; }, 1200);
    }
}

// ==========================================================================
// CARGA GENERAL DE INVENTARIO Y CATÁLOGO
// ==========================================================================
async function cargarDatosGenerales(animar = true) {
    try {
        const res = await fetch("/api/inventario/resumen");
        const json = await res.json();
        if (!json.exito) return;

        const kpis = json.datos.kpis || {};
        const prods = json.datos.productos || {};
        const cats = json.datos.categorias || {};

        AppState.catalogoProductos = kpis.inventario_detalle || [];
        AppState.inventarioCategorias = kpis.categorias_detalle || [];

        actualizarKpisInventario(kpis);
        renderizarGraficosInventario(prods, cats, animar);
        poblarTablaInventario(AppState.catalogoProductos);

        if (!AppState.ultimoCalculoCostos) {
            ejecutarCalculoCostos();
        }
    } catch (e) {
        console.warn("Error cargando resumen de inventario:", e);
    }
}

function actualizarKpisInventario(kpis) {
    const kpiTot = document.getElementById("kpi-inv-total-pares");
    const capOcup = document.getElementById("kpi-inv-cap-ocupacion");
    const kpiEnt = document.getElementById("kpi-inv-entradas");
    const kpiIa = document.getElementById("kpi-inv-ia-count");
    const kpiSal = document.getElementById("kpi-inv-salidas");
    const kpiAlert = document.getElementById("kpi-inv-alertas-count");
    const kpiAlertDesc = document.getElementById("kpi-inv-alertas-desc");

    const totalPares = kpis.total_stock_actual || 90;
    const capMax = kpis.capacidad_almacen || 900;
    const pctOcup = Math.min(100, Math.round((totalPares / capMax) * 100));

    if (kpiTot) kpiTot.textContent = totalPares.toLocaleString();
    if (capOcup) capOcup.textContent = `Capacidad ocupada: ${pctOcup}% (de ${capMax} pares)`;
    if (kpiEnt) kpiEnt.textContent = (kpis.total_ingresos_pares || 0).toLocaleString();
    if (kpiIa) kpiIa.textContent = `${kpis.ingresos_ia_count || 0} escaneos registrados`;
    if (kpiSal) kpiSal.textContent = (kpis.total_salidas_pares || 0).toLocaleString();

    const alertas = kpis.productos_alerta_stock || 0;
    if (kpiAlert) kpiAlert.textContent = alertas;
    if (kpiAlertDesc) {
        kpiAlertDesc.textContent = alertas > 0 ? `${alertas} modelo(s) bajo el stock mínimo` : "Todos los modelos con stock de seguridad";
    }
}

function renderizarGraficosInventario(prods, cats, animar) {
    const ctxProd = document.getElementById("chart-inv-productos");
    if (ctxProd && prods.labels) {
        if (AppState.charts.invProd) AppState.charts.invProd.destroy();

        AppState.charts.invProd = new Chart(ctxProd, {
            type: "bar",
            data: {
                labels: prods.labels,
                datasets: [
                    { label: "Stock Actual (pares)", data: prods.stock_actual, backgroundColor: "#0ea5e9", borderRadius: 4 },
                    { label: "Stock Mínimo Seguridad", data: prods.stock_minimo, type: "line", borderColor: "#f59e0b", borderDash: [5, 5], borderWidth: 2 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animar ? { duration: 400 } : false,
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" } },
                    x: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { font: { size: 10 } } }
                },
                plugins: { legend: { position: "top", labels: { boxWidth: 12, color: "#94a3b8" } } }
            }
        });
    }

    const ctxCat = document.getElementById("chart-inv-categorias");
    if (ctxCat && cats.labels) {
        if (AppState.charts.invCat) AppState.charts.invCat.destroy();

        AppState.charts.invCat = new Chart(ctxCat, {
            type: "bar",
            data: {
                labels: cats.labels,
                datasets: [{
                    label: "Pares en Almacén",
                    data: cats.stock_actual,
                    backgroundColor: ["#0ea5e9", "#f59e0b", "#e11d48"],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animar ? { duration: 400 } : false,
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" } },
                    x: { grid: { color: "rgba(255,255,255,0.06)" } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

function poblarTablaInventario(catalogo) {
    const tbody = document.getElementById("tbody-inventario-catalogo");
    if (!tbody) return;

    if (catalogo.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" class="text-center text-muted">Cargando inventario...</td></tr>`;
        return;
    }

    tbody.innerHTML = catalogo.map(p => {
        const esAlerta = p.stock_actual <= p.stock_minimo;
        const badge = esAlerta ? `<span class="badge-tag tag-alert">⚠️ Stock Bajo</span>` : `<span class="badge-tag tag-emerald">✓ Óptimo</span>`;

        return `
            <tr>
                <td><strong>#${p.id_producto}</strong></td>
                <td><code>${p.codigo_sku}</code></td>
                <td>${p.codigo_sa6}</td>
                <td>${p.categoria_corta}</td>
                <td>${p.linea || 'Básico'}</td>
                <td><strong>${p.nombre_producto}</strong></td>
                <td><strong>${p.stock_actual} pares</strong></td>
                <td>${p.stock_minimo} pares</td>
                <td>$ ${p.precio_unitario_usd.toFixed(2)}</td>
                <td>Bs. ${p.precio_unitario_bs.toFixed(2)}</td>
                <td>${badge}</td>
            </tr>
        `;
    }).join("");
}

// ==========================================================================
// 4. PRODUCTOS: COMPARAR, DECIDIR Y CONTEXTUALIZAR
// ==========================================================================
function configurarTabProductos() {
    // Selector de producto evaluado
    const selProd = document.getElementById("sel-producto-evaluar");
    if (selProd) {
        selProd.addEventListener("change", (e) => {
            AppState.productos.productoSeleccionadoId = parseInt(e.target.value, 10);
            actualizarKpisProductosTab();
        });
    }

    // Toggle origen de ventas (Simulación 12M vs Registros en Almacén)
    const btnSint = document.getElementById("btn-origen-sintetico");
    const btnReg = document.getElementById("btn-origen-registrado");
    if (btnSint && btnReg) {
        btnSint.addEventListener("click", () => {
            AppState.productos.origenVentas = "sintetico";
            btnSint.classList.add("active");
            btnReg.classList.remove("active");
            actualizarKpisProductosTab();
            renderizarGraficoRanking();
            renderizarTablaDecisionProductos();
        });

        btnReg.addEventListener("click", () => {
            AppState.productos.origenVentas = "registrado";
            btnReg.classList.add("active");
            btnSint.classList.remove("active");
            actualizarKpisProductosTab();
            renderizarGraficoRanking();
            renderizarTablaDecisionProductos();
        });
    }

    // Botón reintentar en caja de estado
    const btnReintentar = document.getElementById("btn-reintentar-productos");
    if (btnReintentar) {
        btnReintentar.addEventListener("click", () => {
            cargarDatosProductos();
        });
    }

    // Selector métrica ranking (Pares vendidos vs Contribución)
    const btnRankPares = document.getElementById("btn-ranking-pares");
    const btnRankContrib = document.getElementById("btn-ranking-contribucion");
    if (btnRankPares && btnRankContrib) {
        btnRankPares.addEventListener("click", () => {
            AppState.productos.rankingMetrica = "pares";
            btnRankPares.classList.add("active");
            btnRankContrib.classList.remove("active");
            const sub = document.getElementById("ranking-subtitulo");
            if (sub) sub.textContent = "Ordenado por pares vendidos en el período";
            renderizarGraficoRanking();
        });

        btnRankContrib.addEventListener("click", () => {
            AppState.productos.rankingMetrica = "contribucion";
            btnRankContrib.classList.add("active");
            btnRankPares.classList.remove("active");
            const sub = document.getElementById("ranking-subtitulo");
            if (sub) sub.textContent = "Ordenado por contribución monetaria (Ingresos - Costos atribuibles)";
            renderizarGraficoRanking();
        });
    }

    // Filtro por categoría en la tabla de decisión
    const filtroCatDec = document.getElementById("filtro-prod-categoria-comparar");
    if (filtroCatDec) {
        filtroCatDec.addEventListener("change", (e) => {
            AppState.productos.filtroCategoriaDecision = e.target.value;
            renderizarTablaDecisionProductos();
        });
    }

    // Contexto externo collapsible & filtros
    const panelExt = document.getElementById("panel-contexto-externo");
    if (panelExt) {
        panelExt.addEventListener("toggle", () => {
            if (panelExt.open && !AppState.contextoExterno.datos) {
                cargarContextoExternoProductos();
            }
        });
    }

    const selExtAnio = document.getElementById("filtro-ext-anio");
    const selExtFlujo = document.getElementById("filtro-ext-flujo");
    const btnExtUsd = document.getElementById("btn-ext-medida-usd");
    const btnExtPares = document.getElementById("btn-ext-medida-pares");

    if (selExtAnio) {
        selExtAnio.addEventListener("change", (e) => {
            AppState.contextoExterno.anio = e.target.value;
            cargarContextoExternoProductos();
        });
    }

    if (selExtFlujo) {
        selExtFlujo.addEventListener("change", (e) => {
            AppState.contextoExterno.flujo = e.target.value;
            cargarContextoExternoProductos();
        });
    }

    if (btnExtUsd && btnExtPares) {
        btnExtUsd.addEventListener("click", () => {
            AppState.contextoExterno.medida = "USD";
            btnExtUsd.classList.add("active");
            btnExtPares.classList.remove("active");
            cargarContextoExternoProductos();
        });

        btnExtPares.addEventListener("click", () => {
            AppState.contextoExterno.medida = "PARES";
            btnExtPares.classList.add("active");
            btnExtUsd.classList.remove("active");
            cargarContextoExternoProductos();
        });
    }
}

async function cargarDatosProductos() {
    const estadoBox = document.getElementById("productos-estado-box");
    const estadoMsg = document.getElementById("productos-estado-msg");

    if (estadoBox && estadoMsg) {
        estadoMsg.textContent = "Cargando catálogo y métricas de productos...";
        estadoBox.style.display = "flex";
        estadoBox.className = "status-callout-box status-loading";
    }

    try {
        const res = await fetch("/api/productos/detalle");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();

        if (!json.exito || !json.productos || json.productos.length === 0) {
            throw new Error(json.error || "No se recibieron productos del servidor");
        }

        AppState.productos.datos = json;
        if (estadoBox) estadoBox.style.display = "none";

        actualizarKpisProductosTab();
        renderizarGraficoCostoPrecio();
        renderizarGraficoRanking();
        renderizarTablaDecisionProductos();
    } catch (e) {
        console.error("Error al cargar productos:", e);
        if (estadoBox && estadoMsg) {
            estadoMsg.textContent = `Error al cargar datos de productos: ${e.message || "Fallo de conexión"}`;
            estadoBox.style.display = "flex";
            estadoBox.className = "status-callout-box status-error";
        }
    }
}

function actualizarKpisProductosTab() {
    if (!AppState.productos.datos) return;
    const { kpis, productos } = AppState.productos.datos;

    // KPI 1: Productos activos
    const elSkus = document.getElementById("kpi-prod-total-skus");
    if (elSkus) elSkus.textContent = kpis.total_productos_activos || productos.length || 6;

    // Producto seleccionado
    const prodSelId = AppState.productos.productoSeleccionadoId;
    const p = productos.find(x => x.id_producto === prodSelId) || productos[0];
    if (!p) return;

    // Moneda activa
    const esBob = AppState.monedaActual === "BOB";
    const precio = esBob ? p.precio_unitario_bs : p.precio_unitario_usd;
    const costo = esBob ? p.costo_referencia_bs : p.costo_referencia_usd;
    const diferencia = esBob ? p.diferencia_bs : p.diferencia_usd;
    const prefijo = esBob ? "Bs. " : "$ ";

    // KPI 2: Diferencia estimada por par
    const elDif = document.getElementById("kpi-prod-diferencia-par");
    const elDifSub = document.getElementById("kpi-prod-diferencia-sub");
    if (elDif) {
        elDif.textContent = `${prefijo}${diferencia.toFixed(2)}`;
    }
    if (elDifSub) {
        elDifSub.textContent = `Precio (${prefijo}${precio.toFixed(2)}) - Costo ref. (${prefijo}${costo.toFixed(2)})`;
    }

    // KPI 3: Margen del escenario seleccionado
    const elMargen = document.getElementById("kpi-prod-margen-escenario");
    const elMargenSub = document.getElementById("kpi-prod-margen-sub");
    if (elMargen) {
        elMargen.textContent = `${p.margen_sobre_venta_pct.toFixed(1)}%`;
    }
    if (elMargenSub) {
        elMargenSub.textContent = `Margen s/venta para ${p.codigo_sku} (${p.linea})`;
    }

    // KPI 4: Unidades vendidas en el período indicando procedencia
    const elVentas = document.getElementById("kpi-prod-ventas-tot");
    const elVentasFuente = document.getElementById("kpi-prod-ventas-fuente");
    const origen = AppState.productos.origenVentas;

    if (origen === "sintetico") {
        const totalPares = kpis.ventas_sinteticas_totales_pares || 6959;
        if (elVentas) elVentas.textContent = totalPares.toLocaleString();
        if (elVentasFuente) elVentasFuente.textContent = `Procedencia: Simulación 12M (${p.codigo_sku}: ${p.ventas_sinteticas_pares.toLocaleString()} pares)`;
    } else {
        const totalPares = kpis.ventas_registradas_totales_pares || 0;
        if (elVentas) elVentas.textContent = totalPares.toLocaleString();
        if (elVentasFuente) elVentasFuente.textContent = `Procedencia: Registros en Almacén (${p.codigo_sku}: ${p.ventas_registradas_pares.toLocaleString()} pares)`;
    }
}

function renderizarGraficoCostoPrecio() {
    const canvas = document.getElementById("chart-prod-costo-precio");
    if (!canvas || !AppState.productos.datos) return;
    const productos = AppState.productos.datos.productos || [];
    if (productos.length === 0) return;

    if (AppState.charts.prodCostoPrecio) {
        AppState.charts.prodCostoPrecio.destroy();
    }

    const esBob = AppState.monedaActual === "BOB";
    const prefijo = esBob ? "Bs. " : "$ ";
    const labels = productos.map(p => `${p.codigo_sku} (${p.linea})`);

    const dataCostos = productos.map(p => esBob ? p.costo_referencia_bs : p.costo_referencia_usd);
    const dataPrecios = productos.map(p => esBob ? p.precio_unitario_bs : p.precio_unitario_usd);

    AppState.charts.prodCostoPrecio = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: `Costo Estimado (${prefijo.trim()}/par)`,
                    data: dataCostos,
                    backgroundColor: "#f59e0b",
                    borderRadius: 4
                },
                {
                    label: `Precio Propuesto (${prefijo.trim()}/par)`,
                    data: dataPrecios,
                    backgroundColor: "#0ea5e9",
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: {
                        callback: v => `${prefijo}${v}`
                    }
                },
                x: {
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: { font: { size: 10 } }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: { boxWidth: 12, color: "#94a3b8" }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = productos[context.dataIndex];
                            if (!p) return "";
                            const costo = esBob ? p.costo_referencia_bs : p.costo_referencia_usd;
                            const precio = esBob ? p.precio_unitario_bs : p.precio_unitario_usd;
                            const dif = esBob ? p.diferencia_bs : p.diferencia_usd;
                            return [
                                `Costo estimado: ${prefijo}${costo.toFixed(2)}/par`,
                                `Precio propuesto: ${prefijo}${precio.toFixed(2)}/par`,
                                `Diferencia estimada: ${prefijo}${dif.toFixed(2)}/par`,
                                `Margen s/venta: ${p.margen_sobre_venta_pct.toFixed(1)}%`
                            ];
                        }
                    }
                }
            }
        }
    });
}

function renderizarGraficoRanking() {
    const canvas = document.getElementById("chart-prod-ranking");
    if (!canvas || !AppState.productos.datos) return;
    const productos = [...(AppState.productos.datos.productos || [])];
    if (productos.length === 0) return;

    if (AppState.charts.prodRanking) {
        AppState.charts.prodRanking.destroy();
    }

    const origen = AppState.productos.origenVentas;
    const metrica = AppState.productos.rankingMetrica;
    const esBob = AppState.monedaActual === "BOB";
    const tc = AppState.tasaCambio;
    const prefijo = esBob ? "Bs. " : "$ ";

    // Calcular valor según origen y métrica
    productos.forEach(p => {
        if (origen === "sintetico") {
            p._valRanking = metrica === "pares" 
                ? p.ventas_sinteticas_pares 
                : (esBob ? p.contribucion_sintetica_usd * tc : p.contribucion_sintetica_usd);
        } else {
            p._valRanking = metrica === "pares"
                ? p.ventas_registradas_pares
                : (esBob ? p.contribucion_registrada_usd * tc : p.contribucion_registrada_usd);
        }
    });

    // Ordenar de mayor a menor
    productos.sort((a, b) => b._valRanking - a._valRanking);

    const labels = productos.map(p => `${p.codigo_sku} (${p.linea})`);
    const values = productos.map(p => p._valRanking);
    const labelSerie = metrica === "pares" 
        ? `Pares vendidos (${origen === 'sintetico' ? 'Simulación 12M' : 'Almacén'})`
        : `Contribución (${prefijo.trim()}) (${origen === 'sintetico' ? 'Simulación 12M' : 'Almacén'})`;

    AppState.charts.prodRanking = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: labelSerie,
                data: values,
                backgroundColor: metrica === "pares" ? "#10b981" : "#8b5cf6",
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: {
                        callback: v => metrica === "pares" ? v.toLocaleString() : `${prefijo}${v.toLocaleString()}`
                    }
                },
                y: {
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: { font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw || 0;
                            if (metrica === "pares") {
                                return `Ventas: ${val.toLocaleString()} pares`;
                            } else {
                                return `Contribución: ${prefijo}${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                            }
                        }
                    }
                }
            }
        }
    });
}

function renderizarTablaDecisionProductos() {
    const tbody = document.getElementById("tbody-productos-decision");
    if (!tbody || !AppState.productos.datos) return;
    let prods = AppState.productos.datos.productos || [];

    const filtroCat = AppState.productos.filtroCategoriaDecision;
    if (filtroCat && filtroCat !== "TODAS") {
        prods = prods.filter(p => String(p.codigo_sa6) === String(filtroCat));
    }

    if (prods.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No hay productos en esta selección.</td></tr>`;
        return;
    }

    const origen = AppState.productos.origenVentas;
    const esBob = AppState.monedaActual === "BOB";
    const tc = AppState.tasaCambio;
    const prefijo = esBob ? "Bs. " : "$ ";

    tbody.innerHTML = prods.map(p => {
        const pares = origen === "sintetico" ? p.ventas_sinteticas_pares : p.ventas_registradas_pares;
        const precio = esBob ? p.precio_unitario_bs : p.precio_unitario_usd;
        const costo = esBob ? p.costo_referencia_bs : p.costo_referencia_usd;
        
        let contrib = origen === "sintetico" ? p.contribucion_sintetica_usd : p.contribucion_registrada_usd;
        if (esBob) contrib = contrib * tc;

        // Criterio analítico ponderado (volumen, margen, stock y período)
        let criterioHtml = "";
        if (origen === "registrado" && pares === 0) {
            criterioHtml = `<span class="badge-tag tag-gray">Sin ventas en almacén</span>`;
        } else if (p.stock_actual <= p.stock_minimo) {
            criterioHtml = `<span class="badge-tag tag-alert">⚠️ Reponer stock antes de promocionar</span>`;
        } else if (p.linea === "Básico" && pares > 1000) {
            criterioHtml = `<span class="badge-tag tag-cyan">Mantener • Base de rotación y volumen</span>`;
        } else if (p.linea === "Confort" && p.margen_sobre_venta_pct > 38) {
            criterioHtml = `<span class="badge-tag tag-purple">Promocionar • Alto aporte unitario</span>`;
        } else {
            criterioHtml = `<span class="badge-tag tag-emerald">Mantener en catálogo</span>`;
        }

        return `
            <tr>
                <td><strong>${p.nombre_producto}</strong> (<code>${p.codigo_sku}</code>)</td>
                <td><span class="badge-tag ${p.linea === 'Confort' ? 'tag-purple' : 'tag-cyan'}">${p.linea}</span></td>
                <td><strong>${pares.toLocaleString()}</strong> pares</td>
                <td>${prefijo}${precio.toFixed(2)}</td>
                <td>${prefijo}${costo.toFixed(2)}</td>
                <td><strong class="text-emerald">${prefijo}${contrib.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></td>
                <td>${p.stock_actual} pares</td>
                <td>${criterioHtml}</td>
            </tr>
        `;
    }).join("");
}

async function cargarContextoExternoProductos() {
    const { anio, flujo, medida } = AppState.contextoExterno;
    const txtMayor = document.getElementById("txt-mayor-participacion");
    const canvas = document.getElementById("chart-ext-participacion");
    if (!canvas) return;

    try {
        const url = `/api/productos/participacion_exterior?anio=${encodeURIComponent(anio)}&flujo=${encodeURIComponent(flujo)}&medida=${encodeURIComponent(medida)}`;
        const res = await fetch(url);
        const json = await res.json();
        if (!json.exito) return;

        AppState.contextoExterno.datos = json;

        if (txtMayor) {
            if (json.mayor_participacion) {
                txtMayor.textContent = `Mayor participación en los registros: ${json.mayor_participacion} con ${json.mayor_porcentaje}%`;
            } else {
                txtMayor.textContent = "Sin datos registrados para los filtros seleccionados";
            }
        }

        if (AppState.charts.extPart) {
            AppState.charts.extPart.destroy();
        }

        const cats = json.categorias || [];
        const labels = cats.map(c => c.nombre);
        const dataValues = cats.map(c => c.porcentaje);

        AppState.charts.extPart = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: ["#0ea5e9", "#f59e0b", "#e11d48"],
                    borderWidth: 1,
                    borderColor: "rgba(255,255,255,0.1)"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "right",
                        labels: { boxWidth: 12, color: "#94a3b8", font: { size: 10 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const item = cats[idx];
                                const unidad = medida === "USD" ? "$ USD" : "pares";
                                return [
                                    `${item.nombre}: ${item.porcentaje}%`,
                                    `Total: ${item.valor.toLocaleString()} ${unidad}`
                                ];
                            }
                        }
                    }
                }
            }
        });
    } catch (e) {
        console.warn("Error cargando contexto externo:", e);
    }
}

// ==========================================================================
// 5. PLANIFICACIÓN DE DEMANDA (PROBLEMA 4)
// ==========================================================================

function configurarTabDemanda() {
    // Selector de producto para Gráfico A
    const selProd = document.getElementById("select-prod-grafico-demanda");
    if (selProd) {
        selProd.addEventListener("change", (e) => {
            const id = parseInt(e.target.value);
            if (id > 0 && AppState.demanda) {
                AppState.demanda.productoSeleccionadoId = id;
                if (AppState.demanda.datos && AppState.demanda.datos.productos) {
                    renderizarGraficoHistoricoPronostico(AppState.demanda.datos.productos);
                }
            }
        });
    }

    // Toggle de Ajustar Parámetros
    const btnToggleParam = document.getElementById("btn-toggle-parametros-demanda");
    const panelParam = document.getElementById("panel-ajuste-parametros-demanda");
    if (btnToggleParam && panelParam) {
        btnToggleParam.addEventListener("click", () => {
            const visible = panelParam.style.display !== "none";
            panelParam.style.display = visible ? "none" : "block";
        });
    }

    // Botón Aplicar Parámetros
    const btnAplicarParam = document.getElementById("btn-aplicar-parametros-demanda");
    if (btnAplicarParam) {
        btnAplicarParam.addEventListener("click", () => {
            const inputLt = document.getElementById("input-demanda-lead-time");
            const inputSs = document.getElementById("input-demanda-stock-seguridad");
            const lt = inputLt && inputLt.value ? parseInt(inputLt.value) : null;
            const ss = inputSs && inputSs.value !== "" ? parseInt(inputSs.value) : null;

            if (lt !== null && lt <= 0) {
                alert("El plazo de reposición debe ser un entero mayor o igual a 1 día.");
                return;
            }
            if (ss !== null && ss < 0) {
                alert("La reserva de seguridad no puede ser un número negativo.");
                return;
            }

            AppState.demanda.leadTimeFiltro = lt;
            AppState.demanda.stockSeguridadFiltro = ss;
            cargarPrediccionesOperativas(true);
        });
    }

    // Botón Restablecer Parámetros
    const btnRestablecerParam = document.getElementById("btn-restablecer-parametros-demanda");
    if (btnRestablecerParam) {
        btnRestablecerParam.addEventListener("click", () => {
            const inputLt = document.getElementById("input-demanda-lead-time");
            const inputSs = document.getElementById("input-demanda-stock-seguridad");
            if (inputLt) inputLt.value = "";
            if (inputSs) inputSs.value = "";
            AppState.demanda.leadTimeFiltro = null;
            AppState.demanda.stockSeguridadFiltro = null;
            cargarPrediccionesOperativas(true);
        });
    }

    // Botón Reintentar carga
    const btnReintentar = document.getElementById("btn-reintentar-demanda");
    if (btnReintentar) {
        btnReintentar.addEventListener("click", () => cargarPrediccionesOperativas(true));
    }

    // Botón Limpiar Pendientes
    const btnResetPend = document.getElementById("btn-reset-pendientes-demanda");
    if (btnResetPend) {
        btnResetPend.addEventListener("click", async () => {
            if (!confirm("¿Desea restablecer a cero todos los pedidos pendientes registrados?")) return;
            try {
                const res = await fetch("/api/predicciones/restablecer-pendientes", { method: "POST" });
                const j = await res.json();
                if (j.exito) {
                    cargarPrediccionesOperativas(true);
                }
            } catch (e) {
                console.error("Error al restablecer pendientes:", e);
            }
        });
    }

    // Botón Abrir Modal de Solicitud de Reposición
    const btnAbrirSol = document.getElementById("btn-abrir-solicitud-demanda");
    if (btnAbrirSol) {
        btnAbrirSol.addEventListener("click", () => abrirModalSolicitudReposicion());
    }

    // Selector de producto dentro del modal
    const modalSelProd = document.getElementById("modal-rep-select-producto");
    if (modalSelProd) {
        modalSelProd.addEventListener("change", (e) => {
            actualizarCamposModalReposicion(parseInt(e.target.value));
        });
    }

    // Cargar gráfico de comercio exterior cuando se expanda el panel
    const panelExcelCollapse = document.getElementById("panel-plan-excel-collapse");
    if (panelExcelCollapse) {
        panelExcelCollapse.addEventListener("toggle", () => {
            if (panelExcelCollapse.open) {
                cargarPrediccionesExcel();
            }
        });
    }
}

async function cargarPrediccionesOperativas(forzar = false) {
    const btnReintentar = document.getElementById("btn-reintentar-demanda");
    if (btnReintentar) btnReintentar.style.display = "none";

    const tbody = document.getElementById("tbody-plan-reposicion");
    if (tbody && !AppState.demanda.datos) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Cargando sugerencias de reposición...</td></tr>`;
    }

    try {
        let url = "/api/predicciones/operativas";
        const params = new URLSearchParams();
        if (AppState.demanda && AppState.demanda.leadTimeFiltro) {
            params.append("lead_time", AppState.demanda.leadTimeFiltro);
        }
        if (AppState.demanda && AppState.demanda.stockSeguridadFiltro !== null && AppState.demanda.stockSeguridadFiltro !== undefined) {
            params.append("stock_seguridad", AppState.demanda.stockSeguridadFiltro);
        }
        const qs = params.toString();
        if (qs) url += "?" + qs;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const json = await res.json();

        if (!json.exito) {
            throw new Error(json.mensaje || json.error || "No se pudo obtener el pronóstico de demanda.");
        }

        AppState.demanda.datos = json;

        // Metadatos unificados
        const kpis = json.totales_resumen || (json.datos && json.datos.kpis) || {};
        const prods = json.productos || (json.datos && json.datos.productos) || [];
        const fuente = json.fuente_datos || (json.datos && json.datos.fuente_datos) || {};

        // 1. Tarjetas de Indicadores (Mismo resultado unificado)
        const el7d = document.getElementById("kpi-plan-ventas-7d");
        const elRepPares = document.getElementById("kpi-plan-pares-reponer");
        const elRepProds = document.getElementById("kpi-plan-prods-reponer");
        const elLeadTime = document.getElementById("kpi-plan-lead-time");

        if (el7d) el7d.textContent = (kpis.total_ventas_previstas_7d !== undefined ? kpis.total_ventas_previstas_7d : 0).toLocaleString();
        if (elRepPares) elRepPares.textContent = (kpis.pares_por_reponer !== undefined ? kpis.pares_por_reponer : 0).toLocaleString();
        if (elRepProds) elRepProds.textContent = `${kpis.productos_por_reponer !== undefined ? kpis.productos_por_reponer : 0}`;
        if (elLeadTime) elLeadTime.textContent = kpis.plazo_comun || "Según producto";

        // 2. Metadatos de procedencia y badge
        const badge = document.getElementById("badge-demanda-fuente");
        if (badge) {
            badge.textContent = fuente.badge_texto || (fuente.es_simulado ? "Pronóstico con ventas simuladas" : "Pronóstico con ventas registradas");
            badge.style.display = "inline-flex";
        }
        const lblPeriodo = document.getElementById("texto-demanda-periodo");
        if (lblPeriodo) {
            lblPeriodo.textContent = fuente.etiqueta_fuente ? `Fuente: ${fuente.etiqueta_fuente}` : "Fuente: Ventas operativas registradas";
        }

        // 3. MAE en desplegable de metodología
        const elMaeMa7 = document.getElementById("mae-valor-ma7");
        const elMaeNaive = document.getElementById("mae-valor-naive");
        if (elMaeMa7) elMaeMa7.textContent = kpis.mae_promedio_general !== undefined ? kpis.mae_promedio_general.toFixed(2) : "--";
        if (elMaeNaive) elMaeNaive.textContent = kpis.mae_naive_general !== undefined ? kpis.mae_naive_general.toFixed(2) : "--";

        // 4. Selector de productos para Gráfico A
        poblarSelectorProductoDemanda(prods);

        // 5. Manejo independiente de componentes: un fallo no bloquea a los demás
        // A. Tabla simplificada
        try {
            poblarTablaReposicion(prods);
        } catch (errTab) {
            console.error("Error al poblar tabla de reposición:", errTab);
            if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center text-rose">Error al renderizar tabla: ${errTab.message}</td></tr>`;
        }

        // B. Gráfico A: Histórico reciente y pronóstico 7D
        try {
            renderizarGraficoHistoricoPronostico(prods);
        } catch (errChartA) {
            console.error("Error al renderizar Gráfico A (Pronóstico):", errChartA);
        }

        // C. Gráfico B: Disponibilidad y necesidad agrupadas
        try {
            renderizarGraficoDisponibilidadNecesidad(prods);
        } catch (errChartB) {
            console.error("Error al renderizar Gráfico B (Disponibilidad y necesidad):", errChartB);
        }

    } catch (e) {
        console.error("Error general en cargarPrediccionesOperativas:", e);
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center" style="padding:20px;color:var(--manaco-crimson);">
                        <p style="margin-bottom:8px;">⚠️ Error al cargar datos de planificación: ${e.message}</p>
                        <button class="btn btn-secondary btn-sm" onclick="cargarPrediccionesOperativas(true)">🔄 Reintentar</button>
                    </td>
                </tr>
            `;
        }
        if (btnReintentar) btnReintentar.style.display = "inline-flex";
    }
}

function poblarSelectorProductoDemanda(prods) {
    const sel = document.getElementById("select-prod-grafico-demanda");
    if (!sel || !prods || prods.length === 0) return;

    const valorPrevio = AppState.demanda.productoSeleccionadoId;
    sel.innerHTML = prods.map(p => {
        const sufijo = p.faltante_cobertura > 0 ? ` (Faltante: ${p.faltante_cobertura} p.)` : " (Cubierto)";
        return `<option value="${p.id_producto}">[${p.sku}] ${p.nombre_producto}${sufijo}</option>`;
    }).join("");

    if (valorPrevio && prods.some(p => p.id_producto === valorPrevio)) {
        sel.value = valorPrevio;
    } else {
        const conFaltante = prods.find(p => p.faltante_cobertura > 0);
        AppState.demanda.productoSeleccionadoId = conFaltante ? conFaltante.id_producto : prods[0].id_producto;
        sel.value = AppState.demanda.productoSeleccionadoId;
    }
}

function poblarTablaReposicion(prods) {
    const tbody = document.getElementById("tbody-plan-reposicion");
    if (!tbody) return;

    if (!prods || prods.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">No se encontraron productos en el inventario.</td></tr>`;
        return;
    }

    tbody.innerHTML = prods.map(p => {
        let badgeEstado;
        if (p.estado === "Historial insuficiente") {
            badgeEstado = `<span class="badge-tag tag-amber" title="${p.mensaje_estado || 'Datos insuficientes'}">Historial insuficiente</span>`;
        } else if (p.faltante_cobertura > 0) {
            badgeEstado = `<span class="badge-tag tag-alert">Bajo cobertura</span>`;
        } else {
            badgeEstado = `<span class="badge-tag tag-emerald">Cubierto</span>`;
        }

        const pendientesHtml = p.pendientes_recibir > 0
            ? `<span class="badge-tag tag-emerald">+${p.pendientes_recibir} pares</span>`
            : `<span class="text-muted-sm">0 pares</span>`;

        const faltanteHtml = p.faltante_cobertura > 0
            ? `<strong style="color:var(--manaco-crimson);font-size:13px;">${p.faltante_cobertura}</strong> <span class="text-muted-sm">pares</span>`
            : `<strong class="text-emerald">0</strong> <span class="text-muted-sm">pares</span>`;

        const necesidadDetalle = `${p.necesidad} pares`;
        const necesidadTooltip = `Demanda en plazo: ${p.demanda_plazo} + Reserva: ${p.reserva_seguridad} (Plazo: ${p.lead_time_dias}d)`;

        return `
            <tr>
                <td>
                    <strong>${p.nombre_producto}</strong>
                    <div style="font-size:11px;color:var(--text-muted);font-family:'JetBrains Mono',monospace;">${p.sku} &bull; ${p.categoria}</div>
                </td>
                <td><strong style="color:var(--text-primary);">${p.disponible}</strong> <span class="text-muted-sm">pares</span></td>
                <td><span title="${necesidadTooltip}">${necesidadDetalle}</span></td>
                <td>${pendientesHtml}</td>
                <td>${faltanteHtml}</td>
                <td>${badgeEstado}</td>
            </tr>
        `;
    }).join("");
}

function renderizarGraficoHistoricoPronostico(prods) {
    const ctx = document.getElementById("chart-plan-historico-pronostico");
    if (!ctx || !prods || prods.length === 0) return;

    const selId = AppState.demanda.productoSeleccionadoId;
    const prod = prods.find(p => p.id_producto == selId) || prods[0];

    const hist = prod.historico_reciente || { fechas: [], valores: [] };
    const pron = prod.pronostico_7d || { fechas: [], valores_diarios_pares: [] };

    if (hist.fechas.length === 0 && pron.fechas.length === 0) {
        if (AppState.charts.planHistoricoPronostico) AppState.charts.planHistoricoPronostico.destroy();
        return;
    }

    const labels = [...hist.fechas, ...pron.fechas];
    const nHist = hist.valores.length;

    // Serie histórica (línea sólida)
    const datosHist = [...hist.valores, ...Array(pron.fechas.length).fill(null)];

    // Serie pronóstico (línea discontinua conectada desde el último punto histórico)
    const ultimoHistVal = nHist > 0 ? hist.valores[nHist - 1] : (pron.valores_diarios_pares[0] || 0);
    const nullsForecast = Array(Math.max(0, nHist - 1)).fill(null);
    const datosPron = [...nullsForecast, ultimoHistVal, ...pron.valores_diarios_pares];

    if (AppState.charts.planHistoricoPronostico) {
        AppState.charts.planHistoricoPronostico.destroy();
    }

    AppState.charts.planHistoricoPronostico = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: `Historial reciente (${prod.sku})`,
                    data: datosHist,
                    borderColor: "#0ea5e9",
                    backgroundColor: "rgba(14, 165, 233, 0.12)",
                    borderWidth: 2.2,
                    tension: 0.2,
                    fill: false,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    spanGaps: false
                },
                {
                    label: "Pronóstico a 7 días (estimado)",
                    data: datosPron,
                    borderColor: "#10b981",
                    backgroundColor: "rgba(16, 185, 129, 0.08)",
                    borderWidth: 2.2,
                    borderDash: [5, 5],
                    tension: 0.2,
                    fill: false,
                    pointRadius: 4,
                    pointBackgroundColor: "#10b981",
                    pointHoverRadius: 6,
                    spanGaps: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: {
                        color: "#94a3b8",
                        callback: v => `${v} p.`
                    },
                    title: {
                        display: true,
                        text: "Pares / día",
                        color: "#64748b",
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                    ticks: {
                        color: "#94a3b8",
                        maxRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 14
                    }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        boxWidth: 14,
                        color: "#cbd5e1",
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: ctxChart => {
                            if (ctxChart.raw === null || ctxChart.raw === undefined) return null;
                            return `${ctxChart.dataset.label}: ${ctxChart.raw} pares`;
                        }
                    }
                }
            }
        }
    });
}

function renderizarGraficoDisponibilidadNecesidad(prods) {
    const ctx = document.getElementById("chart-plan-disponibilidad-necesidad");
    if (!ctx || !prods || prods.length === 0) return;

    if (AppState.charts.planDisponibilidadNecesidad) {
        AppState.charts.planDisponibilidadNecesidad.destroy();
    }

    const labels = prods.map(p => p.sku);
    const disponibles = prods.map(p => p.disponible);
    const necesidades = prods.map(p => p.necesidad);

    AppState.charts.planDisponibilidadNecesidad = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Stock disponible",
                    data: disponibles,
                    backgroundColor: "#0ea5e9",
                    borderRadius: 4,
                    barPercentage: 0.8,
                    categoryPercentage: 0.7
                },
                {
                    label: "Necesidad (Plazo + Reserva)",
                    data: necesidades,
                    backgroundColor: "#f43f5e",
                    borderRadius: 4,
                    barPercentage: 0.8,
                    categoryPercentage: 0.7
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255,255,255,0.06)" },
                    ticks: {
                        color: "#94a3b8",
                        callback: v => `${v} p.`
                    },
                    title: {
                        display: true,
                        text: "Cantidad de pares",
                        color: "#64748b",
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: { color: "rgba(255,255,255,0.04)" },
                    ticks: { color: "#94a3b8" }
                }
            },
            plugins: {
                legend: {
                    position: "top",
                    labels: {
                        boxWidth: 14,
                        color: "#cbd5e1",
                        font: { size: 11 }
                    }
                },
                tooltip: {
                    callbacks: {
                        afterBody: (items) => {
                            const idx = items[0].dataIndex;
                            const p = prods[idx];
                            const pend = p.pendientes_recibir || 0;
                            const falt = p.faltante_cobertura || 0;
                            return `\nPendiente de recibir: ${pend} pares\nFaltante de cobertura: ${falt} pares`;
                        }
                    }
                }
            }
        }
    });
}

function abrirModalSolicitudReposicion(idProdDefault = null) {
    const modal = document.getElementById("modal-reposicion-overlay");
    const selProd = document.getElementById("modal-rep-select-producto");
    if (!modal || !selProd) return;

    const prods = (AppState.demanda && AppState.demanda.datos && AppState.demanda.datos.productos) || [];
    if (prods.length === 0) {
        alert("No hay productos disponibles para preparar reposición.");
        return;
    }

    selProd.innerHTML = `<option value="">Seleccione un producto...</option>` +
        prods.map(p => {
            const suf = p.faltante_cobertura > 0 ? ` (Faltante sugerido: ${p.faltante_cobertura} p.)` : " (Cubierto)";
            return `<option value="${p.id_producto}">[${p.sku}] ${p.nombre_producto}${suf}</option>`;
        }).join("");

    let targetId = idProdDefault;
    if (!targetId) {
        const conFaltante = prods.find(p => p.faltante_cobertura > 0);
        targetId = conFaltante ? conFaltante.id_producto : prods[0].id_producto;
    }

    selProd.value = targetId;
    actualizarCamposModalReposicion(targetId);

    modal.style.display = "flex";
}

function actualizarCamposModalReposicion(idProd) {
    const prods = (AppState.demanda && AppState.demanda.datos && AppState.demanda.datos.productos) || [];
    const p = prods.find(item => item.id_producto === idProd);

    const elDisp = document.getElementById("modal-rep-disp");
    const elNec = document.getElementById("modal-rep-nec");
    const elPend = document.getElementById("modal-rep-pend");
    const inputCant = document.getElementById("modal-rep-input-cantidad");

    if (!p) {
        if (elDisp) elDisp.textContent = "--";
        if (elNec) elNec.textContent = "--";
        if (elPend) elPend.textContent = "--";
        if (inputCant) inputCant.value = "";
        return;
    }

    if (elDisp) elDisp.textContent = p.disponible;
    if (elNec) elNec.textContent = p.necesidad;
    if (elPend) elPend.textContent = p.pendientes_recibir;

    // Prefill con faltante sugerido si es > 0, o 10
    if (inputCant) {
        inputCant.value = p.faltante_cobertura > 0 ? p.faltante_cobertura : 10;
    }
}

async function ejecutarConfirmacionReposicion() {
    const selProd = document.getElementById("modal-rep-select-producto");
    const inputCant = document.getElementById("modal-rep-input-cantidad");
    const inputResp = document.getElementById("modal-rep-input-responsable");
    const modal = document.getElementById("modal-reposicion-overlay");

    const idProd = selProd ? parseInt(selProd.value) : 0;
    const cantidad = inputCant ? parseInt(inputCant.value) : 0;
    const responsable = inputResp ? inputResp.value.trim() : "Planificador de Demanda";

    if (idProd <= 0) {
        alert("Por favor selecciona un producto válido.");
        return;
    }
    if (cantidad <= 0 || isNaN(cantidad)) {
        alert("La cantidad debe ser un número entero mayor que cero.");
        return;
    }

    try {
        const res = await fetch("/api/predicciones/solicitar-reposicion", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id_producto: idProd,
                cantidad: cantidad,
                responsable: responsable,
                nota: "Solicitud registrada desde Planificación de demanda"
            })
        });

        const j = await res.json();
        if (modal) modal.style.display = "none";

        if (j.exito) {
            reproducirSonido("exito");
            alert(j.mensaje || `Solicitud guardada: +${cantidad} pares en 'Pendiente de recibir'.`);
            cargarPrediccionesOperativas(true);
        } else {
            alert(`Error: ${j.error || "No se pudo registrar la solicitud."}`);
        }
    } catch (e) {
        console.error("Error al registrar solicitud de reposición:", e);
        alert("Error de comunicación al guardar la solicitud.");
    }
}

async function cargarPrediccionesExcel() {
    try {
        const res = await fetch("/api/predicciones/excel");
        const json = await res.json();
        if (!json.exito) return;

        const cats = json.categorias || (json.datos && json.datos.categorias) || [];
        const ctxExcel = document.getElementById("chart-plan-excel");
        if (ctxExcel && cats.length > 0) {
            if (AppState.charts.planExcel) AppState.charts.planExcel.destroy();

            AppState.charts.planExcel = new Chart(ctxExcel, {
                type: "bar",
                data: {
                    labels: cats.map(c => c.categoria),
                    datasets: [
                        { label: "Real 2024 (pares)", data: cats.map(c => c.evaluacion_2024 ? c.evaluacion_2024.real_2024_pares : (c.real_2024 || 0)), backgroundColor: "#0ea5e9", borderRadius: 4 },
                        { label: "Proyección 2025 tendencia (pares)", data: cats.map(c => c.proyeccion_2025_exploratoria ? c.proyeccion_2025_exploratoria.trend_2025_pares : (c.proyeccion_2025_tendencia || 0)), backgroundColor: "#f59e0b", borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: v => v.toLocaleString() } },
                        x: { grid: { color: "rgba(255,255,255,0.06)" } }
                    },
                    plugins: { legend: { position: "top", labels: { boxWidth: 12, color: "#94a3b8" } } }
                }
            });
        }
    } catch (e) {
        console.warn("Error cargando predicciones de excel:", e);
    }
}

// ==========================================================================
// 6. VENTAS Y CANALES
// ==========================================================================
async function cargarMetricasCanales() {
    try {
        const res = await fetch("/api/canales/metricas");
        const json = await res.json();
        if (!json.exito) return;

        const kpis = json.datos.kpis || {};
        const canales = json.datos.canales || [];

        const elPares = document.getElementById("kpi-canales-pares-tot");
        const elIngBob = document.getElementById("kpi-canales-ingresos-bs");
        const elIngUsd = document.getElementById("kpi-canales-ingresos-usd");
        const elLider = document.getElementById("kpi-canales-lider-nombre");
        const elShare = document.getElementById("kpi-canales-lider-share");

        if (elPares) elPares.textContent = (kpis.total_pares_vendidos || 6959).toLocaleString();
        if (elIngBob) elIngBob.textContent = (kpis.total_ingresos_brutos_bob || 2338090.07).toLocaleString("es-BO", { minimumFractionDigits: 2 });
        if (elIngUsd) elIngUsd.textContent = `$us. ${(kpis.total_ingresos_brutos_usd || 335932.48).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
        if (elLider) elLider.textContent = kpis.canal_lider_ventas || "Tiendas Propias";
        if (elShare) elShare.textContent = `${kpis.canal_lider_participacion_pct || 58}% de las ventas`;

        renderizarGraficosCanales(canales);
    } catch (e) {
        console.warn("Error cargando métricas de canales:", e);
    }

    const btnRegen = document.getElementById("btn-regenerar-sinteticos");
    if (btnRegen) {
        btnRegen.addEventListener("click", regenerarHistorialSintetico);
    }
}

function renderizarGraficosCanales(canales) {
    const ctxPart = document.getElementById("chart-canales-participacion");
    if (ctxPart && canales.length > 0) {
        if (AppState.charts.canalesPart) AppState.charts.canalesPart.destroy();

        AppState.charts.canalesPart = new Chart(ctxPart, {
            type: "pie",
            data: {
                labels: canales.map(c => c.canal),
                datasets: [{
                    data: canales.map(c => c.pares_vendidos),
                    backgroundColor: ["#0ea5e9", "#f59e0b", "#10b981"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: "right", labels: { boxWidth: 12, color: "#94a3b8" } } }
            }
        });
    }

    const ctxFact = document.getElementById("chart-canales-facturacion");
    if (ctxFact && canales.length > 0) {
        if (AppState.charts.canalesFact) AppState.charts.canalesFact.destroy();

        AppState.charts.canalesFact = new Chart(ctxFact, {
            type: "bar",
            data: {
                labels: canales.map(c => c.canal),
                datasets: [{
                    label: "Ingresos Efectivos (Bs.)",
                    data: canales.map(c => c.ingresos_brutos_bob),
                    backgroundColor: "#10b981",
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: v => `Bs. ${v.toLocaleString()}` } },
                    x: { grid: { color: "rgba(255,255,255,0.06)" } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

async function regenerarHistorialSintetico() {
    if (!confirm("¿Deseas regenerar la simulación de ventas transaccionales de 12 meses?")) return;

    try {
        const res = await fetch("/api/sinteticos/regenerar", { method: "POST" });
        const json = await res.json();
        if (json.exito) {
            alert(`Historial sintético generado: ${json.pares_vendidos} pares vendidos.`);
            cargarDatosGenerales(false);
            cargarMetricasCanales();
            cargarPrediccionesOperativas();
        } else {
            alert(`Error: ${json.error || 'No se pudo regenerar'}`);
        }
    } catch (e) {
        console.error("Error regenerando sintéticos:", e);
    }
}

// ==========================================================================
// AUDIO SINTETIZADOR WEB AUDIO API
// ==========================================================================
function reproducirSonido(tipo = "exito") {
    if (!AppState.sonidoHabilitado) return;
    try {
        if (!AppState.audioCtx) {
            AppState.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        const ctx = AppState.audioCtx;
        if (ctx.state === "suspended") ctx.resume();

        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);

        if (tipo === "exito") {
            osc.frequency.setValueAtTime(587.33, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(880.00, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.12, ctx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, ctx.currentTime + 0.25);
            osc.start();
            osc.stop(ctx.currentTime + 0.25);
        }
    } catch (e) {
        // Fallback silencioso
    }
}
