document.addEventListener('DOMContentLoaded', function() {
    // --- 1. NAVEGAÇÃO E ESTADO GLOBAL ---
    const navLinks = document.querySelectorAll('.nav-item');
    const logoLink = document.getElementById('logo-link'); // Seleciona o novo link pelo ID
    logoLink.addEventListener('click', (e) => {
        e.preventDefault(); // Impede o recarregamento da página
        showPage('dashboard'); // Mostra a página do dashboard
    });
    const pages = document.querySelectorAll('.page');
    let currentSupplierId = null;
    let currentSetorId = null;
    let consumptionChart = null; // Para o gráfico de detalhes do setor
    let dashboardSetorChart = null; // Para o gráfico de rosca do dashboard
    let dashboardTendenciaChart = null; // Para o gráfico de linha do dashboard

    function showPage(pageId, context = null) {
        pages.forEach(p => p.classList.add('hidden'));
        const pageToShow = document.getElementById(pageId);
        if (pageToShow) {
            pageToShow.classList.remove('hidden');
        }

        const mainPage = pageId.split('-')[0];
        navLinks.forEach(l => {
            l.classList.toggle('active', l.dataset.page === mainPage);
        });

        // Limpa gráficos de outras páginas para evitar conflitos
        if (consumptionChart && pageId !== 'setor-detail-page') {
            consumptionChart.destroy();
            consumptionChart = null;
        }
        if ((dashboardSetorChart || dashboardTendenciaChart) && pageId !== 'dashboard') {
            if(dashboardSetorChart) dashboardSetorChart.destroy();
            if(dashboardTendenciaChart) dashboardTendenciaChart.destroy();
            dashboardSetorChart = null;
            dashboardTendenciaChart = null;
        }


        const id = (typeof context === 'object' && context !== null) ? context.id : context;
        const mode = (typeof context === 'object' && context !== null) ? context.mode : 'create';

        switch (pageId) {
            case 'dashboard':
                initDashboardPage();
                break;
            case 'estoque':
                initEstoquePage();
                break;
            case 'transferencia':
                initTransferenciaPage();
                break;
            case 'fornecedores':
                initFornecedoresPage();
                break;
            case 'fornecedor-form-page':
                initFornecedorFormPage(id);
                break;
            case 'fornecedor-detail-page':
                currentSupplierId = id;
                initFornecedorDetailPage(id);
                break;
            case 'setores':
                initSetoresPage();
                break;
            case 'setor-detail-page':
                currentSetorId = id;
                initSetorDetailPage(id);
                break;
            case 'recebimento':
                initRecebimentoPage();
                break;
            case 'consulta-notas':
                initConsultaNotasPage();
                break;
            case 'registro-compra':
                initRegistroCompraPage({ id, mode });
                break;
            case 'lista-compras':
                initListaComprasPage();
                break;
            case 'inventario':
                initInventarioPage();
                break;
        }
    }


    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showPage(link.dataset.page);
        });
    });

    // --- 2. SEÇÃO DO DASHBOARD (CORRIGIDA E UNIFICADA) ---

