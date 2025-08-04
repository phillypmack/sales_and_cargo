document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('profile-form');
    const loadingDiv = document.getElementById('profile-loading');
    const contentDiv = document.getElementById('profile-content');
    const authToken = localStorage.getItem('vasap_auth_token');

    if (!authToken) {
        alert('Você precisa estar logado para acessar esta página.');
        window.location.href = '/';
        return;
    }

    // Função para preencher o formulário com dados existentes
    const populateForm = (data) => {
        if (!data) return;
        document.getElementById('legal-name').value = data.legal_name || '';
        document.getElementById('trade-name').value = data.trade_name || '';
        if (data.address) {
            document.getElementById('street').value = data.address.street || '';
            document.getElementById('number').value = data.address.number || '';
            document.getElementById('city').value = data.address.city || '';
            document.getElementById('state-province').value = data.address.state_province || '';
            document.getElementById('postal-code').value = data.address.postal_code || '';
            document.getElementById('country').value = data.address.country || '';
        }
        if (data.contact) {
            document.getElementById('phone').value = data.contact.phone || '';
            document.getElementById('email').value = data.contact.email || '';
            document.getElementById('website').value = data.contact.website || '';
        }
        if (data.fiscal_info) {
            document.getElementById('tax-id').value = data.fiscal_info.tax_id || '';
            document.getElementById('registration-number').value = data.fiscal_info.registration_number || '';
            document.getElementById('legal-representative').value = data.fiscal_info.legal_representative || '';
        }
        if (data.documents) {
            const createFileLink = (docKey, linkContainerId) => {
                if (data.documents[docKey]) {
                    const container = document.getElementById(linkContainerId);
                    container.innerHTML = `<a href="${data.documents[docKey]}" target="_blank" class="small">Ver documento enviado</a>`;
                }
            };
            createFileLink('incorporation_file', 'incorporation-file-link');
            createFileLink('address_proof_file', 'address-proof-file-link');
            createFileLink('tax_id_file', 'tax-id-file-link');
        }
    };

    // Carrega os dados do cliente ao entrar na página
    const loadClientData = async () => {
        try {
            const response = await fetch('/api/clients/profile', {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (response.status === 404) {
                // Cliente ainda não tem cadastro, apenas mostra o formulário
                console.log('Nenhum perfil de cliente encontrado. Exibindo formulário em branco.');
            } else if (response.ok) {
                const result = await response.json();
                populateForm(result.client);
            } else {
                throw new Error('Falha ao carregar dados do perfil.');
            }
        } catch (error) {
            console.error(error);
            alert(error.message);
        } finally {
            loadingDiv.classList.add('d-none');
            contentDiv.classList.remove('d-none');
        }
    };

    loadClientData();

    // Lida com o envio do formulário
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!form.checkValidity()) {
            event.stopPropagation();
            form.classList.add('was-validated');
            alert('Por favor, preencha todos os campos obrigatórios.');
            return;
        }

        const submitButton = form.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';

        const formData = new FormData();
        // Adiciona todos os campos de texto
        formData.append('legal_name', document.getElementById('legal-name').value);
        // ... (adicione todos os outros campos de texto como no register.js)
        formData.append('trade_name', document.getElementById('trade-name').value);
        formData.append('address', document.getElementById('address').value);
        formData.append('city', document.getElementById('city').value);
        formData.append('state_province', document.getElementById('state-province').value);
        formData.append('postal_code', document.getElementById('postal-code').value);
        formData.append('country', document.getElementById('country').value);
        formData.append('phone', document.getElementById('phone').value);
        formData.append('email', document.getElementById('email').value);
        formData.append('website', document.getElementById('website').value);
        formData.append('tax_id', document.getElementById('tax-id').value);
        formData.append('registration_number', document.getElementById('registration-number').value);
        formData.append('legal_representative', document.getElementById('legal-representative').value);

        // Adiciona arquivos apenas se eles foram selecionados
        const incorporationFile = document.getElementById('incorporation-file').files[0];
        const addressProofFile = document.getElementById('address-proof-file').files[0];
        const taxIdFile = document.getElementById('tax-id-file').files[0];
        if (incorporationFile) formData.append('incorporation_file', incorporationFile);
        if (addressProofFile) formData.append('address_proof_file', addressProofFile);
        if (taxIdFile) formData.append('tax_id_file', taxIdFile);

        try {
            const response = await fetch('/api/clients/profile', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData,
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            alert('Perfil salvo com sucesso!');
            window.location.reload(); // Recarrega para mostrar os links atualizados
        } catch (error) {
            alert(`Erro ao salvar perfil: ${error.message}`);
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Salvar Informações';
        }
    });
});