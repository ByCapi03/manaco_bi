/**
 * app.js
 * Lógica Frontend y Control de Visión Artificial para Manaco BI Suite.
 * Gestiona cámara WebRTC, inferencia en tiempo real, gráficos interactivos Chart.js,
 * síntesis de audio con Web Audio API y sincronización con PostgreSQL.
 */

// Estado global de la aplicación
const AppState = {
    sonidoHabilitado: true,
    camaraActiva: false,
    intervaloEscaneo: null,
    ultimaClaseDetectada: "sin_calzado",
    conteoEstabilidad: 0,
    umbralEstabilidad: 3, // ~1.2 segundos continuos
    bloqueadoPorRegistro: false,
    prediccionActual: null,
    audioCtx: null,
    charts: {},
    monedaActual: "USD",
    tasaCambio: 6.96,
    ultimoResultadoEscenario: null,
    ultimoPrecioPropuesto: null
};

// ==========================================================================
// INICIALIZACIÓN AL CARGAR EL DOM
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    iniciarReloj();
    configurarTabs();
    configurarEventosUI();
    cargarDatosDashboard();
    cargarMovimientos();
    inicializarModuloMakeOrBuy();

    // Actualización periódica silenciosa cada 6 segundos si no está escaneando
    setInterval(() => {
        if (!AppState.camaraActiva) {
            cargarDatosDashboard(false);
        }
    }, 6000);
});

// Reloj en tiempo real
function iniciarReloj() {
    const relojEl = document.getElementById("live-clock");
    const actualizar = () => {
        const ahora = new Date();
        if (relojEl) {
            relojEl.textContent = ahora.toLocaleTimeString("es-BO", { hour12: false });
        }
    };
    actualizar();
    setInterval(actualizar, 1000);
}

// ==========================================================================
// AUDIO SINTETIZADO (WEB AUDIO API)
// ==========================================================================
function reproducirSonido(tipo = "exito") {
    if (!AppState.sonidoHabilitado) return;
    try {
        if (!AppState.audioCtx) {
            AppState.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (AppState.audioCtx.state === "suspended") {
            AppState.audioCtx.resume();
        }

        const ctx = AppState.audioCtx;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.connect(gain);
        gain.connect(ctx.destination);

        const ahora = ctx.currentTime;

        if (tipo === "exito") {
            // Acorde armónico ascendente moderno Manaco (Re Mayor / F#)
            osc.type = "sine";
            osc.frequency.setValueAtTime(587.33, ahora); // D5
            osc.frequency.exponentialRampToValueAtTime(880.00, ahora + 0.12); // A5
            gain.gain.setValueAtTime(0.20, ahora);
            gain.gain.exponentialRampToValueAtTime(0.001, ahora + 0.28);
            osc.start(ahora);
            osc.stop(ahora + 0.28);
        } else if (tipo === "alerta") {
            // Tono grave para deshacer/alerta
            osc.type = "triangle";
            osc.frequency.setValueAtTime(320.00, ahora);
            osc.frequency.exponentialRampToValueAtTime(220.00, ahora + 0.18);
            gain.gain.setValueAtTime(0.25, ahora);
            gain.gain.exponentialRampToValueAtTime(0.001, ahora + 0.22);
            osc.start(ahora);
            osc.stop(ahora + 0.22);
        }
    } catch (e) {
        console.warn("No se pudo emitir sonido:", e);
    }
}

// ==========================================================================
// NAVEGACIÓN POR PESTAÑAS
// ==========================================================================
function configurarTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");

            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            document.querySelectorAll(".tab-pane").forEach(pane => {
                pane.classList.remove("active");
            });

            const targetPane = document.getElementById(targetId);
            if (targetPane) {
                targetPane.classList.add("active");
            }

            // Si entra al dashboard o a fabricar o importar, refrescar gráficos para ajustar dimensiones
            if (targetId === "tab-dashboard") {
                setTimeout(() => {
                    Object.values(AppState.charts).forEach(c => c && c.resize && c.resize());
                }, 100);
            } else if (targetId === "tab-make-or-buy") {
                setTimeout(() => {
                    if (AppState.charts.comercioValor && AppState.charts.comercioValor.resize) AppState.charts.comercioValor.resize();
                    if (AppState.charts.comercioPares && AppState.charts.comercioPares.resize) AppState.charts.comercioPares.resize();
                }, 100);
            }
        });
    });
}

// ==========================================================================
// CONFIGURACIÓN DE EVENTOS UI
// ==========================================================================
function configurarEventosUI() {
    // Sonido toggle
    const btnSound = document.getElementById("btn-toggle-sound");
    if (btnSound) {
        btnSound.addEventListener("click", () => {
            AppState.sonidoHabilitado = !AppState.sonidoHabilitado;
            const icon = document.getElementById("sound-icon");
            if (icon) icon.textContent = AppState.sonidoHabilitado ? "🔔" : "🔕";
            btnSound.classList.toggle("btn-danger-soft", !AppState.sonidoHabilitado);
        });
    }

    // Botón rápido simular 20
    const btnQuickSim = document.getElementById("btn-quick-simulate");
    if (btnQuickSim) {
        btnQuickSim.addEventListener("click", () => ejecutarSimulacion(20));
    }

    // Refrescar gráficos
    const btnRefreshCharts = document.getElementById("btn-refresh-charts");
    if (btnRefreshCharts) {
        btnRefreshCharts.addEventListener("click", () => cargarDatosDashboard(true));
    }

    // Controles de Cámara y Escáner
    const btnStartCam = document.getElementById("btn-start-camera");
    const btnStopCam = document.getElementById("btn-stop-camera");
    const btnManualReg = document.getElementById("btn-manual-register");
    const btnUndoScan = document.getElementById("btn-undo-scan");

    if (btnStartCam) btnStartCam.addEventListener("click", iniciarCamara);
    if (btnStopCam) btnStopCam.addEventListener("click", detenerCamara);
    if (btnManualReg) btnManualReg.addEventListener("click", registrarPrediccionManual);
    if (btnUndoScan) btnUndoScan.addEventListener("click", deshacerUltimo);

    // Modos de entrada: Cámara vs Subir Foto
    const btnModeCam = document.getElementById("btn-mode-camera");
    const btnModeUp = document.getElementById("btn-mode-upload");
    const dropzone = document.getElementById("upload-dropzone");
    const videoEl = document.getElementById("webcam-video");
    const fileInput = document.getElementById("file-input-shoe");
    const btnTriggerUp = document.getElementById("btn-trigger-upload");
    const imgPreview = document.getElementById("uploaded-preview");

    if (btnModeCam && btnModeUp) {
        btnModeCam.addEventListener("click", () => {
            btnModeCam.classList.add("active");
            btnModeUp.classList.remove("active");
            if (dropzone) dropzone.style.display = "none";
            if (videoEl) videoEl.style.display = "block";
            iniciarCamara();
        });

        btnModeUp.addEventListener("click", () => {
            btnModeUp.classList.add("active");
            btnModeCam.classList.remove("active");
            detenerCamara();
            if (videoEl) videoEl.style.display = "none";
            if (dropzone) dropzone.style.display = "flex";
        });
    }

    if (btnTriggerUp && fileInput) {
        btnTriggerUp.addEventListener("click", () => fileInput.click());
    }

    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) procesarArchivoImagen(file);
        });
    }

    if (dropzone) {
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--cyan-accent)";
        });
        dropzone.addEventListener("dragleave", () => {
            dropzone.style.borderColor = "rgba(255, 255, 255, 0.18)";
        });
        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "rgba(255, 255, 255, 0.18)";
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                procesarArchivoImagen(e.dataTransfer.files[0]);
            }
        });
    }

    // Simulador: Slider y Botones de preajuste
    const sliderSim = document.getElementById("sim-cantidad");
    const valSim = document.getElementById("sim-cantidad-val");
    if (sliderSim && valSim) {
        sliderSim.addEventListener("input", (e) => {
            valSim.textContent = e.target.value;
        });
    }

    document.querySelectorAll(".btn-sim-preset").forEach(btn => {
        btn.addEventListener("click", () => {
            const cant = parseInt(btn.getAttribute("data-cant") || "20");
            if (sliderSim && valSim) {
                sliderSim.value = cant;
                valSim.textContent = cant;
            }
            ejecutarSimulacion(cant);
        });
    });

    const btnRunSim = document.getElementById("btn-run-simulation");
    if (btnRunSim) {
        btnRunSim.addEventListener("click", () => {
            const cant = parseInt(sliderSim ? sliderSim.value : "25");
            ejecutarSimulacion(cant);
        });
    }

    const btnResetInv = document.getElementById("btn-reset-inventory");
    if (btnResetInv) {
        btnResetInv.addEventListener("click", reiniciarInventario);
    }

    // Búsqueda en tabla de movimientos
    const searchInput = document.getElementById("input-search-movs");
    if (searchInput) {
        searchInput.addEventListener("input", filtrarTablaMovimientos);
    }

    // Exportar CSV
    const btnExport = document.getElementById("btn-export-csv");
    if (btnExport) {
        btnExport.addEventListener("click", () => {
            window.location.href = "/api/exportar-csv";
        });
    }

    const btnRefTable = document.getElementById("btn-refresh-table");
    if (btnRefTable) {
        btnRefTable.addEventListener("click", cargarMovimientos);
    }
}

