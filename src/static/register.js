document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registration-form');

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
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';

        // Usamos FormData para enviar texto e arquivos juntos
        const formData = new FormData();

        // 1. Dados de Identificação
        formData.append('legal_name', document.getElementById('legal-name').value);
        formData.append('trade_name', document.getElementById('trade-name').value);
        formData.append('street', document.getElementById('street').value);
        formData.append('number', document.getElementById('number').value);
        formData.append('city', document.getElementById('city').value);
        formData.append('state_province', document.getElementById('state-province').value);
        formData.append('postal_code', document.getElementById('postal-code').value);
        formData.append('country', document.getElementById('country').value);
        formData.append('phone', document.getElementById('phone').value);
        formData.append('email', document.getElementById('email').value);
        formData.append('website', document.getElementById('website').value);

        // 2. Informações Fiscais
        formData.append('tax_id', document.getElementById('tax-id').value);
        formData.append('registration_number', document.getElementById('registration-number').value);
        formData.append('legal_representative', document.getElementById('legal-representative').value);

        // 3. Contato Principal
        formData.append('primary_contact_name', document.getElementById('primary-contact-name').value);
        formData.append('primary_contact_email', document.getElementById('primary-contact-email').value);
        formData.append('primary_contact_phone', document.getElementById('primary-contact-phone').value);

        // 4. Arquivos
        const incorporationFile = document.getElementById('incorporation-file').files[0];
        const addressProofFile = document.getElementById('address-proof-file').files[0];
        const taxIdFile = document.getElementById('tax-id-file').files[0];

        if (incorporationFile) formData.append('incorporation_file', incorporationFile);
        if (addressProofFile) formData.append('address_proof_file', addressProofFile);
        if (taxIdFile) formData.append('tax_id_file', taxIdFile);

        try {
            const response = await fetch('/api/clients/register', {
                method: 'POST',
                body: formData,
                // NÃO defina 'Content-Type', o navegador faz isso por você com FormData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Ocorreu um erro no servidor.');
            }

            alert('Cadastro enviado com sucesso! Entraremos em contato em breve.');
            window.location.href = '/'; // Redireciona para a página inicial

        } catch (error) {
            console.error('Erro ao enviar cadastro:', error);
            alert(`Falha no envio do cadastro: ${error.message}`);
            submitButton.disabled = false;
            submitButton.textContent = 'Enviar Cadastro para Análise';
        }
    });
});