function initDashboardPage() {
    console.log("Dashboard com rotas separadas inicializado.");

    // --- Seletores de Elementos ---
    const kpiTotalItens = document.getElementById('kpi-total-itens');
    const kpiValorTotal = document.getElementById('kpi-valor-total');
    const kpiConsumoDiario = document.getElementById('kpi-consumo-diario');
    const kpiItensCriticos = document.getElementById('kpi-itens-criticos');
    const filtroStatus = document.getElementById('filtro-status');
    const filtroSetor = document.getElementById('filtro-setor');
    const filtroPeriodo = document.getElementById('filtro-periodo');
    const filtroBusca = document.getElementById('filtro-busca');
    const tableBody = document.getElementById('dashboard-table-body');
    const paginationContainer = document.getElementById('dashboard-pagination');
    const statusExcelente = document.getElementById('status-excelente');
    const statusBom = document.getElementById('status-bom');
    const statusAtencao = document.getElementById('status-atencao');
    const statusCritico = document.getElementById('status-critico');
    const setorChartCanvas = document.getElementById('dashboard-setor-chart');
    const tendenciaChartCanvas = document.getElementById('dashboard-tendencia-chart');

    let debounceTimer;

    const formatarMoeda = (valor) => {
        const numero = valor || 0;
        return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    };

    // --- Funções de Renderização (Gráficos e Paginação) ---
    const renderSetorChart = (chartData) => {
        if (dashboardSetorChart) dashboardSetorChart.destroy();
        if (!chartData || chartData.labels.length === 0) { return; }
        dashboardSetorChart = new Chart(setorChartCanvas, {
            type: 'doughnut', data: { labels: chartData.labels, datasets: [{ data: chartData.data, backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'], borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
        });
    };

    const renderTendenciaChart = (chartData) => {
        if (dashboardTendenciaChart) dashboardTendenciaChart.destroy();
        if (!chartData || chartData.labels.length === 0) { return; }
        dashboardTendenciaChart = new Chart(tendenciaChartCanvas, {
            type: 'line', data: { labels: chartData.labels, datasets: [{ label: 'Consumo Diário (R$)', data: chartData.data, borderColor: '#3B82F6', backgroundColor: 'rgba(59, 130, 246, 0.1)', fill: true, tension: 0.3 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
        });
    };

    const renderPagination = (paginationData, currentPage) => {
        // ... (código da paginação que já está correto) ...
    };

    // --- Funções de Carregamento de Dados ---
    
    // 1. Função para carregar KPIs, Tabela e Resumo
    const loadMainData = (page = 1) => {
        const params = new URLSearchParams({ page: page, periodo: filtroPeriodo.value, busca: filtroBusca.value.trim(), status: filtroStatus.value });
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-10 text-gray-500">A carregar dados...</td></tr>';

        fetch(`/api/dashboard/main?${params.toString()}`)
            .then(res => res.ok ? res.json() : res.json().then(err => Promise.reject(err.error)))
            .then(data => {
                if (filtroSetor.options.length <= 1 && data.filter_options && data.filter_options.setores) {
                        data.filter_options.setores.forEach(setor => {
                            filtroSetor.innerHTML += `<option value="${setor.id}">${setor.nome}</option>`;
                        });
                    }
                    if (filtroStatus.options.length <= 1 && data.filter_options && data.filter_options.status) {
                        // Começa do 1 para não duplicar a opção "Todos"
                        for(let i = 1; i < data.filter_options.status.length; i++) {
                            const status = data.filter_options.status[i];
                            filtroStatus.innerHTML += `<option value="${status}">${status}</option>`;
                        }
                    }
     
                
                kpiTotalItens.textContent = data.kpis.total_itens.toLocaleString('pt-BR');
                kpiValorTotal.textContent = formatarMoeda(data.kpis.valor_total);
                kpiConsumoDiario.textContent = formatarMoeda(data.kpis.consumo_diario);
                kpiItensCriticos.textContent = data.kpis.itens_criticos;

                statusExcelente.textContent = data.status_summary.excelente;
                statusBom.textContent = data.status_summary.bom;
                statusAtencao.textContent = data.status_summary.atencao;
                statusCritico.textContent = data.status_summary.critico;

                tableBody.innerHTML = '';
                if (data.table_data.items.length > 0) {
                    data.table_data.items.forEach(item => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `<td class="px-6 py-4 text-sm">${item.descricao}</td><td class="px-6 py-4 text-sm">${item.estoque_atual}</td><td class="px-6 py-4 text-sm">${item.saida_media_diaria}</td><td class="px-6 py-4 text-sm font-bold ${item.status_key === 'critico' || item.status_key === 'atencao' ? 'text-red-500' : 'text-green-500'}">${item.dias_de_estoque}</td><td class="px-6 py-4 text-sm">${item.consumo_qtd}</td><td class="px-6 py-4 text-sm font-semibold">${formatarMoeda(item.consumo_valor)}</td><td class="px-6 py-4 text-sm"><button class="text-blue-600 hover:underline">Detalhes</button></td>`;
                        tableBody.appendChild(tr);
                    });
                } else {
                    tableBody.innerHTML = '<tr><td colspan="7" class="text-center py-10 text-gray-500">Nenhum item encontrado.</td></tr>';
                }
                renderPagination(data.table_data, page);
            })
            .catch(error => {
                tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-10 text-red-500">Falha ao carregar dados da tabela: ${error}</td></tr>`;
            });
    };

    // 2. Função para carregar os dados dos Gráficos
    const loadChartData = () => {
        const params = new URLSearchParams({ periodo: filtroPeriodo.value });
        fetch(`/api/dashboard/charts?${params.toString()}`)
            .then(res => res.ok ? res.json() : Promise.reject('Erro ao carregar dados dos gráficos'))
            .then(data => {
                renderSetorChart(data.setor_chart_data);
                renderTendenciaChart(data.tendencia_chart_data);
            })
            .catch(error => console.error("Chart Error:", error));
    };

    // --- Event Listeners ---
    [filtroStatus, filtroSetor].forEach(el => el.addEventListener('change', () => loadMainData(1)));
    
    filtroPeriodo.addEventListener('change', () => {
        loadMainData(1);
        loadChartData(); // O período afeta ambos
    });

    filtroBusca.addEventListener('keyup', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => { loadMainData(1); }, 500);
    });

    paginationContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('pagination-btn')) {
            const pageNum = e.target.dataset.page;
            if (pageNum) { loadMainData(parseInt(pageNum, 10)); }
        }
    });

    // --- Carga Inicial ---
    loadMainData(1);
    loadChartData();
}
    
    // --- 3. SEÇÃO DE ESTOQUE ---
    function initEstoquePage() {
    console.log("Página de Estoque inicializada.");
    
    // 1. Seletores dos elementos da página
    const tableBody = document.getElementById('estoque-table-body');
    const filtroInsumo = document.getElementById('filtro-insumo');
    const filtroPosicao = document.getElementById('filtro-posicao');
    const btnFiltrar = document.getElementById('btn-filtrar');
    const btnLimpar = document.getElementById('btn-limpar-filtro');
    const btnExportar = document.getElementById('btn-exportar-excel');
    const modalDetalhes = document.getElementById('modal-detalhes'); // Garante que o modal está selecionado

    // 2. Função para mostrar o pop-up com os detalhes do item
    const showDetalhesModal = async (estoqueId) => {
        try {
            const response = await fetch(`/api/estoque/item/${estoqueId}`);
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Item não encontrado.');
            }
            const item = await response.json();
            const valorUnitarioFmt = `R$ ${(item.valor_unitario || 0).toFixed(2).replace('.', ',')}`;
            const valorTotalFmt = `R$ ${(item.valor_total || 0).toFixed(2).replace('.', ',')}`;

            modalDetalhes.innerHTML = `
                    <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl animate-fade-in-up">
                        <div class="flex justify-between items-center border-b pb-3 mb-4">
                            <h3 class="text-xl font-semibold text-gray-800">Detalhes do Item</h3>
                            <button class="text-gray-400 font-bold text-2xl hover:text-gray-600 close-modal-btn">&times;</button>
                        </div>
                        <div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div><span class="detalhe-label">NOME DO INSUMO</span><p class="detalhe-valor">${item.descricao}</p></div>
                                <div><span class="detalhe-label">SKU (CÓDIGO)</span><p class="detalhe-valor">${item.sku}</p></div>
                                <div><span class="detalhe-label">POSIÇÃO</span><p class="detalhe-valor font-bold text-blue-600">${item.posicao}</p></div>
                                <div><span class="detalhe-label">QUANTIDADE</span><p class="detalhe-valor">${item.quantidade} ${item.unidade_medida}</p></div>
                                <div><span class="detalhe-label">ESTOQUE MÍNIMO</span><p class="detalhe-valor">${item.estoque_minimo} ${item.unidade_medida}</p></div>
                                <div><span class="detalhe-label">VALOR UNITÁRIO</span><p class="detalhe-valor">${valorUnitarioFmt}</p></div>
                                <div class="col-span-2"><span class="detalhe-label">VALOR TOTAL NA POSIÇÃO</span><p class="text-lg font-bold text-green-600">${valorTotalFmt}</p></div>
                                
                                <div class="col-span-2 border-t pt-4 mt-2 grid grid-cols-2 gap-4">
                                    <div>
                                        <span class="detalhe-label">ÚLTIMA MOVIMENTAÇÃO</span>
                                        <p class="detalhe-valor text-gray-600">${item.ultima_movimentacao}</p>
                                    </div>
                                    <div>
                                        <span class="detalhe-label">MOVIMENTADO POR</span>
                                        <p class="detalhe-valor text-gray-600 font-semibold">${item.usuario_movimentacao}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="flex justify-end mt-6">
                            <button type="button" class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-lg close-modal-btn">Fechar</button>
                        </div>
                    </div>`;
                modalDetalhes.classList.remove('hidden');
            } catch (error) {
                alert(`Erro ao carregar detalhes: ${error.message}`);
            }
        };


    // 3. Função para carregar e renderizar a tabela de estoque
    const loadEstoque = () => {
    // Remove todos os espaços do campo de posição
        const posicaoLimpa = filtroPosicao.value.replace(/\s/g, '');

        const params = new URLSearchParams({
            insumo: filtroInsumo.value.trim(),
            posicao: posicaoLimpa
    });
        fetch(`/api/estoque/posicao_geral?${params.toString()}`)
            .then(res => res.ok ? res.json() : Promise.reject(res))
            .then(data => {
                tableBody.innerHTML = '';
                if (!data || data.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-gray-500">Nenhum item encontrado.</td></tr>`;
                    return;
                }
                data.forEach(item => {
                    const tr = document.createElement('tr');
                    // Corrige a exibição da quantidade para incluir a unidade de medida
                    tr.innerHTML = `
                        <td class="px-6 py-4">${item.sku}</td>
                        <td class="px-6 py-4">${item.descricao}</td>
                        <td class="px-6 py-4">${item.posicao}</td>
                        <td class="px-6 py-4">${item.quantidade} ${item.unidade_medida}</td>
                        <td class="px-6 py-4">${item.valor_unitario}</td>
                        <td class="px-6 py-4 font-semibold">${item.valor_total}</td>
                        <td class="px-6 py-4"><a href="#" class="text-blue-600 hover:underline detalhes-btn" data-estoque-id="${item.estoque_id}">Detalhes</a></td>`;
                    tableBody.appendChild(tr);
                });
            })
            .catch(err => {
                console.error("Erro ao carregar estoque:", err);
                tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-red-500">Erro ao carregar os dados.</td></tr>`;
            });
    };

    // 4. Adiciona os "escutadores de eventos"
    btnFiltrar.addEventListener('click', loadEstoque);
    btnLimpar.addEventListener('click', () => {
        filtroInsumo.value = '';
        filtroPosicao.value = '';
        loadEstoque();
    });
    btnExportar.addEventListener('click', () => { window.location.href = '/api/estoque/exportar'; });

    // Evento na tabela para capturar cliques nos botões "Detalhes"
    tableBody.addEventListener('click', (e) => {
        if (e.target.classList.contains('detalhes-btn')) {
            e.preventDefault();
            showDetalhesModal(e.target.dataset.estoqueId);
        }
    });

    // Evento no pop-up para o fechar
    modalDetalhes.addEventListener('click', (e) => {
        if (e.target === modalDetalhes || e.target.closest('.close-modal-btn')) {
            modalDetalhes.classList.add('hidden');
        }
    });

    // 5. Carga inicial dos dados
    loadEstoque();
}


    // --- 4. SEÇÃO DE TRANSFERÊNCIA ---
    function initTransferenciaPage() {
    console.log("Página de Transferência inicializada.");
    const form = document.getElementById('form-transferencia');
    if (!form) return;

    // Seletores dos elementos da página
    const skuInput = document.getElementById('sku-insumo');
    const btnBuscar = document.getElementById('btn-buscar-insumo');
    const camposExpandidos = document.getElementById('campos-expandidos');
    const nomeInsumo = document.getElementById('nome-insumo');
    const posicaoAtualSelect = document.getElementById('posicao-atual');
    const qtdDisponivelInput = document.getElementById('qtd-disponivel');
    const qtdTransferirInput = document.getElementById('qtd-transferir');
    const maxQtdSmall = document.getElementById('max-qtd');
    const destinoInput = document.getElementById('destino-transferencia');
    const btnCancelar = document.getElementById('btn-cancelar-transferencia');
    let posicoesCache = [];

    // Funções de apoio
    const resetForm = () => {
        form.reset();
        camposExpandidos.classList.add('hidden');
        posicaoAtualSelect.innerHTML = '';
        posicoesCache = [];
    };

    const atualizarCamposPosicao = () => {
        const selectedOption = posicaoAtualSelect.options[posicaoAtualSelect.selectedIndex];
        if (!selectedOption) return;
        const qtd = selectedOption.dataset.quantidade;
        const unidade = selectedOption.dataset.unidade;
        qtdDisponivelInput.value = `${qtd} ${unidade}`;
        qtdTransferirInput.max = qtd;
        maxQtdSmall.textContent = `Máx: ${qtd} ${unidade}`;
    };

    const buscarInsumo = async () => {
        const sku = skuInput.value.trim();
        if (!sku) { alert('Digite o SKU.'); return; }
        try {
            const resInsumo = await fetch(`/api/insumos/sku/${sku}`);
            if (!resInsumo.ok) throw new Error('Insumo não encontrado.');
            const dataInsumo = await resInsumo.json();
            nomeInsumo.value = dataInsumo.descricao;

            const resPosicoes = await fetch(`/api/estoque/posicoes/${sku}`);
            if (!resPosicoes.ok) throw new Error('Nenhuma posição de estoque encontrada.');
            posicoesCache = await resPosicoes.json();
            if (posicoesCache.length === 0) { alert('Não há estoque para este insumo.'); resetForm(); return; }

            posicaoAtualSelect.innerHTML = '';
            posicoesCache.forEach(p => {
                const option = document.createElement('option');
                option.value = p.posicao;
                option.textContent = `${p.posicao} (Disp: ${p.quantidade} ${p.unidade})`;
                option.dataset.quantidade = p.quantidade;
                option.dataset.unidade = p.unidade;
                posicaoAtualSelect.appendChild(option);
            });
            atualizarCamposPosicao();
            camposExpandidos.classList.remove('hidden');
        } catch (error) {
            alert(`Erro: ${error.message}`);
            resetForm();
        }
    };

    const submeterTransferencia = async (e) => {
        e.preventDefault();
        const selectedOption = posicaoAtualSelect.options[posicaoAtualSelect.selectedIndex];
        const quantidadeTransferir = parseFloat(qtdTransferirInput.value);
        if(!selectedOption) { alert("Selecione uma posição de origem."); return; }
        const quantidadeDisponivel = parseFloat(selectedOption.dataset.quantidade);

        if (quantidadeTransferir <= 0 || quantidadeTransferir > quantidadeDisponivel) {
            alert('Quantidade inválida ou maior que o estoque disponível.');
            return;
        }

        const payload = {
            sku: skuInput.value.trim(),
            posicao_origem: selectedOption.value,
            qtd: quantidadeTransferir,
            destino: destinoInput.value.trim()
        };

        try {
            const response = await fetch('/api/transferencias', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            alert(result.message);
            resetForm();
        } catch (error) {
            alert(`Erro na transferência: ${error.message}`);
        }
    };

    // --- LIGAÇÃO DOS EVENTOS (CORRIGIDA) ---
    // Usar .onsubmit e .onclick garante que apenas uma função esteja ligada,
    // substituindo qualquer anterior e evitando duplicação.
    form.onsubmit = submeterTransferencia;
    btnBuscar.onclick = buscarInsumo;
    btnCancelar.onclick = resetForm;
    posicaoAtualSelect.onchange = atualizarCamposPosicao;
    
    // Estado inicial da página
    resetForm();
}


    // --- 5. SEÇÃO DE FORNECEDORES ---
    function initFornecedoresPage() {
        const tableBody = document.getElementById('fornecedores-table-body');
        const btnNovo = document.getElementById('btn-novo-fornecedor');
        const btnExportar = document.getElementById('btn-exportar-fornecedores');

        async function loadFornecedores() {
            try {
                const response = await fetch('/api/fornecedores');
                const fornecedores = await response.json();
                tableBody.innerHTML = '';
                if(fornecedores.length === 0) { tableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4 text-gray-500">Nenhum fornecedor.</td></tr>`; return; }
                fornecedores.forEach(f => {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-gray-50 cursor-pointer';
                    tr.dataset.id = f.id;
                    tr.innerHTML = `<td class="px-6 py-4 text-sm font-medium text-blue-600">${f.razao_social}</td><td class="px-6 py-4 text-sm">${f.cnpj}</td><td class="px-6 py-4 text-sm"><span class="px-2 inline-flex text-xs font-semibold rounded-full ${f.ativo ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${f.ativo ? 'Ativo' : 'Inativo'}</span></td>`;
                    tr.addEventListener('click', () => showPage('fornecedor-detail-page', f.id));
                    tableBody.appendChild(tr);
                });
            } catch (error) { console.error("Erro:", error); tableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4 text-red-500">Erro.</td></tr>`; }
        }
        btnNovo.onclick = () => showPage('fornecedor-form-page');
        if (btnExportar) {
            btnExportar.addEventListener('click', () => {
                window.location.href = '/api/fornecedores/exportar';
            });
        }

        loadFornecedores();
    }
   
    
    async function initFornecedorFormPage(id = null) {
        const form = document.getElementById('form-add-fornecedor');
        const pageTitle = form.closest('.page').querySelector('h3');
        const submitButton = form.querySelector('button[type="submit"]');
        const btnCancelar = document.getElementById('btn-cancelar-form');
        form.reset();
        if (id) {
            pageTitle.textContent = 'Editar Fornecedor';
            submitButton.textContent = 'Salvar Alterações';
            try {
                const response = await fetch(`/api/fornecedores/${id}`);
                const data = await response.json();
                if (!response.ok) throw new Error(data.error);
                Object.keys(data).forEach(key => { const field = form.querySelector(`[name="${key}"]`); if (field) { if (field.type === 'checkbox') { field.checked = data[key]; } else { field.value = data[key] || ''; } } });
            } catch (error) { alert(`Erro: ${error.message}`); showPage('fornecedores'); }
        } else { pageTitle.textContent = 'Cadastro de Fornecedor'; submitButton.textContent = 'Cadastrar Fornecedor'; }
        form.onsubmit = async function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            data.ativo = formData.has('ativo');
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/fornecedores/${id}` : '/api/fornecedores';
            try {
                const response = await fetch(url, { method: method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error);
                alert(result.message);
                form.reset();
                showPage(id ? 'fornecedor-detail-page' : 'fornecedores', id);
            } catch (error) { console.error("Erro:", error); alert(`Erro: ${error.message}`); }
        };
        btnCancelar.onclick = () => showPage(id ? 'fornecedor-detail-page' : 'fornecedores', id);
    }
    async function initFornecedorDetailPage(id) {
        const detailPage = document.getElementById('fornecedor-detail-page');
        detailPage.innerHTML = `<div class="text-center py-10">Carregando...</div>`;
        try {
            const [resFornecedor, resNcs] = await Promise.all([ fetch(`/api/fornecedores/${id}`), fetch(`/api/fornecedores/${id}/ncs`) ]);
            if (!resFornecedor.ok) throw new Error('Fornecedor não encontrado.');
            const fornecedor = await resFornecedor.json();
            const ncs = await resNcs.json();
            renderizarDetalhesFornecedor(detailPage, fornecedor, ncs);
        } catch (error) { detailPage.innerHTML = `<div class="text-center py-10 text-red-500">Erro: ${error.message}</div>`; }
    }
    function renderizarDetalhesFornecedor(container, f, ncs) {
        container.innerHTML = `<div class="flex justify-between items-center mb-6"><h2 class="text-2xl font-bold">${f.razao_social}</h2><div class="flex items-center gap-4"><button id="btn-editar-fornecedor" title="Editar" class="p-2 rounded-full hover:bg-gray-200"><svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.5L15.232 5.232z"></path></svg></button><button id="btn-voltar-lista" class="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300">Voltar</button></div></div><div class="bg-white p-8 rounded-lg shadow-lg space-y-8"><div><h3 class="text-lg font-semibold border-b pb-2 mb-4">Informações</h3><div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm"><div><strong>CNPJ:</strong> ${f.cnpj}</div><div><strong>Telefone:</strong> ${f.telefone}</div><div><strong>Email:</strong> ${f.email}</div><div><strong>Nome Fantasia:</strong> ${f.nome_fantasia || 'N/A'}</div><div><strong>Website:</strong> ${f.website ? `<a href="${f.website}" target="_blank" class="text-blue-600">${f.website}</a>` : 'N/A'}</div><div><strong>Status:</strong> ${f.ativo ? 'Ativo' : 'Inativo'}</div></div></div><div><h3 class="text-lg font-semibold border-b pb-2 mb-4">Não Conformidades</h3><form id="form-add-nc" class="mb-6 bg-gray-50 p-4 rounded-lg"><label for="nc-descricao" class="block text-sm font-medium">Nova Ocorrência</label><textarea id="nc-descricao" name="descricao" rows="3" required class="mt-1 block w-full border-gray-300 rounded-md"></textarea><label for="nc-acao" class="block text-sm font-medium mt-2">Ação Tomada</label><input id="nc-acao" name="acao_tomada" type="text" class="mt-1 block w-full border-gray-300 rounded-md"><button type="submit" class="mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700">Registrar</button></form><div id="nc-list" class="space-y-3">${ncs.length === 0 ? '<p class="text-gray-500">Nenhuma NC registrada.</p>' : ''}${ncs.map(nc => `<div class="border p-3 rounded-md"><p class="font-semibold">${nc.descricao}</p><p class="text-sm text-gray-600">Ação: ${nc.acao_tomada || 'Nenhuma'}</p><p class="text-xs text-gray-400 text-right">Data: ${nc.data_ocorrido}</p></div>`).join('')}</div></div></div>`;
        container.querySelector('#btn-voltar-lista').onclick = () => showPage('fornecedores');
        container.querySelector('#btn-editar-fornecedor').onclick = () => showPage('fornecedor-form-page', currentSupplierId);
        container.querySelector('#form-add-nc').onsubmit = async (e) => {
            e.preventDefault();
            const form = e.target;
            const data = { descricao: form.querySelector('#nc-descricao').value, acao_tomada: form.querySelector('#nc-acao').value };
            try {
                const response = await fetch(`/api/fornecedores/${currentSupplierId}/ncs`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error);
                alert(result.message);
                initFornecedorDetailPage(currentSupplierId);
            } catch (error) { alert(`Erro: ${error.message}`); }
        };
    }
    
    // --- 6. SEÇÃO DE SETORES ---
    async function initSetoresPage() {
        const container = document.getElementById('setores-card-container');
        container.innerHTML = '<p>Carregando setores...</p>';
        try {
            const response = await fetch('/api/setores');
            const setores = await response.json();
            container.innerHTML = '';
            if (setores.length === 0) { container.innerHTML = '<p>Nenhum setor cadastrado.</p>'; return; }
            setores.forEach(setor => {
                const card = document.createElement('div');
                card.className = 'bg-white p-6 rounded-lg shadow-md hover:shadow-xl hover:-translate-y-1 transition-all cursor-pointer';
                card.innerHTML = `<h3 class="text-xl font-bold text-gray-800">${setor.nome}</h3><p class="text-gray-500 text-sm">Análise de consumo</p><div class="text-right mt-4"><span class="text-blue-600 font-semibold">Ver detalhes</span></div>`;
                card.addEventListener('click', () => showPage('setor-detail-page', setor.id));
                container.appendChild(card);
            });
        } catch (error) { console.error('Erro:', error); container.innerHTML = '<p class="text-red-500">Não foi possível carregar.</p>'; }
    }
    async function initSetorDetailPage(id) {
        const detailPage = document.getElementById('setor-detail-page');
        if (consumptionChart) { consumptionChart.destroy(); }
        const dadosEsqueleto = { setor_nome: 'Carregando...', insumos_mais_consumidos: [], consumo_mensal: { labels: [], data: [] }, consumo_medio_diario: 0, historico: [] };
        renderizarDetalhesSetor(detailPage, dadosEsqueleto);
        try {
            const response = await fetch(`/api/setores/${id}/analytics`);
            if (!response.ok) { const errorData = await response.json(); throw new Error(errorData.error || 'Falha ao carregar.'); }
            const dadosReais = await response.json();
            renderizarDetalhesSetor(detailPage, dadosReais);
        } catch (error) {
            console.error('Erro:', error);
            const titulo = detailPage.querySelector('#setor-detail-title');
            if (titulo) { titulo.textContent = 'Erro ao carregar'; }
            alert(`Não foi possível carregar a análise: ${error.message}`);
        }
    }
    function renderizarDetalhesSetor(container, data) {
        const formatarMoeda = (valor) => {
            const numero = valor || 0;
            return numero.toLocaleString('pt-BR', {
                style: 'currency',
                currency: 'BRL'
            });
        };
        container.innerHTML = `<div class="flex justify-between items-center mb-6"><h2 id="setor-detail-title" class="text-2xl font-bold">${data.setor_nome}</h2><button id="btn-voltar-setores" class="bg-gray-200 px-4 py-2 rounded-lg">Voltar</button></div><div class="space-y-8"><div class="grid grid-cols-1 lg:grid-cols-3 gap-6"><div class="lg:col-span-2 bg-white p-6 rounded-lg shadow-md"><h3 class="font-semibold mb-4">Consumo Mensal</h3><div class="relative h-64 md:h-80"><canvas id="consumoMensalChart"></canvas></div></div><div class="space-y-6"><div class="bg-white p-6 rounded-lg shadow-md"><h3 class="font-semibold">Consumo Médio Diário</h3><p class="text-3xl font-bold text-green-600">${formatarMoeda(data.consumo_medio_diario)}</p></div><div class="bg-white p-6 rounded-lg shadow-md"><h3 class="font-semibold mb-2">Top 5 Insumos</h3><ul class="text-sm space-y-1">${data.insumos_mais_consumidos.length > 0 ? data.insumos_mais_consumidos.map(i => `<li class="flex justify-between"><span>${i.descricao}</span><span class="font-bold">${formatarMoeda(i.valor_total)}</span></li>`).join('') : '<li>Nenhum consumo.</li>'}</ul></div></div></div><div class="bg-white p-6 rounded-lg shadow-md"><h3 class="font-semibold mb-4">Histórico</h3><div class="overflow-x-auto"><table class="min-w-full"><thead class="bg-gray-50"><tr><th class="px-4 py-2 text-left text-xs font-medium">Data</th><th class="px-4 py-2 text-left text-xs font-medium">Insumo</th><th class="px-4 py-2 text-left text-xs font-medium">Qtd</th><th class="px-4 py-2 text-left text-xs font-medium">Valor Total</th></tr></thead><tbody class="divide-y">${data.historico.length > 0 ? data.historico.map(h => `<tr><td class="px-4 py-3 text-sm">${h.data}</td><td class="px-4 py-3 text-sm">${h.descricao_insumo}</td><td class="px-4 py-3 text-sm">${h.quantidade.toFixed(2)} ${h.unidade}</td><td class="px-4 py-3 text-sm font-semibold">${formatarMoeda(h.valor_total)}</td></tr>`).join('') : '<tr><td colspan="4" class="text-center py-4 text-gray-500">Nenhum histórico.</td></tr>'}</tbody></table></div></div></div>`;
        container.querySelector('#btn-voltar-setores').onclick = () => showPage('setores');
        const ctx = document.getElementById('consumoMensalChart').getContext('2d');
        if (data.consumo_mensal && data.consumo_mensal.labels.length > 0) {
            consumptionChart = new Chart(ctx, {
                type: 'bar',
                data: { labels: data.consumo_mensal.labels, datasets: [{ label: 'Valor (R$)', data: data.consumo_mensal.data, backgroundColor: 'rgba(59, 130, 246, 0.5)', borderColor: 'rgba(59, 130, 246, 1)', borderWidth: 1 }] },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { callback: (value) => formatarMoeda(value) } } } }
            });
        }
    }

    // --- 7. SEÇÃO DE RECEBIMENTO ---
 function initRecebimentoPage() {
    let itensRecebidos = [];
    const form = document.getElementById('form-recebimento');
    const tabelaItensBody = document.getElementById('tabela-itens-recebimento');
    const resumoTotalItens = document.getElementById('resumo-total-itens');
    const resumoValorTotal = document.getElementById('resumo-valor-total');
    const dataRecebimentoInput = document.getElementById('data_recebimento');
    const btnExtrairPdf = document.getElementById('btn-extrair-pdf');
    const btnLimpar = document.getElementById('btn-limpar-recebimento');
    const btnFinalizar = document.getElementById('btn-finalizar-conferencia');
    if (!form) return;
    
    dataRecebimentoInput.valueAsDate = new Date();
    
    // Inicialização dos selects com Select2
    const selectFornecedor = $('#select-fornecedor').select2({ placeholder: 'Busque por fornecedor', ajax: { url: '/api/fornecedores/buscar', dataType: 'json', delay: 250, processResults: r => ({ results: r }), cache: true } });
    const selectInsumo = $('#select-insumo-recebimento').select2({ placeholder: 'Busque por insumo', ajax: { url: '/api/insumos/buscar', dataType: 'json', delay: 250, processResults: r => ({ results: r }), cache: true } });
    
    const formatarMoeda = (valor) => {
        const numero = valor || 0;
        return numero.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    };

    function renderizarTabelaEAtualizarResumo() {
        tabelaItensBody.innerHTML = '';
        let valorTotalConferido = 0;
        if (itensRecebidos.length === 0) { tabelaItensBody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-gray-500">Nenhum item adicionado à conferência.</td></tr>'; }
        
        itensRecebidos.forEach((item, index) => {
            const classeDestaque = item.novo ? 'bg-blue-50' : (item.quantidade_documento != item.quantidade_conferida ? 'bg-yellow-50' : '');
            const tr = document.createElement('tr');
            tr.className = classeDestaque;
            tr.innerHTML = `
                <td class="px-4 py-2 text-sm align-middle">${item.descricao}</td>
                <td class="align-middle"><input type="number" value="${item.quantidade_documento}" class="w-full border-gray-300 rounded-md item-input" data-index="${index}" data-field="quantidade_documento"></td>
                <td class="align-middle"><input type="number" value="${item.quantidade_conferida}" class="w-full border-gray-300 rounded-md item-input" data-index="${index}" data-field="quantidade_conferida"></td>
                <td class="align-middle"><input type="text" value="${item.posicao_destino}" required placeholder="Ex: A-01-01" class="w-full border-gray-300 rounded-md item-input" data-index="${index}" data-field="posicao_destino"></td>
                <td class="align-middle"><button type="button" class="text-red-600 hover:text-red-900 remover-item-btn" data-index="${index}">Remover</button></td>
            `;
            tabelaItensBody.appendChild(tr);
            valorTotalConferido += (item.quantidade_conferida || 0) * (item.valor_unitario || 0);
        });
        
        resumoTotalItens.textContent = itensRecebidos.length;
        resumoValorTotal.textContent = formatarMoeda(valorTotalConferido);
    }

    function limparTudo() { 
        form.reset(); 
        dataRecebimentoInput.valueAsDate = new Date(); 
        selectFornecedor.val(null).trigger('change'); 
        itensRecebidos = []; 
        renderizarTabelaEAtualizarResumo();
        // Garante que o botão volte ao normal
        btnFinalizar.disabled = false;
        btnFinalizar.textContent = 'Finalizar Conferência e Receber';
    }

    selectInsumo.on('select2:select', (e) => {
        const insumo = e.params.data;
        if (itensRecebidos.some(i => i.insumo_id === insumo.id)) { 
            alert('Insumo já adicionado.'); 
            selectInsumo.val(null).trigger('change'); 
            return; 
        }
        itensRecebidos.push({ 
            insumo_id: insumo.id, 
            descricao: insumo.text, // O Select2 retorna o texto formatado em 'text'
            quantidade_documento: 1, 
            quantidade_conferida: 1, 
            valor_unitario: insumo.valor_unitario, 
            posicao_destino: '', 
            novo: false 
        });
        renderizarTabelaEAtualizarResumo();
        selectInsumo.val(null).trigger('change');
    });

    btnExtrairPdf.addEventListener('click', async () => {
        const fileInput = document.getElementById('pdf-upload-input');
        if (fileInput.files.length === 0) { alert('Selecione um ficheiro PDF primeiro.'); return; }
        const formData = new FormData();
        formData.append('pdf_file', fileInput.files[0]);
        btnExtrairPdf.textContent = 'A extrair...';
        btnExtrairPdf.disabled = true;

        try {
            const response = await fetch('/api/recebimento/upload-pdf', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            if (result.fornecedor) { 
                const option = new Option(result.fornecedor.text, result.fornecedor.id, true, true); 
                selectFornecedor.append(option).trigger('change'); 
            }
            document.getElementById('numero_documento').value = result.numero_documento || '';
            itensRecebidos = result.itens.map(item => ({ ...item, quantidade_conferida: item.quantidade_documento, posicao_destino: '' })) || [];
            renderizarTabelaEAtualizarResumo();
            alert(result.message || "Itens extraídos com sucesso!");
        } catch (error) { 
            alert(`Erro ao processar o PDF: ${error.message}`); 
        } finally {
            btnExtrairPdf.textContent = 'Extrair Itens';
            btnExtrairPdf.disabled = false;
        }
    });

    tabelaItensBody.addEventListener('input', (e) => { 
        if (e.target.classList.contains('item-input')) { 
            const { index, field } = e.target.dataset; 
            const value = e.target.type === 'number' ? parseFloat(e.target.value) || 0 : e.target.value; 
            itensRecebidos[index][field] = value; 
            renderizarTabelaEAtualizarResumo(); 
        } 
    });

    tabelaItensBody.addEventListener('click', (e) => { 
        if (e.target.classList.contains('remover-item-btn')) { 
            const { index } = e.target.dataset; 
            itensRecebidos.splice(index, 1); 
            renderizarTabelaEAtualizarResumo(); 
        } 
    });

    // --- CORREÇÃO PRINCIPAL APLICADA AQUI ---
    btnFinalizar.addEventListener('click', async () => {
        // Validações
        if (!form.checkValidity()) { 
            alert('Por favor, preencha todos os campos obrigatórios (*).'); 
            form.reportValidity(); 
            return; 
        }
        if (itensRecebidos.length === 0) { 
            alert('Adicione pelo menos um item para registrar o recebimento.'); 
            return; 
        }
        if (itensRecebidos.some(item => !item.posicao_destino.trim())) { 
            alert('Todas as posições de destino devem ser preenchidas.'); 
            return; 
        }

        // Desativa o botão para evitar cliques duplos
        btnFinalizar.disabled = true;
        btnFinalizar.textContent = 'A processar...';

        const recebimentoData = { 
            fornecedor_id: selectFornecedor.val(), 
            numero_documento: document.getElementById('numero_documento').value, 
            data_recebimento: dataRecebimentoInput.value, 
            itens: itensRecebidos 
        };

        try {
            const response = await fetch('/api/recebimentos', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(recebimentoData) 
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            alert(result.message);
            limparTudo(); // Limpa o formulário e reativa o botão
        } catch (error) { 
            alert(`Erro ao finalizar recebimento: ${error.message}`);
            // Reativa o botão em caso de erro para permitir nova tentativa
            btnFinalizar.disabled = false;
            btnFinalizar.textContent = 'Finalizar Conferência e Receber';
        }
    });

    btnLimpar.addEventListener('click', limparTudo);
    renderizarTabelaEAtualizarResumo();
}

    // --- 8. SEÇÃO DE CONSULTA DE NOTAS ---
    function initConsultaNotasPage() {
    const inputBusca = document.getElementById('input-busca-nota');
    const btnBuscar = document.getElementById('btn-buscar-nota');
    const containerResultado = document.getElementById('resultado-consulta-container');

    const formatarMoeda = (valor) => {
        const numero = valor || 0;
        return numero.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    };

    async function buscarNota() {
        const numeroNota = inputBusca.value.trim();
        if (!numeroNota) {
            alert('Por favor, digite um número de nota para buscar.');
            return;
        }

        containerResultado.innerHTML = `<p class="text-center text-gray-500">Buscando...</p>`;

        try {
            const response = await fetch(`/api/recebimentos/consultar/${numeroNota}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erro desconhecido');
            }

            // Se encontrou, renderiza os detalhes
            containerResultado.innerHTML = `
                <div class="bg-white p-8 rounded-lg shadow-lg animate-fade-in-up">
                    <div class="border-b pb-4 mb-6">
                        <h3 class="text-xl font-bold text-gray-800">Detalhes do Recebimento</h3>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 text-sm">
                        <div><strong>Número do Documento:</strong><p class="font-semibold text-lg">${data.numero_documento}</p></div>
                        <div><strong>Fornecedor:</strong><p class="font-semibold text-lg">${data.fornecedor_nome}</p></div>
                        <div><strong>Data do Recebimento:</strong><p class="font-semibold text-lg">${data.data_recebimento}</p></div>
                        <div class="md:col-span-3"><strong>Valor Total da Nota:</strong><p class="font-bold text-2xl text-green-600">${formatarMoeda(data.valor_total_documento)}</p></div>
                    </div>

                    <h4 class="text-lg font-semibold text-gray-700 mb-4">Itens da Nota</h4>
                    <div class="overflow-x-auto">
                        <table class="min-w-full">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">SKU</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Descrição</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Qtd. Recebida</th>
                                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Valor Total</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y">
                                ${data.itens.map(item => `
                                    <tr>
                                        <td class="px-4 py-3 text-sm">${item.sku}</td>
                                        <td class="px-4 py-3 text-sm">${item.descricao}</td>
                                        <td class="px-4 py-3 text-sm">${item.quantidade_conferida}</td>
                                        <td class="px-4 py-3 text-sm font-semibold">${formatarMoeda(item.valor_total)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

        } catch (error) {
            containerResultado.innerHTML = `<p class="text-center text-red-500 font-semibold">Erro: ${error.message}</p>`;
        }
    }

    btnBuscar.addEventListener('click', buscarNota);
    // Permite buscar pressionando Enter no campo de input
    inputBusca.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            buscarNota();
        }
    });

    // Limpa o resultado ao iniciar a página
    containerResultado.innerHTML = '';
}
    
    // --- 9. SEÇÃO DE REGISTRO DE COMPRA ---