// ==========================================================================
// CARGAR DATOS Y ACTUALIZAR KPIS & GRÁFICOS
// ==========================================================================
async function cargarDatosDashboard(animar = true) {
    try {
        const [resEstado, resGraficos] = await Promise.all([
            fetch("/api/estado").then(r => r.json()),
            fetch("/api/graficos").then(r => r.json())
        ]);

        if (resEstado.exito) {
            actualizarKPIs(resEstado.kpis, resEstado.motor_db);
            actualizarResumenCategorias(resEstado.inventario);
            actualizarMiniInventario(resEstado.inventario);
        }

        if (resGraficos.exito && resGraficos.datos) {
            renderizarGraficos(resGraficos.datos, animar);
        }
    } catch (err) {
        console.error("Error al cargar datos del dashboard:", err);
    }
}

function actualizarKPIs(kpis, motorDb) {
    if (!kpis) return;

    const elPares = document.getElementById("kpi-val-pares");
    const elBs = document.getElementById("kpi-val-dinero-bs");
    const elUsd = document.getElementById("kpi-val-dinero-usd");
    const elLider = document.getElementById("kpi-val-lider");
    const elLiderPares = document.getElementById("kpi-cap-lider-pares");
    const elIngresosIa = document.getElementById("kpi-val-ingresos-ia");
    const elConfianza = document.getElementById("kpi-val-confianza-prom");
    const elBarOcupacion = document.getElementById("kpi-bar-ocupacion");
    const elCapOcupacion = document.getElementById("kpi-cap-ocupacion");
    const elDbBadge = document.getElementById("db-status-text");

    if (elPares) elPares.textContent = (kpis.total_pares || 0).toLocaleString();
    if (elBs) elBs.textContent = kpis.total_valor_bs || "0.00";
    if (elUsd) elUsd.textContent = `$us. ${kpis.total_valor_usd || "0.00"}`;
    if (elLider) elLider.textContent = kpis.categoria_lider || "N/D";
    if (elLiderPares) elLiderPares.textContent = `${kpis.stock_lider || 0} pares disponibles`;
    if (elIngresosIa) elIngresosIa.textContent = kpis.total_ingresos_ia || 0;
    if (elConfianza) elConfianza.textContent = kpis.confianza_promedio_ia ? String(kpis.confianza_promedio_ia) : "Sin escaneos";

    const ocupPct = Math.min(100, kpis.capacidad_ocupada_pct || 0);
    if (elBarOcupacion) elBarOcupacion.style.width = `${ocupPct}%`;
    if (elCapOcupacion) elCapOcupacion.textContent = `Capacidad ocupada: ${ocupPct}%`;

    if (elDbBadge && motorDb) {
        elDbBadge.textContent = `${motorDb} ACTIVO`;
    }
}

