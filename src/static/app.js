// =================================================================
// Variáveis Globais e Estado da Aplicação
// =================================================================
let currentTab = 'items';
let currentView = 'grid'; // 'grid' ou 'table'
let items = [];
let cart = [];
let orders = [];
let cargo = [];
let currentUser = null;
let authToken = localStorage.getItem('vasap_auth_token');

// Variáveis de paginação e filtros
let currentPage = 1;
let totalPages = 1;
let currentFilters = {};
let categories = [];
let colors = [];

// =================================================================
// Inicialização da Aplicação
// =================================================================
document.addEventListener('DOMContentLoaded', function() {
    // --- 1. Lógica Comum a Todas as Páginas ---
    checkAuthStatus();

    // --- 2. Lógica Específica da Página ---

    // Se encontrarmos o container da GRADE de itens, estamos na página da loja.
    if (document.getElementById('items-grid-container')) { // <-- CORREÇÃO APLICADA AQUI
        console.log("Executando inicialização da Loja...");
        loadCategories();
        loadItems(); // Agora esta função será chamada corretamente
        loadCart();
        loadOrders();
        loadCargo();
    } 
    // Se encontrarmos a navegação em abas do admin, estamos na página de admin.
    else if (document.getElementById('adminTab')) {
    console.log("Executando inicialização da Página de Admin...");
    loadClientsForDropdown(); 
} 
});

// =================================================================
// Funções de Autenticação
// =================================================================
function checkAuthStatus() {
    if (authToken) {
        fetch('/api/auth/verify', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                currentUser = data.user;
                updateAuthUI(true);
            } else {
                logout();
            }
        })
        .catch(() => logout());
    } else {
        updateAuthUI(false);
    }
}

function updateAuthUI(isLoggedIn) {
    // Elementos da página principal (index.html)
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const userInfo = document.getElementById('user-info');
    const adminNavLink = document.getElementById('admin-nav-link');
    const profileLink = document.getElementById('profile-link');

    if (isLoggedIn && currentUser) {
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';
        if (userInfo) {
            userInfo.style.display = 'inline-block';
            userInfo.textContent = `Olá, ${currentUser.email}`;
        }
        if (adminNavLink) {
            adminNavLink.style.display = currentUser.is_admin ? 'block' : 'none';
            
        }
        if (profileLink) profileLink.style.display = 'inline-block';
    } else {
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (logoutBtn) logoutBtn.style.display = 'none';
        if (userInfo) userInfo.style.display = 'none';
        if (adminNavLink) {
            adminNavLink.style.display = 'none';
        }
        if (profileLink) profileLink.style.display = 'none';
    }
}

function goToAdminPage() {
    // Verifica se o usuário é um admin e se o token existe
    if (currentUser && currentUser.is_admin && authToken) {
        // Se tudo estiver OK, redireciona para a página de admin
        window.location.href = '/admin';
    } else {
        // Se não, mostra um erro ou pede para fazer login
        showAlert('Acesso negado. Você precisa ser um administrador.', 'danger');
        // Opcional: se o usuário não estiver logado, pode mostrar o modal de login
        if (!currentUser) {
            showLogin();
        }
    }
}

function showLogin() {
    document.getElementById('authModalTitle').textContent = 'Login';
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
    new bootstrap.Modal(document.getElementById('authModal')).show();
}

function showRegisterForm() {
    document.getElementById('authModalTitle').textContent = 'Cadastro';
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('register-form').style.display = 'block';
}

function showLoginForm() {
    document.getElementById('authModalTitle').textContent = 'Login';
    document.getElementById('login-form').style.display = 'block';
    document.getElementById('register-form').style.display = 'none';
}

function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('vasap_auth_token', authToken);
            updateAuthUI(true);
            bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
            showAlert('Login realizado com sucesso!', 'success');
            
            // Recarrega TODOS os dados que dependem do estado de login
            loadCart();
            loadOrders();
            loadItems(); // <-- LINHA ADICIONADA: Recarrega a lista de produtos com os preços do usuário
        }
    })
    .catch(() => showAlert('Erro de conexão', 'danger'));
}

function handleRegister(event) {
    event.preventDefault();
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    
    fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('vasap_auth_token', authToken);
            updateAuthUI(true);
            bootstrap.Modal.getInstance(document.getElementById('authModal')).hide();
            showAlert('Cadastro realizado com sucesso!', 'success');
        } else {
            showAlert(data.error || 'Erro no cadastro', 'danger');
        }
    })
    .catch(() => showAlert('Erro de conexão', 'danger'));
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('vasap_auth_token');
    updateAuthUI(false);
    
    // Limpa dados sensíveis do usuário
    cart = [];
    orders = [];
    displayCart();
    displayOrders();
    updateCartCount();
    
    showAlert('Logout realizado com sucesso!', 'info');
    
    // Recarrega a lista de produtos para mostrar os preços padrão
    loadItems(); // <-- LINHA ADICIONADA
}

// =================================================================
// Funções de Carregamento de Dados (API Calls)
// =================================================================

function loadItems(page = 1) {
    currentPage = page;
    const params = new URLSearchParams({ page: page, per_page: 20, ...currentFilters });
    
    // Prepara os cabeçalhos da requisição
    const headers = {
        'Content-Type': 'application/json'
    };
    // Adiciona o token de autenticação SE ele existir
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    fetch(`/api/items/?${params}`, { headers: headers }) // <-- ADICIONA OS CABEÇALHOS AQUI
        .then(response => response.json())
        .then(data => {
            items = data.items || [];
            totalPages = data.pagination ? data.pagination.total_pages : 1;
            displayItems();
            if (data.pagination) updatePagination(data.pagination);
        })
        .catch(error => {
            console.error('Erro ao carregar itens:', error);
            showAlert('Erro ao carregar produtos', 'danger');
        });
}