function initRegistroCompraPage(context = { id: null, mode: 'create' }) {
    const { id, mode } = context;
    const form = document.getElementById('form-registro-compra');
    if (!form) return;

    // Seleção de Elementos
    const pageTitle = form.querySelector('h2');
    const dataCompraInput = document.getElementById('data_compra');
    const containerItens = document.getElementById('compra-itens-container');
    const btnAdicionarItem = document.getElementById('btn-adicionar-item-compra');
    const subtotalEl = document.getElementById('compra-subtotal');
    const freteEl = document.getElementById('compra-frete');
    const impostosEl = document.getElementById('compra-impostos');
    const totalEl = document.getElementById('compra-total');
    const btnCancelar = form.querySelector('#btn-cancelar-compra');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // --- CORREÇÃO APLICADA AQUI ---
    // Inicializa o Select2 para o campo de fornecedor, conectando-o com a API
    const selectFornecedor = $('#compra-select-fornecedor').select2({
        placeholder: 'Busque por razão social ou CNPJ',
        ajax: {
            url: '/api/fornecedores/buscar', // API que busca os fornecedores
            dataType: 'json',
            delay: 250,
            processResults: r => ({ results: r }),
            cache: true
        }
    });

    let itensDaCompra = [];
    let itemCounter = 0;
    const formatarMoeda = (valor) => {
        const numero = valor || 0;
        return numero.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    };

    function calcularTotais() {
        const subtotal = itensDaCompra.reduce((acc, item) => acc + ((item.quantidade || 0) * (item.preco_unitario || 0)), 0);
        const frete = parseFloat(freteEl.value) || 0;
        const impostosPerc = parseFloat(impostosEl.value) || 0;
        const valorImpostos = subtotal * (impostosPerc / 100);
        const total = subtotal + frete + valorImpostos;
        subtotalEl.textContent = formatarMoeda(subtotal);
        totalEl.textContent = formatarMoeda(total);
    }

    function adicionarNovaLinhaDeItem(itemData = null) {
        itemCounter++;
        const novaLinha = {
            idUnico: `item-compra-${itemCounter}`,
            insumo_id: itemData ? itemData.insumo_id : null,
            insumo_text: itemData ? itemData.insumo_text : '',
            quantidade: itemData ? itemData.quantidade : 1,
            preco_unitario: itemData ? itemData.preco_unitario : 0,
        };
        itensDaCompra.push(novaLinha);
        renderizarItens();
    }

    function renderizarItens() {
        containerItens.innerHTML = '';
        itensDaCompra.forEach((item, index) => {
            const itemEl = document.createElement('div');
            itemEl.className = 'grid grid-cols-6 gap-4 items-center';
            itemEl.innerHTML = `<div class="col-span-3"><select id="${item.idUnico}" class="w-full item-select-insumo"></select></div><div><input type="number" value="${item.quantidade}" min="0" data-index="${index}" data-field="quantidade" class="w-full border-gray-300 rounded-md item-compra-input"></div><div><input type="number" value="${item.preco_unitario}" min="0" step="0.01" data-index="${index}" data-field="preco_unitario" class="w-full border-gray-300 rounded-md item-compra-input"></div><div><button type="button" data-index="${index}" class="text-red-500 hover:text-red-700 remover-item-compra-btn">Remover</button></div>`;
            containerItens.appendChild(itemEl);
            const selectEl = $(`#${item.idUnico}`);
            if (item.insumo_id && item.insumo_text) {
                const option = new Option(item.insumo_text, item.insumo_id, true, true);
                selectEl.append(option).trigger('change');
            }
            selectEl.select2({
                placeholder: 'Busque por um insumo',
                ajax: { url: '/api/insumos/buscar', dataType: 'json', delay: 250, processResults: r => ({ results: r }), cache: true }
            }).on('select2:select', (e) => {
                const data = e.params.data;
                itensDaCompra[index].insumo_id = data.id;
                itensDaCompra[index].insumo_text = data.text;
                itensDaCompra[index].preco_unitario = data.valor_unitario || 0;
                renderizarItens();
            });
        });
        calcularTotais();
    }
    
    function setupPageMode() {
        form.reset();
        form.querySelectorAll('input, select, textarea, button').forEach(el => { el.disabled = false; el.style.display = ''; });
        selectFornecedor.val(null).trigger('change');
        itensDaCompra = [];
        containerItens.innerHTML = '';

        if (mode === 'view' && id) {
            pageTitle.textContent = 'Detalhes da Ordem de Compra';
            btnAdicionarItem.style.display = 'none';
            submitButton.style.display = 'none';
            btnCancelar.textContent = 'Voltar para a Lista';
            btnCancelar.onclick = () => showPage('lista-compras');
            
            fetch(`/api/ordens-de-compra/${id}`)
                .then(res => {
                    if(!res.ok) throw new Error('Falha ao buscar dados da ordem.');
                    return res.json();
                })
                .then(data => {
                    Object.keys(data).forEach(key => { const field = form.elements[key]; if (field && field.type !== 'file') { field.value = data[key] || ''; }});
                    
                    if (data.fornecedor_id) {
                         fetch(`/api/fornecedores/${data.fornecedor_id}`)
                           .then(res => res.json())
                           .then(fornecedorData => {
                               const option = new Option(fornecedorData.razao_social, data.fornecedor_id, true, true);
                               selectFornecedor.append(option).trigger('change');
                           });
                    }

                    itensDaCompra = data.itens.map((item, index) => ({ ...item, idUnico: `item-compra-${index}` }));
                    renderizarItens();
                    form.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
                    containerItens.querySelectorAll('button').forEach(btn => btn.style.display = 'none');
                })
                .catch(err => { alert('Erro ao carregar os detalhes da ordem.'); console.error(err); });
        } else {
            pageTitle.textContent = 'Registro de Compra';
            submitButton.textContent = 'Registrar Compra';
            btnCancelar.textContent = 'Cancelar';
            btnCancelar.onclick = () => showPage('dashboard');
            dataCompraInput.valueAsDate = new Date();
            adicionarNovaLinhaDeItem();
        }
    }

    btnAdicionarItem.addEventListener('click', adicionarNovaLinhaDeItem);
    containerItens.addEventListener('input', (e) => { if (e.target.classList.contains('item-compra-input')) { const { index, field } = e.target.dataset; itensDaCompra[index][field] = parseFloat(e.target.value) || 0; calcularTotais(); } });
    containerItens.addEventListener('click', (e) => { if (e.target.classList.contains('remover-item-compra-btn')) { const { index } = e.target.dataset; itensDaCompra.splice(index, 1); renderizarItens(); } });
    [freteEl, impostosEl].forEach(el => el.addEventListener('input', calcularTotais));

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (mode === 'view') return;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        data.fornecedor_id = selectFornecedor.val();
        const itensValidos = itensDaCompra.filter(item => item.insumo_id && item.quantidade > 0);
        if (!data.fornecedor_id) { alert('Selecione um fornecedor.'); return; }
        if (itensValidos.length === 0) { alert('Adicione pelo menos um item válido.'); return; }
        data.itens = itensValidos;
        data.subtotal = itensValidos.reduce((acc, item) => acc + (item.quantidade * item.preco_unitario), 0);
        data.frete = freteEl.value;
        data.impostos_percentual = impostosEl.value;
        data.valor_total = data.subtotal + parseFloat(data.frete) + (data.subtotal * (parseFloat(data.impostos_percentual)/100));
        try {
            const response = await fetch('/api/ordens-de-compra', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            alert(result.message);
            setupPageMode(); // Limpa o formulário para um novo registro
        } catch (error) { alert(`Erro: ${error.message}`); }
    });
    
    // Chama a configuração da página ao inicializar
    setupPageMode();
}
    
    // --- 10. PÁGINA DE LISTAGEM DE ORDENS DE COMPRA ---
    function initListaComprasPage() {
    const tableBody = document.getElementById('lista-compras-table-body');
    const modal = document.getElementById('modal-registrar-chegada');
    const formChegada = document.getElementById('form-registrar-chegada');
    const dataChegadaInput = document.getElementById('data-chegada-input');
    const ordemIdInput = document.getElementById('ordem-id-chegada');
    const btnExportar = document.getElementById('btn-exportar-ordens');
    const formatarMoeda = (valor) => {
        const numero = valor || 0;
        return numero.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    };
    
    function getStatusClass(status) {
        if (status.includes('Atrasado')) return 'bg-red-100 text-red-800';
        if (status.includes('Recebido no prazo')) return 'bg-green-100 text-green-800';
        if (status.includes('atraso')) return 'bg-yellow-100 text-yellow-800';
        return 'bg-gray-100 text-gray-800';
    }
    if(btnExportar) {
        btnExportar.addEventListener('click', () => {
            window.location.href = '/api/ordens-de-compra/exportar';
        });
    }
    async function loadOrdens() {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Carregando...</td></tr>';
        try {
            const response = await fetch('/api/ordens-de-compra');
            const ordens = await response.json();
            tableBody.innerHTML = '';
            
            if (ordens.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4">Nenhuma ordem de compra registrada.</td></tr>';
                return;
            }

            ordens.forEach(ordem => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="px-6 py-4 text-sm font-medium">
                        <a href="#" class="text-blue-600 hover:underline view-order-btn" data-id="${ordem.id}">
                            ${ordem.numero_ordem}
                        </a>
                    </td>
                    <td class="px-6 py-4 text-sm">${ordem.fornecedor_nome}</td>
                    <td class="px-6 py-4 text-sm">${ordem.data_entrega_prevista}</td>
                    <td class="px-6 py-4 text-sm font-semibold">${formatarMoeda(ordem.valor_total)}</td>
                    <td class="px-6 py-4 text-sm"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusClass(ordem.status)}">${ordem.status}</span></td>
                    <td class="px-6 py-4 text-sm">
                        ${!ordem.data_chegada_real ? `<button class="text-blue-600 hover:underline registrar-chegada-btn" data-id="${ordem.id}">Registrar Chegada</button>` : ''}
                    </td>
                `;
                tableBody.appendChild(tr);
            });

        } catch (error) {
            console.error('Erro:', error);
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-red-500">Erro ao carregar ordens.</td></tr>';
        }
    }
    
    tableBody.addEventListener('click', (e) => {
        // Ação para o botão "Registrar Chegada"
        if (e.target.classList.contains('registrar-chegada-btn')) {
            const id = e.target.dataset.id;
            ordemIdInput.value = id;
            dataChegadaInput.valueAsDate = new Date();
            modal.classList.remove('hidden');
        }
        
        // Ação para o link de visualização da ordem
        if (e.target.classList.contains('view-order-btn')) {
                e.preventDefault();
                const id = e.target.dataset.id;
                showPage('registro-compra', { id: id, mode: 'view' });
            }
    });

    if(modal) modal.addEventListener('click', (e) => {
        if (e.target === modal || e.target.closest('.close-modal-btn')) {
            modal.classList.add('hidden');
        }
    });

    if(formChegada) formChegada.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = ordemIdInput.value;
        const data = { data_chegada: dataChegadaInput.value };

        try {
            const response = await fetch(`/api/ordens-de-compra/${id}/registrar-chegada`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            alert(result.message);
            modal.classList.add('hidden');
            loadOrdens();

        } catch (error) {
            alert(`Erro: ${error.message}`);
        }
    });

    loadOrdens();
}

    // --- 11. PÁGINA DE INVENTÁRIO ---
    function initInventarioPage() {
    console.log("Página de Inventário inicializada.");
    
    const formBusca = document.getElementById('form-busca-item');
    const inputSKU = document.getElementById('busca-sku');
    const inputPosicao = document.getElementById('busca-posicao');
    const btnLimpar = document.getElementById('btn-limpar-busca');
    const containerResultado = document.getElementById('container-resultado');
    const containerHistorico = document.getElementById('container-historico');
    const btnExportar = document.getElementById('btn-exportar-historico');
    
    let itemEncontrado = null;
    
    async function buscarItem(e) {
        if (e) e.preventDefault();
        const sku = inputSKU.value.trim();
        const posicao = inputPosicao.value.trim();
        if (!sku && !posicao) {
            alert('Por favor, informe o SKU ou a Posição para buscar.');
            return;
        }
        try {
            const params = new URLSearchParams({ sku, posicao });
            const response = await fetch(`/api/inventario/buscar?${params.toString()}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            itemEncontrado = data;
            renderizarResultado(itemEncontrado);
        } catch (error) {
            alert(`Erro na busca: ${error.message}`);
            limparResultado();
        }
    }

    function renderizarResultado(item) {
        containerResultado.innerHTML = `
            <h2 class="text-xl font-semibold text-gray-700 mb-4">📦 Item Encontrado</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-y-4 gap-x-6 mb-6 text-sm">
                <div><strong class="block text-gray-500">SKU/Código:</strong><p class="font-semibold text-lg">${item.sku}</p></div>
                <div><strong class="block text-gray-500">Nome do Item:</strong><p class="font-semibold text-lg">${item.nome}</p></div>
                <div><strong class="block text-gray-500">Posição:</strong><p class="font-semibold text-lg">${item.posicao}</p></div>
                <div><strong class="block text-gray-500">Quantidade Atual:</strong><p class="font-bold text-2xl text-blue-600">${item.quantidade_atual} ${item.unidade_medida}</p></div>
            </div>
            <form id="form-ajuste-estoque" class="grid grid-cols-1 md:grid-cols-3 gap-4 items-end border-t pt-4">
                <div>
                    <label for="nova-quantidade" class="block text-sm font-medium text-gray-900"><strong>Nova Quantidade (Contada) *</strong></label>
                    <input type="number" id="nova-quantidade" value="${item.quantidade_atual}" required class="mt-1 w-full border-gray-300 rounded-md shadow-sm text-lg p-2">
                </div>
                <div>
                    <button type="submit" class="w-full bg-red-600 text-white font-bold py-2 px-4 rounded-md hover:bg-red-700">Confirmar Ajuste</button>
                </div>
            </form>`;
        containerResultado.classList.remove('hidden');
        document.getElementById('form-ajuste-estoque').addEventListener('submit', confirmarAjuste);
    }

    function limparResultado() {
        itemEncontrado = null;
        containerResultado.innerHTML = '';
        containerResultado.classList.add('hidden');
    }

    async function confirmarAjuste(e) {
        e.preventDefault();
        const novaQuantidadeInput = document.getElementById('nova-quantidade');
        if (!itemEncontrado || !novaQuantidadeInput) return;
        const payload = {
            estoque_id: itemEncontrado.estoque_id,
            nova_quantidade: novaQuantidadeInput.value
        };
        if (!confirm(`Tem certeza que deseja ajustar o estoque do item ${itemEncontrado.sku} de ${itemEncontrado.quantidade_atual} para ${payload.nova_quantidade}?`)) return;
        
        try {
            const response = await fetch('/api/inventario/ajustar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            alert(data.message);
            limparResultado();
            formBusca.reset();
            carregarHistorico();
        } catch (error) {
            alert(`Erro ao ajustar estoque: ${error.message}`);
        }
    }

    async function carregarHistorico() {
        try {
            const response = await fetch('/api/inventario/historico');
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            if (data.length === 0) {
                containerHistorico.innerHTML = '<p class="text-center text-gray-500 py-4">Nenhum ajuste realizado ainda.</p>';
                return;
            }
            const table = `
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Data</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">SKU</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Posição</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Qtd. Anterior</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Qtd. Nova</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Diferença</th>
                            <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Usuário</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200 text-sm">
                        ${data.map(h => `
                            <tr>
                                <td class="px-4 py-2">${h.data}</td>
                                <td class="px-4 py-2 font-semibold">${h.sku}</td>
                                <td class="px-4 py-2">${h.posicao}</td>
                                <td class="px-4 py-2">${h.qtd_anterior}</td>
                                <td class="px-4 py-2">${h.qtd_nova}</td>
                                <td class="px-4 py-2 font-bold ${h.diferenca > 0 ? 'text-green-600' : 'text-red-600'}">${h.diferenca > 0 ? '+' : ''}${h.diferenca}</td>
                                <td class="px-4 py-2">${h.usuario}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>`;
            containerHistorico.innerHTML = table;
        } catch (error) {
            containerHistorico.innerHTML = `<p class="text-center text-red-500 py-4">Erro ao carregar histórico: ${error.message}</p>`;
        }
    }

    formBusca.addEventListener('submit', buscarItem);
    btnLimpar.addEventListener('click', () => {
        formBusca.reset();
        limparResultado();
    });

    btnExportar.addEventListener('click', () => {
        window.location.href = '/api/inventario/historico/exportar';
    });

    carregarHistorico();
}

    // --- INICIALIZAÇÃO ---
    showPage('dashboard');
});