function actualizarResumenCategorias(inventario) {
    const contenedor = document.getElementById("categories-summary-container");
    if (!contenedor || !inventario) return;

    const iconos = {
        1: { icon: "👟", bg: "rgba(6, 182, 212, 0.15)", border: "#06b6d4" },
        2: { icon: "👞", bg: "rgba(245, 158, 11, 0.15)", border: "#f59e0b" },
        3: { icon: "👞", bg: "rgba(225, 29, 72, 0.15)", border: "#e11d48" }
    };

    contenedor.innerHTML = inventario.map(item => {
        const estilo = iconos[item.id_producto] || { icon: "👟", bg: "rgba(255,255,255,0.1)", border: "#94a3b8" };
        const alertaHtml = item.alerta_stock 
            ? `<span class="badge-tag" style="background: rgba(225,29,72,0.2); color: #fda4af;">⚠️ Stock Bajo</span>`
            : `<span class="badge-tag tag-emerald">✓ Óptimo</span>`;

        return `
            <div class="cat-bar-card glass-panel" style="border-left-color: ${estilo.border};">
                <div class="cat-icon-wrap" style="background: ${estilo.bg};">
                    ${estilo.icon}
                </div>
                <div class="cat-details">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4 class="cat-title">${item.categoria_corta}</h4>
                        ${alertaHtml}
                    </div>
                    <span class="cat-sa6">SA6: ${item.codigo_sa6}</span>
                    <div class="cat-numbers">
                        <span>Stock: <strong>${item.stock_actual} pares</strong></span>
                        <span>Mín: ${item.stock_minimo}</span>
                        <span>Bs. ${item.precio_unitario_bs.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join("");
}

function actualizarMiniInventario(inventario) {
    const cont = document.getElementById("mini-inventory-container");
    if (!cont || !inventario) return;

    cont.innerHTML = inventario.map(item => {
        const color = item.id_producto === 1 ? "#06b6d4" : (item.id_producto === 2 ? "#f59e0b" : "#e11d48");
        return `
            <div class="mini-inv-item">
                <span class="mini-inv-name" style="border-left: 3px solid ${color}; padding-left: 8px;">
                    ${item.categoria_corta}
                </span>
                <span class="mini-inv-stock" style="color: ${color};">
                    ${item.stock_actual} pares
                </span>
            </div>
        `;
    }).join("");
}

// ==========================================================================
// RENDERIZADO DE GRÁFICOS INTERACTIVOS (CHART.JS)
// ==========================================================================
function renderizarGraficos(datos, animar) {
    // Configuración compartida de tema oscuro para Chart.js
    Chart.defaults.color = "#94a3b8";
    Chart.defaults.font.family = "'Outfit', sans-serif";

    // 1. Gráfico: Stock Actual vs Mínimo
    const ctxStock = document.getElementById("chart-stock-niveles");
    if (ctxStock) {
        if (AppState.charts.stock) AppState.charts.stock.destroy();

        AppState.charts.stock = new Chart(ctxStock, {
            type: "bar",
            data: {
                labels: datos.categorias || ["Deportivo", "Casual", "Formal"],
                datasets: [
                    {
                        label: "Stock Actual (pares)",
                        data: datos.stock_actual || [0, 0, 0],
                        backgroundColor: ["rgba(6, 182, 212, 0.8)", "rgba(245, 158, 11, 0.8)", "rgba(225, 29, 72, 0.8)"],
                        borderColor: ["#06b6d4", "#f59e0b", "#e11d48"],
                        borderWidth: 2,
                        borderRadius: 8
                    },
                    {
                        label: "Stock Mínimo de Seguridad",
                        data: datos.stock_minimo || [25, 25, 20],
                        type: "line",
                        borderColor: "rgba(255, 255, 255, 0.45)",
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointBackgroundColor: "#ffffff",
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animar ? { duration: 600 } : false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12 } },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        borderColor: "rgba(255,255,255,0.15)",
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 2. Gráfico: Evolución Temporal de Movimientos
    const ctxTemp = document.getElementById("chart-tendencia-temporal");
    if (ctxTemp) {
        if (AppState.charts.temporal) AppState.charts.temporal.destroy();

        AppState.charts.temporal = new Chart(ctxTemp, {
            type: "line",
            data: {
                labels: datos.serie_fechas && datos.serie_fechas.length ? datos.serie_fechas : ["Reciente"],
                datasets: [
                    {
                        label: "Ingresos por Visión IA",
                        data: datos.serie_ingresos && datos.serie_ingresos.length ? datos.serie_ingresos : [1],
                        borderColor: "#06b6d4",
                        backgroundColor: "rgba(6, 182, 212, 0.15)",
                        fill: true,
                        tension: 0.35,
                        borderWidth: 3,
                        pointRadius: 4
                    },
                    {
                        label: "Salidas por Ventas",
                        data: datos.serie_ventas && datos.serie_ventas.length ? datos.serie_ventas : [0],
                        borderColor: "#f59e0b",
                        backgroundColor: "rgba(245, 158, 11, 0.10)",
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animar ? { duration: 600 } : false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12 } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    x: {
                        grid: { color: "rgba(255, 255, 255, 0.03)" }
                    }
                }
            }
        });
    }

    // 3. Gráfico: Distribución de Inventario en Dona
    const ctxDona = document.getElementById("chart-distribucion-dona");
    if (ctxDona) {
        if (AppState.charts.dona) AppState.charts.dona.destroy();

        AppState.charts.dona = new Chart(ctxDona, {
            type: "doughnut",
            data: {
                labels: datos.categorias || ["Deportivo", "Casual", "Formal"],
                datasets: [
                    {
                        data: datos.stock_actual || [1, 1, 1],
                        backgroundColor: ["#06b6d4", "#f59e0b", "#e11d48"],
                        borderColor: "#0e1526",
                        borderWidth: 3,
                        hoverOffset: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "68%",
                animation: animar ? { duration: 600 } : false,
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, padding: 16 } }
                }
            }
        });
    }

    // 4. Gráfico: Contexto Data Warehouse (Comercio Exterior de Bolivia)
    const ctxDw = document.getElementById("chart-dw-comercio");
    if (ctxDw && datos.dw_comercio && datos.dw_comercio.disponible) {
        if (AppState.charts.dw) AppState.charts.dw.destroy();

        AppState.charts.dw = new Chart(ctxDw, {
            type: "bar",
            data: {
                labels: datos.dw_comercio.anios,
                datasets: [
                    {
                        label: "Importaciones (pares)",
                        data: datos.dw_comercio.importacion_pares,
                        backgroundColor: "rgba(225, 29, 72, 0.75)",
                        borderRadius: 6
                    },
                    {
                        label: "Exportaciones (pares)",
                        data: datos.dw_comercio.exportacion_pares,
                        backgroundColor: "rgba(16, 185, 129, 0.75)",
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: animar ? { duration: 600 } : false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12 } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

// ==========================================================================
// CÁMARA WEBCAM & RECONOCIMIENTO EN TIEMPO REAL
// ==========================================================================
async function iniciarCamara() {
    const videoEl = document.getElementById("webcam-video");
    const btnStart = document.getElementById("btn-start-camera");
    const btnStop = document.getElementById("btn-stop-camera");
    const statusText = document.getElementById("scanner-status-text");
    const statusDot = document.getElementById("scanner-dot");

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "environment"
            },
            audio: false
        });

        videoEl.srcObject = stream;
        await videoEl.play();

        AppState.camaraActiva = true;
        if (btnStart) btnStart.style.display = "none";
        if (btnStop) btnStop.style.display = "inline-flex";

        if (statusText) statusText.textContent = "ESCANEANDO CALZADO EN VIVO...";
        if (statusDot) statusDot.classList.add("green");

        // Bucle de inferencia periódica cada 380 ms
        AppState.intervaloEscaneo = setInterval(capturarYClasificarFrame, 380);
    } catch (err) {
        console.error("Error al acceder a la cámara:", err);
        if (statusText) statusText.textContent = "NO SE PUDO ACCEDER A LA CÁMARA (Usa el modo 'Subir Fotografía')";
        alert("No se pudo iniciar la cámara web. Puedes usar la pestaña 'Subir Fotografía' para probar con cualquier imagen.");
    }
}

function detenerCamara() {
    const videoEl = document.getElementById("webcam-video");
    const btnStart = document.getElementById("btn-start-camera");
    const btnStop = document.getElementById("btn-stop-camera");
    const statusText = document.getElementById("scanner-status-text");
    const statusDot = document.getElementById("scanner-dot");

    if (AppState.intervaloEscaneo) {
        clearInterval(AppState.intervaloEscaneo);
        AppState.intervaloEscaneo = null;
    }

    if (videoEl && videoEl.srcObject) {
        const tracks = videoEl.srcObject.getTracks();
        tracks.forEach(t => t.stop());
        videoEl.srcObject = null;
    }

    AppState.camaraActiva = false;
    if (btnStart) btnStart.style.display = "inline-flex";
    if (btnStop) btnStop.style.display = "none";

    if (statusText) statusText.textContent = "CÁMARA DETENIDA";
    if (statusDot) statusDot.classList.remove("green");
    ocultarTagHUD();
}

async function capturarYClasificarFrame() {
    const videoEl = document.getElementById("webcam-video");
    const canvasEl = document.getElementById("webcam-canvas");
    if (!videoEl || !canvasEl || videoEl.videoWidth === 0) return;

    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;
    const ctx = canvasEl.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

    // Obtener imagen en JPEG Base64
    const base64Data = canvasEl.toDataURL("image/jpeg", 0.82);

    try {
        const res = await fetch("/api/clasificar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ imagen: base64Data })
        });
        const datos = await res.json();
        if (datos.exito) {
            procesarResultadoClasificacion(datos);
        }
    } catch (e) {
        console.warn("Fallo de clasificación en frame:", e);
    }
}

function procesarResultadoClasificacion(pred) {
    AppState.prediccionActual = pred;

    // Actualizar barras de probabilidades
    const probs = pred.probabilidades || {};
    actualizarBarraProb("deportivo", probs["calzado_deportivo"] || 0);
    actualizarBarraProb("casual", probs["calzado_casual"] || 0);
    actualizarBarraProb("formal", probs["calzado_formal"] || 0);
    actualizarBarraProb("sin_calzado", probs["sin_calzado"] || 0);

    const btnManualReg = document.getElementById("btn-manual-register");
    const chkAuto = document.getElementById("chk-auto-register");
    const autoActivo = chkAuto ? chkAuto.checked : true;

    // Si es calzado y supera el 75% de confianza
    if (pred.es_calzado && pred.confianza >= 0.75) {
        if (btnManualReg) btnManualReg.disabled = false;
        mostrarTagHUD(pred);

        // Lógica de persistencia temporal
        if (pred.clase === AppState.ultimaClaseDetectada) {
            AppState.conteoEstabilidad++;
        } else {
            AppState.ultimaClaseDetectada = pred.clase;
            AppState.conteoEstabilidad = 1;
            AppState.bloqueadoPorRegistro = false;
        }

        // Auto-registro al cumplir N frames de estabilidad
        if (autoActivo && !AppState.bloqueadoPorRegistro && AppState.conteoEstabilidad >= AppState.umbralEstabilidad) {
            AppState.bloqueadoPorRegistro = true;
            ejecutarRegistroCalzado(pred.clase, pred.confianza, "camara_web_auto");
        }
    } else {
        if (btnManualReg) btnManualReg.disabled = true;
        ocultarTagHUD();

        // Si ve fondo/sin calzado, liberar candado de registro
        if (!pred.es_calzado) {
            AppState.bloqueadoPorRegistro = false;
            AppState.conteoEstabilidad = 0;
            AppState.ultimaClaseDetectada = "sin_calzado";
        }
    }
}

function actualizarBarraProb(clave, pct) {
    const bar = document.getElementById(`bar-prob-${clave}`);
    const val = document.getElementById(`val-prob-${clave}`);
    if (bar) bar.style.width = `${pct}%`;
    if (val) val.textContent = `${pct.toFixed(1)}%`;
}

function mostrarTagHUD(pred) {
    const tag = document.getElementById("hud-tag");
    const tagText = document.getElementById("hud-tag-text");
    const tagPct = document.getElementById("hud-tag-pct");
    const reticle = document.getElementById("hud-reticle");

    if (tag && tagText && tagPct) {
        tagText.textContent = pred.nombre.split("(")[0].trim().toUpperCase();
        tagPct.textContent = `${pred.porcentaje}%`;
        tag.style.display = "flex";
        tag.style.borderColor = pred.color;
    }
    if (reticle) {
        reticle.style.borderColor = pred.color;
    }
}

function ocultarTagHUD() {
    const tag = document.getElementById("hud-tag");
    const reticle = document.getElementById("hud-reticle");
    if (tag) tag.style.display = "none";
    if (reticle) reticle.style.borderColor = "rgba(255, 255, 255, 0.12)";
}

// Subida de imagen fija
function procesarArchivoImagen(file) {
    const reader = new FileReader();
    reader.onload = async (e) => {
        const base64Img = e.target.result;
        const imgEl = document.getElementById("uploaded-preview");
        if (imgEl) {
            imgEl.src = base64Img;
            imgEl.style.display = "block";
        }

        try {
            const res = await fetch("/api/clasificar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ imagen: base64Img })
            });
            const datos = await res.json();
            if (datos.exito) {
                procesarResultadoClasificacion(datos);
                const statusText = document.getElementById("scanner-status-text");
                if (statusText) statusText.textContent = `FOTO CLASIFICADA: ${datos.nombre} (${datos.porcentaje}%)`;
            }
        } catch (err) {
            console.error("Error al procesar archivo:", err);
        }
    };
    reader.readAsDataURL(file);
}

// ==========================================================================
// REGISTRO DE CALZADO EN LA BASE DE DATOS
// ==========================================================================
async function ejecutarRegistroCalzado(clase, confianza, origen = "escaner_web") {
    try {
        const res = await fetch("/api/registrar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ clase, confianza, origen })
        });
        const datos = await res.json();

        if (datos.exito) {
            reproducirSonido("exito");
            actualizarNotificacionUltimoRegistro(datos);
            cargarDatosDashboard(false);
            cargarMovimientos();
        }
    } catch (e) {
        console.error("Error al registrar calzado:", e);
    }
}

function registrarPrediccionManual() {
    if (AppState.prediccionActual && AppState.prediccionActual.es_calzado) {
        ejecutarRegistroCalzado(
            AppState.prediccionActual.clase,
            AppState.prediccionActual.confianza,
            "registro_manual_boton"
        );
    }
}

function actualizarNotificacionUltimoRegistro(item) {
    const nameEl = document.getElementById("last-det-name");
    const timeEl = document.getElementById("last-det-time");
    if (nameEl) nameEl.textContent = `+1 ${item.categoria} (Stock: ${item.nuevo_stock})`;
    if (timeEl) timeEl.textContent = `Registrado a las ${item.timestamp} • Confianza: ${(item.confianza * 100).toFixed(1)}%`;
}

async function deshacerUltimo() {
    try {
        const res = await fetch("/api/deshacer", { method: "POST" });
        const datos = await res.json();
        reproducirSonido("alerta");
        alert(datos.mensaje || "Operación completada");
        cargarDatosDashboard(false);
        cargarMovimientos();
    } catch (e) {
        console.error("Error al deshacer:", e);
    }
}

// ==========================================================================
// MOVIMIENTOS & AUDITORÍA (TABLA)
// ==========================================================================
async function cargarMovimientos() {
    const tbody = document.getElementById("table-movimientos-body");
    if (!tbody) return;

    try {
        const res = await fetch("/api/estado");
        const datos = await res.json();

        if (datos.exito && datos.movimientos) {
            if (datos.movimientos.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="padding: 24px;">No hay movimientos registrados aún. ¡Usa el escáner o el simulador!</td></tr>`;
                return;
            }

            tbody.innerHTML = datos.movimientos.map(m => {
                let badgeClass = "ingreso";
                if (m.accion.includes("VENTA")) badgeClass = "venta";
                if (m.accion.includes("DESHACER") || m.accion.includes("AJUSTE")) badgeClass = "reversa";

                return `
                    <tr>
                        <td><strong>#${m.id_registro}</strong></td>
                        <td>${m.fecha_hora}</td>
                        <td><strong>${m.categoria}</strong></td>
                        <td><span class="badge-action ${badgeClass}">${m.accion}</span></td>
                        <td><strong>${m.cantidad}</strong></td>
                        <td>${(m.confianza * 100).toFixed(1)}%</td>
                        <td>${m.origen}</td>
                        <td>${m.responsable}</td>
                    </tr>
                `;
            }).join("");
        }
    } catch (e) {
        console.error("Error al cargar movimientos:", e);
    }
}