function loadCart() {
    if (!authToken) {
        cart = [];
        displayCart();
        updateCartCount();
        return;
    }
    fetch("/api/cart/", {
        headers: { "Authorization": `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(data => {
        cart = data;
        displayCart();
        updateCartCount();
        loadCartTotals();
    })
    .catch(error => console.error('Erro ao carregar carrinho:', error));
}

function loadCartTotals() {
    if (!authToken) return;
    fetch(`/api/cart/totals`, {
        headers: { "Authorization": `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(data => displayCartTotals(data))
    .catch(error => console.error('Erro ao carregar totais do carrinho:', error));
}

function loadOrders() {
    if (!authToken) return;
    fetch("/api/pedidos/", {
        headers: { "Authorization": `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(data => {
        orders = data;
        displayOrders();
    })
    .catch(error => console.error('Erro ao carregar pedidos:', error));
}

function loadCargo() {
    fetch('/api/cargo/')
        .then(response => response.json())
        .then(data => {
            cargo = data;
            displayCargo();
        })
        .catch(error => console.error('Erro ao carregar cargo:', error));
}

function loadCategories() {
    fetch('/api/items/categories')
        .then(response => response.json())
        .then(data => {
            categories = data;
            populateCategoryFilter();
        });
}



// =================================================================
// Funções de Ação (Carrinho, Pedidos, etc.)
// =================================================================

function addToCart(itemId, quantity = 1) {
    if (!authToken) {
        showAlert("Por favor, faça login para adicionar itens ao carrinho.", "warning");
        showLogin();
        return;
    }
    if (quantity <= 0) {
        showAlert("Por favor, insira uma quantidade válida.", "warning");
        return;
    }
    fetch('/api/cart/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ item_id: itemId, amount: quantity })
    })
    .then(response => {
        if (!response.ok) throw new Error('Erro ao adicionar ao carrinho');
        return response.json();
    })
    .then(() => {
        showAlert(`Item adicionado com sucesso!`, 'success');
        loadCart(); // Recarrega o carrinho para atualizar a UI
    })
    .catch(error => {
        console.error("Erro ao adicionar ao carrinho:", error);
        showAlert('Erro ao adicionar item ao carrinho.', 'danger');
    });
}

function addTableItemToCart(itemId) {
    const quantityInput = document.getElementById(`quantity-${itemId}`);
    const quantity = parseInt(quantityInput.value) || 1;
    addToCart(itemId, quantity);
    quantityInput.value = ''; // Limpa o campo
}

function removeFromCart(inventoryId) {
    fetch(`/api/cart/${inventoryId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(() => {
        showAlert('Item removido do carrinho!', 'info');
        loadCart();
    })
    .catch(() => showAlert('Erro ao remover item.', 'danger'));
}

function updateCartItem(inventoryId, newAmount) {
    if (newAmount < 1) {
        removeFromCart(inventoryId);
        return;
    }
    fetch(`/api/cart/${inventoryId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ amount: parseInt(newAmount) })
    })
    .then(response => response.json())
    .then(() => loadCart()) // Recarrega tudo para manter a consistência
    .catch(() => showAlert('Erro ao atualizar quantidade.', 'danger'));
}

function clearCart() {
    if (!confirm('Tem certeza que deseja limpar todo o carrinho?')) return;
    fetch(`/api/cart/clear`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(data => {
        showAlert(data.message, 'success');
        loadCart();
    })
    .catch(() => showAlert('Erro ao limpar carrinho.', 'danger'));
}

function placeOrder() {
    if (!authToken) {
        showAlert("Por favor, faça login para finalizar o pedido.", "warning");
        return;
    }
    fetch("/api/cart/place-order", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${authToken}`
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.message && data.message.includes('empty')) {
            showAlert('Seu carrinho está vazio.', 'warning');
        } else {
            showAlert('Pedido realizado com sucesso!', 'success');
            loadCart();
            loadOrders();
            showTab('orders');
        }
    })
    .catch(() => showAlert('Erro ao finalizar pedido.', 'danger'));
}

// =================================================================
// Funções de Exibição e UI (Renderização)
// =================================================================

function setView(viewName) {
    if (viewName === currentView) return;
    currentView = viewName;

    const gridContainer = document.getElementById('items-grid-container');
    const tableContainer = document.getElementById('items-table-container');
    const gridBtn = document.getElementById('grid-view-btn');
    const tableBtn = document.getElementById('table-view-btn');

    if (viewName === 'grid') {
        gridContainer.style.display = 'flex';
        tableContainer.style.display = 'none';
        gridBtn.classList.add('active');
        tableBtn.classList.remove('active');
    } else {
        gridContainer.style.display = 'none';
        tableContainer.style.display = 'block';
        gridBtn.classList.remove('active');
        tableBtn.classList.add('active');
    }
    displayItems();
}

function displayItems() {
    if (currentView === 'grid') {
        displayItemsAsGrid();
    } else {
        displayItemsAsTable();
    }
}

function displayItemsAsGrid() {
    const container = document.getElementById('items-grid-container');
    if (!container) return;
    
    if (items.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-info">Nenhum produto encontrado.</div></div>';
        return;
    }
    
    container.innerHTML = items.map(item => {
        const imageUrl = item.main_photo_url || 'no-image.png';

        // --- INÍCIO DA LÓGICA ADICIONADA ---
        // Define o passo do incremento. Se Group Pile for 0 ou inválido, o passo é 1.
        const groupPile = item['Group Pile'] > 0 ? item['Group Pile'] : 1;
        // Cria um placeholder dinâmico para informar o usuário sobre o múltiplo.
        const placeholderText = groupPile > 1 ? `Qtd (${groupPile})` : 'Qtd';
        // --- FIM DA LÓGICA ADICIONADA ---

        let dimensionsText = '';
        if (item.Height > 0 && item.Width > 0 && item.Length > 0) {
            dimensionsText = `<p class="card-text small text-muted mb-2">Dim: ${item.Height} x ${item.Width} x ${item.Length} cm</p>`;
        }

        return `
        <div class="col">
            <div class="card h-100">
                <img src="${imageUrl}" class="card-img-top" alt="${item.Name}" style="height: 200px; object-fit: contain; background-color: #f8f9fa; cursor: pointer;" onclick="showImageGallery(${item['Item ID']})">
                <div class="card-body d-flex flex-column">
                    <h6 class="card-title">${item.Name || 'Nome indisponível'}</h6>
                    <p class="card-text text-muted small">${item.Category || 'Categoria'}</p>
                    <p class="card-text small text-secondary">Ref: ${item['Item ID']}</p>
                    ${dimensionsText}
                    ${item.has_special_price
                        ? `<p class="card-text text-success fw-bold mt-auto">$${(item['Sale Price'] || 0).toFixed(2)} <small class="text-muted text-decoration-line-through">$${(item.original_price || 0).toFixed(2)}</small></p>`
                        : `<p class="card-text text-success fw-bold mt-auto">$${(item['Sale Price'] || 0).toFixed(2)}</p>`
                    }
                    <p class="card-text small">Disponível: <strong>${item.available_stock || 0}</strong></p>
                    <div class="input-group input-group-sm mt-2">
                        <!-- INPUT MODIFICADO ABAIXO -->
                        <input type="number" class="form-control" placeholder="${placeholderText}" min="1" step="${groupPile}" id="grid-quantity-${item['Item ID']}">
                        <button class="btn btn-primary" type="button" onclick="addGridItemToCart(${item['Item ID']})">
                            <i class="fas fa-cart-plus"></i> Adicionar
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

function setPrimaryPhoto(photoId) {
    if (!confirm('Deseja definir esta imagem como a principal do produto?')) {
        return;
    }

    fetch(`/api/admin/photos/${photoId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ is_primary: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert('Foto principal definida com sucesso!', 'success');
            // Recarrega a lista de fotos para mostrar a mudança (o badge se movendo)
            searchPhotos();
        }
    })
    .catch(error => {
        console.error('Erro ao definir foto principal:', error);
        showAlert('Erro ao definir foto principal.', 'danger');
    });
}

function loadAllItemsTable() {
    const searchTerm = document.getElementById('admin-all-items-search').value;
    let fetchUrl = '/api/admin/all-items';

    if (searchTerm) {
        fetchUrl += `?search=${encodeURIComponent(searchTerm)}`;
    }

    showAlert('Carregando todos os itens...', 'info');

    fetch(fetchUrl, {
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Falha ao carregar os dados.');
        return response.json();
    })
    .then(data => {
        displayAllItemsTable(data);
        showAlert('Tabela carregada com sucesso!', 'success');
    })
    .catch(error => {
        console.error('Erro ao carregar tabela completa:', error);
        showAlert('Erro ao carregar a tabela de itens.', 'danger');
    });
}

function displayAllItemsTable(allItems) {
    const container = document.getElementById('admin-all-items-container');
    if (!container) return;

    if (!allItems || allItems.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">Nenhum item encontrado.</div>';
        return;
    }

    const headers = [
        'Item ID', 'Name', 'Shape', 'Category', 'Sale Price', 'Group Pile', // <-- 'Shape' ADICIONADO
        'Weight', 'Height', 'Width', 'Length', 'Description'
    ];

    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-striped table-bordered table-sm">
                <thead>
                    <tr>
                        ${headers.map(h => `<th>${h}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${allItems
                        // FILTRO ADICIONADO AQUI: Garante que o item existe e tem um ID antes de tentar renderizar a linha
                        .filter(item => item && item['Item ID']) 
                        .map(item => `
                        <tr>
                            ${headers.map(header => `<td>${item[header] || ''}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        <p class="mt-2 text-muted"><small>${allItems.length} itens exibidos.</small></p>
    `;

    container.innerHTML = tableHtml;
}

function displayItemsAsTable() {
    const tableBody = document.getElementById('items-table-body');
    if (!tableBody) return;

    if (items.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Nenhum produto encontrado.</td></tr>';
        return;
    }

    tableBody.innerHTML = items.map(item => {
        const imageUrl = item.main_photo_url || 'no-image.png';
        
        // --- INÍCIO DA LÓGICA ADICIONADA ---
        const groupPile = item['Group Pile'] > 0 ? item['Group Pile'] : 1;
        // Placeholder mais simples para a tabela, para não ocupar muito espaço.
        const placeholderText = groupPile > 1 ? `${groupPile}` : '1';
        // --- FIM DA LÓGICA ADICIONADA ---

        let dimensionsText = '';
        if (item.Height > 0 && item.Width > 0 && item.Length > 0) {
            dimensionsText = `<div class="text-muted small">Dim: ${item.Height} x ${item.Width} x ${item.Length} cm</div>`;
        }

        return `
            <tr>
                <td><img src="${imageUrl}" alt="${item.Name}" class="table-item-img" style="cursor: pointer;" onclick="showImageGallery(${item['Item ID']})"></td>
                <td>
                    <h6 class="mb-0">${item.Name || 'Nome não disponível'}</h6>
                    <small class="text-muted">${item.Category || 'Categoria'}</small>
                    ${dimensionsText}
                </td>
                <td>${item['Item ID']}</td>
                <td>
                    ${item.has_special_price
                        ? `<div>$${(item['Sale Price'] || 0).toFixed(2)}</div><small class="text-muted text-decoration-line-through">$${(item.original_price || 0).toFixed(2)}</small>`
                        : `$${(item['Sale Price'] || 0).toFixed(2)}`
                    }
                </td>
                <td><strong>${item.available_stock || 0}</strong></td>
                <td>
                    <!-- INPUT MODIFICADO ABAIXO -->
                    <input type="number" class="form-control form-control-sm quantity-input" id="quantity-${item['Item ID']}" min="1" step="${groupPile}" placeholder="${placeholderText}">
                </td>
                <td>
                    <button class="btn btn-success btn-sm" onclick="addTableItemToCart(${item['Item ID']})">
                        <i class="fas fa-cart-plus"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function displayCart() {
    const container = document.getElementById('cart-container');
    if (!container) return;
    if (cart.length === 0) {
        container.innerHTML = '<div class="alert alert-info">Seu carrinho está vazio.</div>';
        document.getElementById('cart-totals').innerHTML = ''; // Limpa os totais
        return;
    }
    container.innerHTML = cart.map(item => `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-5">
                        <h6>${item.Name || 'Produto'}</h6>
                        <small class="text-muted">${item.Category || ''}</small>
                    </div>
                    <div class="col-md-3">
                        <div class="input-group input-group-sm">
                            <span class="input-group-text">Qtd:</span>
                            <input type="number" class="form-control" value="${item.Amount}" min="1" onchange="updateCartItem('${item['Inventory ID']}', this.value)">
                        </div>
                    </div>
                    <div class="col-md-2">
                        <strong>$ ${(item['Total price'] || 0).toFixed(2)}</strong>
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-danger btn-sm" onclick="removeFromCart('${item['Inventory ID']}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function displayCartTotals(totals) {
    const totalsContainer = document.getElementById('cart-totals');
    if (!totalsContainer) return;
    totalsContainer.innerHTML = `
        <div class="card">
            <div class="card-header"><h5 class="mb-0">Resumo do Pedido</h5></div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Total de Itens:</strong> ${totals.total_items}</p>
                        <p><strong>Valor Total:</strong> $ ${totals.total_value.toFixed(2)}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Peso Total:</strong> ${totals.total_weight.toFixed(2)} kg</p>
                        <p><strong>Cubagem Total:</strong> ${totals.total_volume.toFixed(6)} m³</p>
                    </div>
                </div>
                <div class="mt-3 d-flex justify-content-between">
                    <button class="btn btn-outline-danger" onclick="clearCart()"><i class="fas fa-trash"></i> Limpar Carrinho</button>
                    <button class="btn btn-success btn-lg" onclick="placeOrder()"><i class="fas fa-check"></i> Finalizar Pedido</button>
                </div>
            </div>
        </div>`;
}

function displayOrders() {
    const container = document.getElementById('orders-container');
    if (!container) return;
    
    if (orders.length === 0) {
        container.innerHTML = '<div class="alert alert-info">Nenhum pedido encontrado.</div>';
        return;
    }
    
    container.innerHTML = orders.map(order => {
        // Lógica para criar o badge de status
        let statusBadge = '';
        if (order.sankhya_integration) {
            if (order.sankhya_integration.status === 'success') {
                const nunota = order.sankhya_integration.nunota;
                statusBadge = `
                    <p><span class="badge bg-success">Sucesso no Envio ao ERP</span></p>
                    ${nunota ? `<p class="small text-muted">Nota ERP: <strong>${nunota}</strong></p>` : ''}
                `;
            } else {
                statusBadge = '<p><span class="badge bg-danger">Falha no Envio ao ERP</span></p>';
            }
        }

        return `
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <strong>Pedido #${order.Order}</strong>
                <small>${new Date(order.Data).toLocaleDateString('pt-BR')}</small>
            </div>
            <div class="card-body">
                <p><strong>Valor Total:</strong> $${(order['Total price'] || 0).toFixed(2)}</p>
                <p><strong>Total de Itens:</strong> ${order['Total Itens']}</p>
                <!-- Badge de status é inserido aqui -->
                ${statusBadge}
            </div>
            <div class="card-footer text-end">
                <button class="btn btn-outline-primary btn-sm me-2" onclick="showOrderDetails('${order._id}')">
                    <i class="fas fa-eye"></i> Detalhes
                </button>
                <button class="btn btn-outline-success btn-sm me-2" onclick="simulateLoading('${order._id}')">
                    <i class="fas fa-cube"></i> Simular Carregamento
                </button>
                <button class="btn btn-primary btn-sm me-2" onclick="formalizeOrder('${order._id}')" ${order.sankhya_integration && order.sankhya_integration.status === 'success' ? 'disabled' : ''}>
                    <i class="fas fa-check"></i> Formalizar Pedido
                </button>
                <button class="btn btn-outline-danger btn-sm" onclick="deleteOrder('${order._id}')">
                    <i class="fas fa-trash-alt"></i> Excluir
                </button>
            </div>
        </div>
    `}).join('');
}

async function formalizeOrder(orderId) {
    // --- INÍCIO DA VERIFICAÇÃO APRIMORADA ---
    try {
        const profileResponse = await fetch('/api/clients/profile', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        // Se o status for 404, significa que o perfil não foi preenchido.
        if (profileResponse.status === 404) {
            alert('Você precisa completar o cadastro da sua empresa antes de formalizar um pedido.');
            window.location.href = '/profile'; // Redireciona para a página de perfil
            return; // Interrompe a execução
        }

        // Se o status não for OK (ex: 401, 500), lança um erro.
        if (!profileResponse.ok) {
            throw new Error('Não foi possível verificar seu perfil de cliente. Tente fazer login novamente.');
        }
        // Se chegou aqui, o perfil existe e a verificação foi bem-sucedida.
    } catch (error) {
        showAlert(error.message, 'danger');
        return; // Interrompe a execução
    }
    // --- FIM DA VERIFICAÇÃO APRIMORADA ---

    if (!confirm("Este pedido será enviado para a Vasap, deseja continuar?")) {
        return;
    }

    showAlert('Enviando pedido para o ERP, por favor aguarde...', 'info');

    fetch(`/api/pedidos/${orderId}/formalize`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // Esta parte permanece a mesma, pois a rota /formalize sempre retorna JSON.
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.error || 'Erro desconhecido no servidor') });
        }
        return response.json();
    })
    .then(data => {
        showAlert(data.message, 'success');
        loadOrders();
    })
    .catch(error => {
        console.error('Erro ao formalizar pedido:', error);
        showAlert(`Falha ao formalizar o pedido: ${error.message}`, 'danger');
    });
}

function simulateLoading(orderId) {
    // 1. Encontra o pedido completo na nossa lista 'orders' usando o _id que recebemos.
    const order = orders.find(o => o._id === orderId);

    // 2. Medida de segurança: se por algum motivo o pedido não for encontrado, exibe um erro.
    if (!order) {
        console.error("Pedido não encontrado para o ID:", orderId);
        showAlert("Não foi possível encontrar os dados do pedido para simular o carregamento.", "danger");
        return;
    }

    // 3. Pega o número do pedido (ex: 1, 2, 3...) do objeto que encontramos.
    const orderNumber = order.Order;

    // 4. Chama a função que já existe e funciona, passando o número do pedido para ela.
    openCargoOptimizerForOrder(orderNumber);
}

function displayCargo() {
    const container = document.getElementById('cargo-container');
    if (!container) return;
    
    if (cargo.length === 0) {
        container.innerHTML = '<div class="alert alert-info">Nenhum pedido ativo para otimização.</div>';
        return;
    }
    
    container.innerHTML = cargo.map(pedido => `
        <div class="card mb-3">
            <div class="card-header">
                <strong>Pedido #${pedido.Order}</strong> - Cliente: ${pedido.Client}
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <p><strong>Data:</strong> ${new Date(pedido.Data).toLocaleDateString('pt-BR')}</p>
                        <p><strong>Total de Itens:</strong> ${pedido['Total Itens']}</p>
                    </div>
                    <div class="col-md-4">
                        <p><strong>Valor Total:</strong> $${(pedido['Total price'] || 0).toFixed(2)}</p>
                        <p><strong>Peso Total:</strong> ${(pedido['Total wheight Kg'] || 0).toFixed(2)} kg</p>
                    </div>
                    <div class="col-md-4 d-flex align-items-center justify-content-end">
                        <button class="btn btn-primary" onclick="openCargoOptimizerForOrder(${pedido.Order})">
                            <i class="fas fa-box-open"></i> Otimizar Este Pedido
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function openCargoOptimizerForOrder(orderNumber) {
    // Abre a página do otimizador em uma nova aba, passando o ID do pedido na URL
    // Ex: /cargo-optimizer?order=123
    const url = `/cargo-optimizer?order=${orderNumber}`;
    window.open(url, '_blank');
}

function updateCartCount() {
    // Atualiza todos os contadores de carrinho na página
    const cartCounters = document.querySelectorAll('#cart-count');
    cartCounters.forEach(counter => {
        if (cart.length > 0) {
            counter.textContent = cart.length;
            counter.style.display = 'block';
        } else {
            counter.style.display = 'none';
        }
    });
}

// =================================================================
// Funções de Filtro e Paginação
// =================================================================

function applyFilters() {
    const filters = {};
    
    // Busca geral
    const search = document.getElementById('search-input')?.value;
    if (search) filters.search = search;
    
    // Categoria (Grupo)
    const category = document.getElementById('category-filter')?.value;
    if (category) filters.category = category;
    
    // Preço
    const minPrice = document.getElementById('min-price')?.value;
    const maxPrice = document.getElementById('max-price')?.value;
    if (minPrice) filters.min_price = minPrice;
    if (maxPrice) filters.max_price = maxPrice;
    
    currentFilters = filters;
    loadItems(1); // Volta para a primeira página
}

function clearFilters() {
    currentFilters = {};
    const form = document.querySelector('.filter-card');
    if (form) form.querySelectorAll('input, select').forEach(el => el.value = '');
    loadItems(1);
}

function populateCategoryFilter() {
    const select = document.getElementById('category-filter');
    if (!select) return;
    select.innerHTML = '<option value="">Todas as categorias</option>';
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
    });
}


function updatePagination(pagination) {
    const container = document.getElementById('pagination-container');
    if (!container) return;
    let html = '<nav><ul class="pagination justify-content-center">';
    if (pagination.has_prev) html += `<li class="page-item"><a class="page-link" href="#" onclick="event.preventDefault(); loadItems(${pagination.page - 1})">Anterior</a></li>`;
    else html += '<li class="page-item disabled"><span class="page-link">Anterior</span></li>';
    
    // Lógica simplificada de números de página
    for (let i = Math.max(1, pagination.page - 2); i <= Math.min(pagination.total_pages, pagination.page + 2); i++) {
        if (i === pagination.page) html += `<li class="page-item active"><span class="page-link">${i}</span></li>`;
        else html += `<li class="page-item"><a class="page-link" href="#" onclick="event.preventDefault(); loadItems(${i})">${i}</a></li>`;
    }

    if (pagination.has_next) html += `<li class="page-item"><a class="page-link" href="#" onclick="event.preventDefault(); loadItems(${pagination.page + 1})">Próximo</a></li>`;
    else html += '<li class="page-item disabled"><span class="page-link">Próximo</span></li>';
    html += '</ul></nav>';
    container.innerHTML = html;
}

// =================================================================
// Funções de Navegação e Utilitários
// =================================================================

function showTab(tabName) {
    currentTab = tabName;
    document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
    document.querySelectorAll('.bottom-nav .nav-link').forEach(link => link.classList.remove('active'));
    
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) selectedTab.style.display = 'block';
    
    const selectedLink = document.querySelector(`.bottom-nav [onclick="showTab('${tabName}')"]`);
    if (selectedLink) selectedLink.classList.add('active');
    
    // Recarrega dados da aba se necessário
    if (tabName === 'cart') loadCart();
    if (tabName === 'orders') loadOrders();
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(alertDiv);
    setTimeout(() => alertDiv.remove(), 5000);
}

// =================================================================
// Funções de Administração (sem alterações significativas)
// =================================================================
function toggleAdminPanel() {
    const panel = document.querySelector('.admin-panel');
    if (panel.style.display === 'none' || !panel.style.display) {
        panel.style.display = 'block';
        loadAdminStats();
    } else {
        panel.style.display = 'none';
    }
}

function loadAdminStats() {
    fetch('/api/admin/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-products').textContent = data.total_products;
            document.getElementById('low-stock-items').textContent = data.low_stock_items;
            document.getElementById('total-inventory-value').textContent = `$ ${data.total_inventory_value.toFixed(2)}`;
        })
        .catch(error => console.error('Erro ao carregar estatísticas:', error));
}

function registerProduct() {
    const formData = {
        name: document.getElementById('product-name').value,
        shape: document.querySelector('input[name="item-shape"]:checked').value, // <-- LINHA ADICIONADA
        category: document.getElementById('product-category').value,
        sale_price: parseFloat(document.getElementById('product-price').value),
        stock: parseInt(document.getElementById('product-stock').value)
        // Adicione outros campos se necessário
    };
    fetch('/api/admin/products', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) showAlert(data.error, 'danger');
        else {
            showAlert('Produto cadastrado com sucesso!', 'success');
            document.getElementById('individual-product-form').reset();
            loadItems();
            loadAdminStats();
        }
    })
    .catch(() => showAlert('Erro ao cadastrar produto.', 'danger'));
}

function searchPhotos() {
    const itemId = document.getElementById('photo-search-id').value;
    if (!itemId) {
        showAlert('Por favor, digite o ID do produto', 'warning');
        return;
    }
    fetch(`/api/admin/photos/${itemId}`, { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(response => response.json())
        .then(data => displayProductPhotos(data))
        .catch(() => showAlert('Erro ao buscar fotos.', 'danger'));
}

function displayProductPhotos(photos) {
    const container = document.getElementById('product-photos-list');
    if (!photos || photos.length === 0) {
        container.innerHTML = '<div class="alert alert-info">Nenhuma foto encontrada para este produto</div>';
        return;
    }
    
    container.innerHTML = photos.map(photo => `
        <div class="card mb-2">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-2">
                        <img src="${photo['Photo URL']}" class="img-thumbnail" style="max-width: 80px;">
                    </div>
                    <div class="col-md-6">
                        <p class="mb-1">${photo.Description || 'Sem descrição'}</p>
                        <small class="text-muted">
                            ${photo['Is Primary'] ? '<span class="badge bg-primary">Principal</span>' : ''}
                        </small>
                    </div>
                    <div class="col-md-4">
                        <!-- Botão "Tornar Principal" só aparece se a foto NÃO for a principal -->
                        ${!photo['Is Primary'] ? 
                            `<button class="btn btn-sm btn-outline-success me-1" onclick="setPrimaryPhoto('${photo._id}')">
                                <i class="fas fa-star"></i> Tornar Principal
                             </button>` : ''
                        }
                        <button class="btn btn-sm btn-outline-danger" onclick="deletePhoto('${photo._id}')">
                            <i class="fas fa-trash"></i> Excluir
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function cleanupBrokenPhotos() {
    const confirmation = prompt("Esta ação verificará TODAS as fotos no banco de dados e removerá permanentemente aquelas com links inválidos. Isso pode levar alguns minutos e não pode ser desfeito. Digite 'LIMPAR' para confirmar.");

    if (confirmation !== 'LIMPAR') {
        showAlert('Ação de limpeza cancelada.', 'info');
        return;
    }

    showAlert('Iniciando verificação de links... Por favor, aguarde.', 'info');

    fetch('/api/admin/photos/cleanup', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('A resposta do servidor não foi OK');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) {
            showAlert(`Erro: ${data.error}`, 'danger');
        } else {
            showAlert(data.message, 'success');
        }
    })
    .catch(error => {
        console.error('Erro ao executar a limpeza de fotos:', error);
        showAlert('Ocorreu um erro de comunicação durante a limpeza.', 'danger');
    });
}

function deletePhoto(photoId) {
    if (!confirm('Tem certeza que deseja excluir esta foto?')) return;
    fetch(`/api/admin/photos/${photoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) showAlert(data.error, 'danger');
        else {
            showAlert('Foto excluída com sucesso!', 'success');
            searchPhotos(); // Recarrega a lista
        }
    })
    .catch(() => showAlert('Erro ao excluir foto.', 'danger'));
}


function showOrderDetails(orderId) {
    // Encontra o pedido na lista já carregada
    const order = orders.find(o => o._id === orderId);
    if (!order || !order.items) {
        showAlert('Detalhes do pedido não encontrados ou pedido antigo sem itens salvos.', 'warning');
        return;
    }

    const modalTitle = document.getElementById('orderDetailsModalTitle');
    const modalBody = document.getElementById('orderDetailsModalBody');

    modalTitle.textContent = `Detalhes do Pedido #${order.Order}`;

    let itemsHtml = `
        <p><strong>Data:</strong> ${new Date(order.Data).toLocaleString('pt-BR')}</p>
        <table class="table">
            <thead>
                <tr>
                    <th>Produto</th>
                    <th>Preço Unit.</th>
                    <th>Qtd.</th>
                    <th>Subtotal</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    order.items.forEach(item => {
        itemsHtml += `
            <tr>
                <td>${item.Name || 'Produto'}</td>
                <td>$ ${(item['Sale Price'] || 0).toFixed(2)}</td>
                <td>${item.Amount}</td>
                <td>$ ${(item['Total price'] || 0).toFixed(2)}</td>
            </tr>
        `;
    });

    itemsHtml += `
            </tbody>
        </table>
        <hr>
        <div class="text-end">
            <p><strong>Peso Total:</strong> ${(order['Total wheight Kg'] || 0).toFixed(2)} kg</p>
            <p><strong>Valor Total do Pedido:</strong> <span class="fs-5 fw-bold">$ ${(order['Total price'] || 0).toFixed(2)}</span></p>
        </div>
    `;

    modalBody.innerHTML = itemsHtml;

    new bootstrap.Modal(document.getElementById('orderDetailsModal')).show();
}

function deleteOrder(orderId) {
    if (!confirm('Tem certeza que deseja excluir este pedido? Ele não poderá ser recuperado.')) {
        return;
    }

    fetch(`/api/pedidos/${orderId}/delete`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Falha ao excluir pedido');
        }
        return response.json();
    })
    .then(data => {
        showAlert(data.message, 'success');
        loadOrders(); // Recarrega a lista de pedidos, o item excluído não aparecerá mais
    })
    .catch(error => {
        console.error('Erro ao excluir pedido:', error);
        showAlert('Erro ao excluir pedido.', 'danger');
    });
}

// Funções para o Painel de Admin
function loadAdminOrders() {
    fetch('/api/admin/orders', {
        headers: { 'Authorization': `Bearer ${authToken}` } // Se a rota admin for protegida
    })
    .then(response => response.json())
    .then(data => {
        displayAdminOrders(data);
    })
    .catch(error => {
        console.error('Erro ao carregar pedidos do admin:', error);
        showAlert('Erro ao carregar pedidos do admin.', 'danger');
    });
}

function addGridItemToCart(itemId) {
    // Usa um ID único para o campo de quantidade da grade para evitar conflitos
    const quantityInput = document.getElementById(`grid-quantity-${itemId}`);
    const quantity = parseInt(quantityInput.value) || 1; // Pega o valor ou assume 1 se estiver vazio

    addToCart(itemId, quantity);
    
    // Opcional: Limpa o campo de quantidade após adicionar
    quantityInput.value = '';
}

function showImageGallery(itemId) {
    fetch(`/api/items/${itemId}/photos`)
        .then(response => response.json())
        .then(photos => {
            if (!photos || photos.length === 0) {
                showAlert('Nenhuma foto adicional encontrada para este produto.', 'info');
                return;
            }

            const indicatorsContainer = document.getElementById('carousel-indicators-container');
            const innerContainer = document.getElementById('carousel-inner-container');

            // Limpa o conteúdo anterior
            indicatorsContainer.innerHTML = '';
            innerContainer.innerHTML = '';

            // Cria os indicadores e os slides do carrossel
            photos.forEach((photo, index) => {
                const isActive = index === 0 ? 'active' : '';

                // Adiciona o indicador (bolinha)
                indicatorsContainer.innerHTML += `
                    <button type="button" data-bs-target="#imageCarousel" data-bs-slide-to="${index}" class="${isActive}" aria-current="${isActive ? 'true' : 'false'}" aria-label="Slide ${index + 1}"></button>
                `;

                // Adiciona a imagem ao slide
                innerContainer.innerHTML += `
                    <div class="carousel-item ${isActive}">
                        <img src="${photo['Photo URL']}" class="d-block w-100" alt="${photo.Description || 'Foto do produto'}">
                        ${photo.Description ? `<div class="carousel-caption d-none d-md-block"><p>${photo.Description}</p></div>` : ''}
                    </div>
                `;
            });

            // Mostra o modal
            const galleryModal = new bootstrap.Modal(document.getElementById('imageGalleryModal'));
            galleryModal.show();
        })
        .catch(error => {
            console.error('Erro ao buscar fotos da galeria:', error);
            showAlert('Não foi possível carregar a galeria de fotos.', 'danger');
        });
}

function displayAdminOrders(allOrders) {
    const container = document.getElementById('admin-orders-list');
    if (!container) return;

    if (!allOrders || allOrders.length === 0) {
        container.innerHTML = '<div class="alert alert-info mt-3">Nenhum pedido no sistema.</div>';
        return;
    }

    container.innerHTML = `
        <table class="table table-sm table-striped mt-3">
            <thead>
                <tr>
                    <th># Pedido</th>
                    <th>Data</th>
                    <th>Cliente (ID)</th>
                    <th>Valor</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${allOrders.map(order => `
                    <tr>
                        <td>${order.Order}</td>
                        <td>${new Date(order.Data).toLocaleDateString('pt-BR')}</td>
                        <td>${order.Client}</td>
                        <td>$ ${(order['Total price'] || 0).toFixed(2)}</td>
                        <td>
                            ${(order.deleted_by_users && order.deleted_by_users.length > 0)
                                ? '<span class="badge bg-secondary">Oculto para usuário</span>'
                                : '<span class="badge bg-success">Ativo</span>'
                            }
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}
function loadClientsForDropdown() {
    fetch('/api/admin/clients', { headers: { 'Authorization': `Bearer ${authToken}` } })
        .then(response => response.json())
        .then(clients => {
            const select = document.getElementById('client-select');
            if (!select) return;
            select.innerHTML = '<option selected disabled>Selecione um cliente</option>';
            clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client._id;
                option.textContent = `${client.name} (${client.email})`;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Erro ao carregar clientes:', error));
}

function adjustClientPrices() {
    const clientId = document.getElementById('client-select').value;
    const type = document.getElementById('client-price-adjustment-type').value;
    const value = document.getElementById('client-price-adjustment-value').value;

    if (!clientId || !value) {
        showAlert('Por favor, selecione um cliente e insira um valor de ajuste.', 'warning');
        return;
    }

    if (!confirm(`Confirma o ajuste de preço para o cliente selecionado? Esta ação sobrescreverá quaisquer preços especiais existentes para este cliente.`)) {
        return;
    }

    fetch('/api/admin/adjust-client-prices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
        body: JSON.stringify({ client_id: clientId, type, value })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) showAlert(data.error, 'danger');
        else showAlert(data.message, 'success');
    })
    .catch(error => showAlert('Erro ao aplicar ajuste de preço.', 'danger'));
}

function importItems() {
    const fileInput = document.getElementById('import-file-input');
    const file = fileInput.files[0];

    if (!file) {
        showAlert('Por favor, selecione um arquivo para importar.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    showAlert('Enviando arquivo... O processo pode levar alguns instantes.', 'info');

    fetch('/api/admin/import-items', {
        method: 'POST',
        headers: {
            // NÃO defina 'Content-Type', o navegador fará isso por você com FormData
            'Authorization': `Bearer ${authToken}`
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(`Erro na importação: ${data.error}`, 'danger');
        } else {
            showAlert(`${data.message} (Atualizados: ${data.updated_count}, Criados: ${data.created_count})`, 'success');
            // Recarrega a tabela para mostrar os novos dados
            loadAllItemsTable();
        }
    })
    .catch(error => {
        console.error('Erro na importação:', error);
        showAlert('Ocorreu um erro de comunicação durante a importação.', 'danger');
    });
}

function exportItems() {
    showAlert('Preparando seu arquivo para download...', 'info');

    fetch('/api/admin/export-items', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${authToken}`
        }
    })
    .then(response => {
        // Verifica se a resposta foi bem-sucedida
        if (!response.ok) {
            // Se não foi, tenta ler o erro como JSON
            return response.json().then(err => { throw new Error(err.error || 'Erro no servidor') });
        }
        // Se foi bem-sucedida, pega o nome do arquivo do cabeçalho
        const header = response.headers.get('Content-Disposition');
        const parts = header.split(';');
        const filename = parts[1].split('=')[1].replace(/"/g, ''); // Extrai o nome do arquivo
        
        // Retorna o arquivo como um "blob" (Binary Large Object)
        return response.blob().then(blob => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
        // Cria uma URL temporária para o arquivo em memória
        const url = window.URL.createObjectURL(blob);
        
        // Cria um link <a> invisível
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename; // Define o nome do arquivo para o download
        
        // Adiciona o link ao corpo do documento e o clica programaticamente
        document.body.appendChild(a);
        a.click();
        
        // Limpa a URL temporária e remove o link
        window.URL.revokeObjectURL(url);
        a.remove();
        
        showAlert('Download iniciado!', 'success');
    })
    .catch(error => {
        console.error('Erro ao exportar:', error);
        showAlert(`Falha na exportação: ${error.message}`, 'danger');
    });
}


// Adicione outras funções de admin aqui conforme necessário...