function filtrarTablaMovimientos(e) {
    const query = (e.target.value || "").toLowerCase();
    const filas = document.querySelectorAll("#table-movimientos-body tr");
    filas.forEach(f => {
        const texto = f.textContent.toLowerCase();
        f.style.display = texto.includes(query) ? "" : "none";
    });
}

// ==========================================================================
// SIMULADOR DE DATOS
// ==========================================================================
async function ejecutarSimulacion(cantidad = 25) {
    const consoleEl = document.getElementById("sim-console-output");
    if (consoleEl) {
        consoleEl.innerHTML += `<p class="console-line">⏳ [${new Date().toLocaleTimeString()}] Generando ${cantidad} transacciones sintéticas de calzado...</p>`;
        consoleEl.scrollTop = consoleEl.scrollHeight;
    }

    try {
        const res = await fetch("/api/simular", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ cantidad })
        });
        const datos = await res.json();

        if (datos.exito) {
            reproducirSonido("exito");
            if (consoleEl) {
                consoleEl.innerHTML += `<p class="console-line" style="color: #6ee7b7;">✓ [${new Date().toLocaleTimeString()}] ${datos.mensaje}</p>`;
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }
            cargarDatosDashboard(true);
            cargarMovimientos();
        } else {
            if (consoleEl) {
                consoleEl.innerHTML += `<p class="console-line" style="color: #fda4af;">✕ Error: ${datos.error}</p>`;
            }
        }
    } catch (e) {
        console.error("Error al simular:", e);
    }
}

async function reiniciarInventario() {
    if (!confirm("¿Estás seguro de que deseas reiniciar el inventario a 30 pares por categoría?")) {
        return;
    }

    try {
        const res = await fetch("/api/reiniciar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stock_base: 30 })
        });
        const datos = await res.json();
        reproducirSonido("alerta");
        alert(datos.mensaje || "Inventario reiniciado");
        cargarDatosDashboard(true);
        cargarMovimientos();
    } catch (e) {
        console.error("Error al reiniciar:", e);
    }
}

// ==========================================================================
// MÓDULO: FABRICAR O IMPORTAR & ANÁLISIS COMERCIAL (EXCEL DIRECTO)
// ==========================================================================

function inicializarModuloMakeOrBuy() {
    configurarEventosMakeOrBuy();
    cargarOpcionesComercio();
    cargarMetricasComercio();
    ejecutarCalculoEscenario();
}

function configurarEventosMakeOrBuy() {
    // 1. Selector de Moneda y Tasa de Cambio
    const btnUsd = document.getElementById("btn-currency-usd");
    const btnBob = document.getElementById("btn-currency-bob");
    const inputTc = document.getElementById("input-tasa-cambio");

    if (btnUsd && btnBob) {
        btnUsd.addEventListener("click", () => cambiarMoneda("USD"));
        btnBob.addEventListener("click", () => cambiarMoneda("BOB"));
    }

    if (inputTc) {
        inputTc.addEventListener("change", (e) => {
            const val = parseFloat(e.target.value);
            if (val > 0) {
                AppState.tasaCambio = val;
                cargarMetricasComercio();
                ejecutarCalculoEscenario();
            }
        });
    }

    // 2. Filtros de Comercio Exterior
    const btnFiltros = document.getElementById("btn-aplicar-filtros-comercio");
    if (btnFiltros) {
        btnFiltros.addEventListener("click", () => cargarMetricasComercio());
    }

    ["sel-comercio-flujo", "sel-comercio-anio", "sel-comercio-categoria", "sel-comercio-socio"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("change", () => cargarMetricasComercio());
        }
    });

    // 3. Fichas de Referencia 2024
    document.querySelectorAll(".ref-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".ref-chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");

            const sa6 = chip.getAttribute("data-sa6");
            const val = parseFloat(chip.getAttribute("data-val"));

            const catSel = document.getElementById("calc-categoria-sel");
            if (catSel) {
                catSel.value = sa6;
                actualizarCardInventarioActivo(sa6);
            }

            const pCompra = document.getElementById("calc-p-compra");
            if (pCompra) {
                const precio = (AppState.monedaActual === "BOB") ? (val * AppState.tasaCambio) : val;
                pCompra.value = precio.toFixed(2);
            }

            ejecutarCalculoEscenario();
        });
    });

    // 4. Botones de transferencia de referencia
    const btnUseExcelQuote = document.getElementById("btn-use-excel-quote");
    if (btnUseExcelQuote) {
        btnUseExcelQuote.addEventListener("click", () => {
            const catSel = document.getElementById("calc-categoria-sel");
            const sa6 = catSel ? catSel.value : "640399";
            const chip = document.querySelector(`.ref-chip[data-sa6="${sa6}"]`);
            if (chip) {
                const val = parseFloat(chip.getAttribute("data-val") || "26.15");
                const pCompra = document.getElementById("calc-p-compra");
                if (pCompra) {
                    const precio = (AppState.monedaActual === "BOB") ? (val * AppState.tasaCambio) : val;
                    pCompra.value = precio.toFixed(2);
                }
                ejecutarCalculoEscenario();
            }
        });
    }

    const btnTransferCalc = document.getElementById("btn-transfer-ref-calc");
    if (btnTransferCalc) {
        btnTransferCalc.addEventListener("click", () => {
            const ratioEl = document.getElementById("kpi-ext-ratio");
            if (ratioEl) {
                const rawVal = parseFloat(ratioEl.textContent.replace(/,/g, "")) || 0;
                const pCompra = document.getElementById("calc-p-compra");
                if (pCompra && rawVal > 0) {
                    pCompra.value = rawVal.toFixed(2);
                    ejecutarCalculoEscenario();
                }
            }
        });
    }

    // 5. Cambio de categoría en la calculadora
    const calcCatSel = document.getElementById("calc-categoria-sel");
    if (calcCatSel) {
        calcCatSel.addEventListener("change", (e) => {
            actualizarCardInventarioActivo(e.target.value);
            ejecutarCalculoEscenario();
        });
    }

    // 6. Preajustes de Escenarios Equilibrados
    document.querySelectorAll(".btn-preset-scenario").forEach(btn => {
        btn.addEventListener("click", () => {
            const presetTipo = btn.getAttribute("data-preset");
            cargarEscenarioPreset(presetTipo);
        });
    });

    // 7. Botón de Ejecutar Cálculo
    const btnCalc = document.getElementById("btn-calcular-escenario");
    if (btnCalc) {
        btnCalc.addEventListener("click", () => ejecutarCalculoEscenario());
    }

    // 8. Botón Aplicar Precio al Inventario
    const btnAplicarPrecio = document.getElementById("btn-aplicar-precio-propuesto");
    if (btnAplicarPrecio) {
        btnAplicarPrecio.addEventListener("click", aplicarPrecioAlInventario);
    }
}

function cambiarMoneda(nuevaMoneda) {
    if (AppState.monedaActual === nuevaMoneda) return;
    AppState.monedaActual = nuevaMoneda;
    const tc = AppState.tasaCambio;

    const btnUsd = document.getElementById("btn-currency-usd");
    const btnBob = document.getElementById("btn-currency-bob");
    if (btnUsd && btnBob) {
        btnUsd.classList.toggle("active", nuevaMoneda === "USD");
        btnBob.classList.toggle("active", nuevaMoneda === "BOB");
    }

    // Actualizar labels de unidad en el DOM
    const simbolo = nuevaMoneda === "USD" ? "$us" : "Bs.";
    document.querySelectorAll(".unit-curr-text").forEach(el => el.textContent = simbolo);
    document.querySelectorAll(".curr-symbol").forEach(el => el.textContent = simbolo);

    // Convertir campos numéricos de la calculadora
    const factor = (nuevaMoneda === "BOB") ? tc : (1.0 / tc);
    const campos = [
        "calc-precio-venta",
        "calc-cv-fabril",
        "calc-cf-evitables",
        "calc-cf-permanentes",
        "calc-p-compra",
        "calc-flete",
        "calc-seguro",
        "calc-arancel",
        "calc-logistica",
        "calc-otros"
    ];

    campos.forEach(id => {
        const inp = document.getElementById(id);
        if (inp && inp.value) {
            const v = parseFloat(inp.value);
            if (!isNaN(v)) {
                inp.value = (v * factor).toFixed(2);
            }
        }
    });

    // Actualizar visualización en fichas de referencia
    document.querySelectorAll(".ref-chip").forEach(chip => {
        const valUsd = parseFloat(chip.getAttribute("data-val"));
        const chipValEl = chip.querySelector(".chip-val");
        if (chipValEl) {
            if (nuevaMoneda === "BOB") {
                chipValEl.textContent = `Bs. ${(valUsd * tc).toFixed(2)}/par`;
            } else {
                chipValEl.textContent = `$${valUsd.toFixed(2)} USD/par`;
            }
        }
    });

    cargarMetricasComercio();
    ejecutarCalculoEscenario();
}

async function cargarOpcionesComercio() {
    try {
        const res = await fetch("/api/comercio/opciones");
        const datos = await res.json();
        if (datos.exito && datos.socios) {
            const selSocio = document.getElementById("sel-comercio-socio");
            if (selSocio) {
                selSocio.innerHTML = '<option value="">Todos los Socios (30 Países)</option>' +
                    datos.socios.map(s => `<option value="${s}">${s}</option>`).join("");
            }
        }
    } catch (e) {
        console.error("Error al cargar opciones de comercio:", e);
    }
}

async function cargarMetricasComercio() {
    const flujo = document.getElementById("sel-comercio-flujo")?.value || "Importación";
    const anio = document.getElementById("sel-comercio-anio")?.value || "2024";
    const sa6 = document.getElementById("sel-comercio-categoria")?.value || "";
    const socio = document.getElementById("sel-comercio-socio")?.value || "";

    const params = new URLSearchParams({
        flujo: flujo,
        anio: anio,
        codigo_sa6: sa6,
        socio: socio
    });

    try {
        const res = await fetch(`/api/comercio/metricas?${params.toString()}`);
        const data = await res.json();

        if (data.exito && data.resumen) {
            const tc = AppState.tasaCambio;
            const esBob = (AppState.monedaActual === "BOB");
            const factor = esBob ? tc : 1.0;

            const valTotal = data.resumen.suma_valor_usd * factor;
            const paresTotal = data.resumen.suma_cantidad_pares;
            const ratioPonderado = data.resumen.referencia_usd_por_par * factor;

            const elValor = document.getElementById("kpi-ext-valor");
            const elPartValor = document.getElementById("kpi-ext-part-valor");
            const elPares = document.getElementById("kpi-ext-pares");
            const elPartPares = document.getElementById("kpi-ext-part-pares");
            const elRatio = document.getElementById("kpi-ext-ratio");

            if (elValor) elValor.textContent = valTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            if (elPartValor) elPartValor.textContent = `${data.resumen.participacion_valor_pct.toFixed(1)}% del flujo`;
            if (elPares) elPares.textContent = paresTotal.toLocaleString();
            if (elPartPares) elPartPares.textContent = `${data.resumen.participacion_pares_pct.toFixed(1)}% del volumen`;
            if (elRatio) elRatio.textContent = ratioPonderado.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

            renderizarGraficosComercio(data.serie_temporal, data.ranking_socios);
        }
    } catch (e) {
        console.error("Error al cargar métricas de comercio:", e);
    }
}

function renderizarGraficosComercio(serieTemporal, rankingSocios) {
    if (!serieTemporal) return;

    const esBob = (AppState.monedaActual === "BOB");
    const factor = esBob ? AppState.tasaCambio : 1.0;
    const simbolo = esBob ? "Bs." : "$ USD";

    // 1. Gráfico: Valor Comercial
    const ctxValor = document.getElementById("chart-comercio-valor");
    if (ctxValor) {
        if (AppState.charts.comercioValor) AppState.charts.comercioValor.destroy();

        const valoresConvertidos = (serieTemporal.valores_usd || []).map(v => Math.round(v * factor));

        AppState.charts.comercioValor = new Chart(ctxValor, {
            type: "bar",
            data: {
                labels: serieTemporal.anios || ["2020", "2021", "2022", "2023", "2024"],
                datasets: [
                    {
                        label: `Valor Comercial Declarado (${simbolo})`,
                        data: valoresConvertidos,
                        backgroundColor: "rgba(6, 182, 212, 0.75)",
                        borderColor: "#06b6d4",
                        borderWidth: 2,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Valor: ${simbolo} ${Number(ctx.raw).toLocaleString()}`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            callback: (v) => `${simbolo} ${(v / 1e6).toFixed(1)}M`
                        }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 2. Gráfico: Volumen Físico (Pares)
    const ctxPares = document.getElementById("chart-comercio-pares");
    if (ctxPares) {
        if (AppState.charts.comercioPares) AppState.charts.comercioPares.destroy();

        AppState.charts.comercioPares = new Chart(ctxPares, {
            type: "bar",
            data: {
                labels: serieTemporal.anios || ["2020", "2021", "2022", "2023", "2024"],
                datasets: [
                    {
                        label: "Volumen Físico Registrado (Pares)",
                        data: serieTemporal.cantidades_pares || [],
                        backgroundColor: "rgba(245, 158, 11, 0.75)",
                        borderColor: "#f59e0b",
                        borderWidth: 2,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `Volumen: ${Number(ctx.raw).toLocaleString()} pares`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(255, 255, 255, 0.05)" },
                        ticks: {
                            callback: (v) => `${(v / 1e6).toFixed(1)}M pares`
                        }
                    },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

async function ejecutarCalculoEscenario() {
    const catSel = document.getElementById("calc-categoria-sel")?.value || "640411";
    const paresInput = document.getElementById("calc-cantidad-pares");
    const pVentaInput = document.getElementById("calc-precio-venta");
    const margenInput = document.getElementById("calc-margen-objetivo");
    const cvInput = document.getElementById("calc-cv-fabril");
    const cfEvInput = document.getElementById("calc-cf-evitables");
    const cfPermInput = document.getElementById("calc-cf-permanentes");
    const pCompraInput = document.getElementById("calc-p-compra");
    const fleteInput = document.getElementById("calc-flete");
    const seguroInput = document.getElementById("calc-seguro");
    const arancelInput = document.getElementById("calc-arancel");
    const logisticaInput = document.getElementById("calc-logistica");
    const otrosInput = document.getElementById("calc-otros");

    const cantidadPares = Math.max(0, parseInt(paresInput?.value || "1000"));
    const margenPct = Math.min(99.0, Math.max(0.0, parseFloat(margenInput?.value || "35.0")));

    const payload = {
        codigo_sa6: catSel,
        cantidad_pares: cantidadPares,
        precio_venta: parseFloat(pVentaInput?.value || "0"),
        margen_objetivo_pct: margenPct,
        costo_variable_unitario_fab: parseFloat(cvInput?.value || "0"),
        costos_fijos_evitables: parseFloat(cfEvInput?.value || "0"),
        costos_fijos_permanentes: parseFloat(cfPermInput?.value || "0"),
        cotizacion_compra: parseFloat(pCompraInput?.value || "0"),
        flete_transporte: parseFloat(fleteInput?.value || "0"),
        seguro_transporte: parseFloat(seguroInput?.value || "0"),
        gastos_internacion: parseFloat(arancelInput?.value || "0"),
        entrega_local: parseFloat(logisticaInput?.value || "0"),
        otros_gastos: parseFloat(otrosInput?.value || "0"),
        moneda: AppState.monedaActual,
        tasa_cambio: AppState.tasaCambio
    };

    try {
        const res = await fetch("/api/escenarios/calcular", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.exito) {
            AppState.ultimoResultadoEscenario = data;
            actualizarResultadosEscenarioUI(data);
        }
    } catch (e) {
        console.error("Error al calcular escenario:", e);
    }
}

function actualizarResultadosEscenarioUI(data) {
    const esBob = (AppState.monedaActual === "BOB");
    const tc = AppState.tasaCambio;
    const simbolo = esBob ? "Bs." : "$us.";

    const fab = data.fabricacion;
    const imp = data.importacion;
    const diff = data.analisis_diferencial;

    // 1. Tarjeta de Decisión Estratégica
    const cardOutcome = document.getElementById("card-decision-outcome");
    const pillResult = document.getElementById("pill-decision-result");
    const tagDiff = document.getElementById("tag-decision-diff");
    const narrativeResult = document.getElementById("narrative-decision-result");
    const boxIndiff = document.getElementById("box-indifference-q");
    const valIndiff = document.getElementById("val-indiff-q");

    if (cardOutcome && pillResult && tagDiff && narrativeResult) {
        cardOutcome.classList.remove("decision-fab", "decision-imp", "decision-eq");

        if (diff.decision_recomendada === "FABRICAR") {
            cardOutcome.classList.add("decision-fab");
            pillResult.textContent = "RECOMENDACIÓN: FABRICAR LOCALMENTE";
            pillResult.style.background = "rgba(6, 182, 212, 0.25)";
            pillResult.style.color = "#38bdf8";
        } else if (diff.decision_recomendada === "IMPORTAR") {
            cardOutcome.classList.add("decision-imp");
            pillResult.textContent = "RECOMENDACIÓN: IMPORTAR EXTERIOR";
            pillResult.style.background = "rgba(245, 158, 11, 0.25)";
            pillResult.style.color = "#fbbf24";
        } else {
            cardOutcome.classList.add("decision-eq");
            pillResult.textContent = "RECOMENDACIÓN: COSTOS EQUIVALENTES";
            pillResult.style.background = "rgba(139, 92, 246, 0.25)";
            pillResult.style.color = "#c084fc";
        }

        const difMonto = esBob ? diff.diferencia_costo_bob : diff.diferencia_costo_usd;
        tagDiff.textContent = `Diferencial Lote: ${simbolo} ${Math.abs(difMonto).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        narrativeResult.textContent = diff.mensaje;

        if (boxIndiff && valIndiff) {
            if (diff.punto_indiferencia_pares !== null && diff.punto_indiferencia_pares > 0) {
                boxIndiff.style.display = "flex";
                valIndiff.textContent = diff.punto_indiferencia_pares.toLocaleString();
            } else {
                boxIndiff.style.display = "none";
            }
        }
    }

    // 2. Resultados Fabricación
    const cuFab = esBob ? fab.costo_unitario_total_bob : fab.costo_unitario_total_usd;
    const ctFab = esBob ? fab.costo_total_lote_bob : fab.costo_total_lote_usd;
    const ppFab = esBob ? fab.precio_propuesto_bob : fab.precio_propuesto_usd;

    const elCuFab = document.getElementById("res-cu-fab");
    const elCtFab = document.getElementById("res-ct-fab");
    const elMbFab = document.getElementById("res-mb-fab");
    const elPpFab = document.getElementById("res-pp-fab");

    if (elCuFab) elCuFab.textContent = `${simbolo} ${cuFab.toFixed(2)}`;
    if (elCtFab) elCtFab.textContent = `${simbolo} ${ctFab.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (elMbFab) elMbFab.textContent = `${fab.margen_bruto_pct.toFixed(1)}%`;
    if (elPpFab) elPpFab.textContent = `${simbolo} ${ppFab.toFixed(2)}`;

    // 3. Resultados Importación
    const cuImp = esBob ? imp.costo_unitario_total_bob : imp.costo_unitario_total_usd;
    const ctImp = esBob ? imp.costo_total_lote_bob : imp.costo_total_lote_usd;
    const ppImp = esBob ? imp.precio_propuesto_bob : imp.precio_propuesto_usd;

    const elCuImp = document.getElementById("res-cu-imp");
    const elCtImp = document.getElementById("res-ct-imp");
    const elMbImp = document.getElementById("res-mb-imp");
    const elPpImp = document.getElementById("res-pp-imp");

    if (elCuImp) elCuImp.textContent = `${simbolo} ${cuImp.toFixed(2)}`;
    if (elCtImp) elCtImp.textContent = `${simbolo} ${ctImp.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    if (elMbImp) elMbImp.textContent = `${imp.margen_bruto_pct.toFixed(1)}%`;
    if (elPpImp) elPpImp.textContent = `${simbolo} ${ppImp.toFixed(2)}`;

    // 4. Inventario Activo & Guardado de Precio Propuesto Seleccionado
    if (data.precio_activo_inventario) {
        const act = data.precio_activo_inventario;
        const elActCat = document.getElementById("res-act-cat");
        const elActPrecio = document.getElementById("res-act-precio");
        const elActPrecioUsd = document.getElementById("res-act-precio-usd");
        const elActStock = document.getElementById("res-act-stock");

        if (elActCat) elActCat.textContent = act.categoria;
        if (elActPrecio) elActPrecio.textContent = `Bs. ${act.precio_unitario_bs.toFixed(2)}`;
        if (elActPrecioUsd) elActPrecioUsd.textContent = `$us. ${act.precio_unitario_usd.toFixed(2)}`;
        if (elActStock) elActStock.textContent = `${act.stock_actual} pares`;

        // Selección de precio propuesto según alternativa recomendada o por defecto fabricación
        let precioPropuestoFinalBs = 0;
        let precioPropuestoFinalUsd = 0;
        let fuenteRecomendada = "Fabricación Local";

        if (diff.decision_recomendada === "IMPORTAR") {
            precioPropuestoFinalBs = imp.precio_propuesto_bob;
            precioPropuestoFinalUsd = imp.precio_propuesto_usd;
            fuenteRecomendada = "Importación Externa";
        } else {
            precioPropuestoFinalBs = fab.precio_propuesto_bob;
            precioPropuestoFinalUsd = fab.precio_propuesto_usd;
            fuenteRecomendada = "Fabricación Local";
        }

        AppState.ultimoPrecioPropuesto = {
            id_producto: act.id_producto,
            categoria: act.categoria,
            precio_bs: precioPropuestoFinalBs,
            precio_usd: precioPropuestoFinalUsd,
            fuente: fuenteRecomendada
        };
    }
}

async function cargarEscenarioPreset(tipo) {
    document.querySelectorAll(".btn-preset-scenario").forEach(btn => {
        btn.classList.toggle("active", btn.getAttribute("data-preset") === tipo);
    });

    try {
        const res = await fetch(`/api/escenarios/predefinido/${tipo}`);
        const data = await res.json();

        if (data.exito && data.parametros) {
            const p = data.parametros;
            const tc = AppState.tasaCambio;
            const esBob = (AppState.monedaActual === "BOB");
            const factor = esBob ? tc : 1.0;

            const catSel = document.getElementById("calc-categoria-sel");
            if (catSel) catSel.value = String(p.codigo_sa6);

            const qInput = document.getElementById("calc-cantidad-pares");
            if (qInput) qInput.value = p.cantidad_pares;

            const pVenta = document.getElementById("calc-precio-venta");
            if (pVenta) pVenta.value = (p.precio_venta * factor).toFixed(2);

            const margen = document.getElementById("calc-margen-objetivo");
            if (margen) margen.value = p.margen_objetivo_pct.toFixed(1);

            const cv = document.getElementById("calc-cv-fabril");
            if (cv) cv.value = (p.costo_variable_unitario_fab * factor).toFixed(2);

            const cfEv = document.getElementById("calc-cf-evitables");
            if (cfEv) cfEv.value = (p.costos_fijos_evitables * factor).toFixed(2);

            const cfPerm = document.getElementById("calc-cf-permanentes");
            if (cfPerm) cfPerm.value = (p.costos_fijos_permanentes * factor).toFixed(2);

            const pComp = document.getElementById("calc-p-compra");
            if (pComp) pComp.value = (p.cotizacion_compra * factor).toFixed(2);

            const flete = document.getElementById("calc-flete");
            if (flete) flete.value = (p.flete_transporte * factor).toFixed(2);

            const seg = document.getElementById("calc-seguro");
            if (seg) seg.value = (p.seguro_transporte * factor).toFixed(2);

            const aranc = document.getElementById("calc-arancel");
            if (aranc) aranc.value = (p.gastos_internacion * factor).toFixed(2);

            const log = document.getElementById("calc-logistica");
            if (log) log.value = (p.entrega_local * factor).toFixed(2);

            const otros = document.getElementById("calc-otros");
            if (otros) otros.value = (p.otros_gastos * factor).toFixed(2);

            actualizarCardInventarioActivo(String(p.codigo_sa6));
            ejecutarCalculoEscenario();
        }
    } catch (e) {
        console.error("Error al cargar escenario predefinido:", e);
    }
}

async function actualizarCardInventarioActivo(codigoSa6) {
    try {
        const res = await fetch("/api/estado");
        const datos = await res.json();
        if (datos.exito && datos.inventario) {
            const item = datos.inventario.find(x => String(x.codigo_sa6) === String(codigoSa6));
            if (item) {
                const elCat = document.getElementById("res-act-cat");
                const elBs = document.getElementById("res-act-precio");
                const elUsd = document.getElementById("res-act-precio-usd");
                const elStock = document.getElementById("res-act-stock");

                if (elCat) elCat.textContent = item.categoria_corta;
                if (elBs) elBs.textContent = `Bs. ${item.precio_unitario_bs.toFixed(2)}`;
                if (elUsd) elUsd.textContent = `$us. ${item.precio_unitario_usd.toFixed(2)}`;
                if (elStock) elStock.textContent = `${item.stock_actual} pares`;
            }
        }
    } catch (e) {
        console.error("Error al actualizar tarjeta de inventario activo:", e);
    }
}

async function aplicarPrecioAlInventario() {
    if (!AppState.ultimoPrecioPropuesto) {
        alert("Primero ejecuta el cálculo de un escenario para obtener un precio propuesto.");
        return;
    }

    const { id_producto, categoria, precio_bs, precio_usd, fuente } = AppState.ultimoPrecioPropuesto;

    const confirmacion = confirm(
        `¿Deseas aplicar el precio propuesto por el escenario al inventario activo?\n\n` +
        `• Categoría: ${categoria}\n` +
        `• Nuevo Precio en Tienda: Bs. ${precio_bs.toFixed(2)} ($us. ${precio_usd.toFixed(2)})\n` +
        `• Alternativa origen: ${fuente}\n\n` +
        `NOTA: Esta acción actualizará exclusivamente el precio oficial en el catálogo sin alterar las existencias de calzado en bodega.`
    );

    if (!confirmacion) return;

    try {
        const res = await fetch("/api/inventario/aplicar-precio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                id_producto: id_producto,
                nuevo_precio_bs: precio_bs,
                nuevo_precio_usd: precio_usd,
                responsable: "Gerente Comercial Manaco (Módulo Make-or-Buy)"
            })
        });
        const datos = await res.json();

        if (datos.exito) {
            reproducirSonido("exito");
            alert(datos.mensaje || `Precio de ${categoria} actualizado con éxito a Bs. ${precio_bs.toFixed(2)}`);
            cargarDatosDashboard(false);
            cargarMovimientos();
            ejecutarCalculoEscenario();
        } else {
            alert(`Error al actualizar precio: ${datos.error}`);
        }
    } catch (e) {
        console.error("Error al aplicar precio:", e);
    }
}
