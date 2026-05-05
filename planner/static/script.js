let currentFilterType = 'current-month';
let currentFilterValue = '';
let currentEvents = [];
let employeesList = [];

let modalEvent, modalEmployees, modalEmployeeEdit, importModal, importEmployeesModal, importUsersModal, usersModal, userEditModal;

document.addEventListener('DOMContentLoaded', async () => {
    modalEvent = new bootstrap.Modal(document.getElementById('eventModal'));
    modalEmployees = new bootstrap.Modal(document.getElementById('employeesModal'));
    modalEmployeeEdit = new bootstrap.Modal(document.getElementById('employeeEditModal'));
    importModal = new bootstrap.Modal(document.getElementById('importModal'));
    if (document.getElementById('importEmployeesModal')) {
        importEmployeesModal = new bootstrap.Modal(document.getElementById('importEmployeesModal'));
        importUsersModal = new bootstrap.Modal(document.getElementById('importUsersModal'));
        usersModal = new bootstrap.Modal(document.getElementById('usersModal'));
        userEditModal = new bootstrap.Modal(document.getElementById('userEditModal'));
    }

    await loadEmployees();

    const tabs = [
        { name: "📅 Текущий месяц", filterType: "current-month", filterValue: "" },
        { name: "🏛 Общетехникумовские", filterType: "category", filterValue: "general" },
        { name: "🎓 Профориентация", filterType: "category", filterValue: "career" },
        { name: "🏢 Административно-хозяйственная", filterType: "service", filterValue: "admin" },
        { name: "🤝 Социально-педагогическая", filterType: "service", filterValue: "social-ped" },
        { name: "📚 Учебно-методический отдел", filterType: "service", filterValue: "methodical" },
        { name: "✈️ БАС-центр", filterType: "service", filterValue: "bas" },
        { name: "🌍 Внешние мероприятия", filterType: "category", filterValue: "external" },
        { name: "👥 Совет руководства", filterType: "service", filterValue: "council" },
        { name: "💻 Отдел ИКТ", filterType: "service", filterValue: "ict" },
        { name: "📖 Учебная служба", filterType: "service", filterValue: "academic" },
        { name: "🏋️ Физкультура", filterType: "service", filterValue: "physical" },
        { name: "📋 Организационная работа", filterType: "service", filterValue: "organizational" }
    ];
    const tabsContainer = document.getElementById('plannerTabs');
    tabsContainer.innerHTML = '';
    tabs.forEach((tab, idx) => {
        const btn = document.createElement('button');
        btn.className = `nav-link ${idx === 0 ? 'active' : ''}`;
        btn.innerText = tab.name;
        btn.setAttribute('data-filter-type', tab.filterType);
        btn.setAttribute('data-filter-value', tab.filterValue);
        btn.addEventListener('click', () => {
            document.querySelectorAll('#plannerTabs .nav-link').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            currentFilterType = tab.filterType;
            currentFilterValue = tab.filterValue;
            loadEvents();
        });
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.appendChild(btn);
        tabsContainer.appendChild(li);
    });

    document.getElementById('addEventBtn').addEventListener('click', () => openEditModal(null));
    document.getElementById('importCsvBtn').addEventListener('click', () => importModal.show());
    document.getElementById('confirmImportBtn').addEventListener('click', importCSV);
    document.getElementById('saveEventBtn').addEventListener('click', saveEvent);
    document.getElementById('deleteEventBtn').addEventListener('click', deleteCurrentEvent);
    document.getElementById('manageEmployeesBtn').addEventListener('click', () => { loadEmployeesTable(); modalEmployees.show(); });
    document.getElementById('addEmployeeBtn').addEventListener('click', () => openEmployeeEditModal(null));
    document.getElementById('saveEmployeeBtn').addEventListener('click', saveEmployee);
    if (document.getElementById('importEmployeesBtn')) {
        document.getElementById('importEmployeesBtn').addEventListener('click', () => importEmployeesModal.show());
        document.getElementById('confirmImportEmployeesBtn').addEventListener('click', importEmployeesCSV);
        document.getElementById('importUsersBtn').addEventListener('click', () => importUsersModal.show());
        document.getElementById('confirmImportUsersBtn').addEventListener('click', importUsersCSV);
        document.getElementById('manageUsersBtn').addEventListener('click', () => { loadUsersTable(); usersModal.show(); });
        document.getElementById('addUserBtn').addEventListener('click', () => openUserEditModal(null));
        document.getElementById('saveUserBtn').addEventListener('click', saveUser);
    }

    loadEvents();
});

async function loadEmployees() {
    try {
        const resp = await fetch('/api/employees');
        employeesList = await resp.json();
        populateEmployeeSelects();
        initSearchFilters();
    } catch(e) { console.error(e); }
}

function populateEmployeeSelects() {
    const responsibleSelect = document.getElementById('responsible');
    const controllerSelect = document.getElementById('controller');
    if (!responsibleSelect) return;
    responsibleSelect.innerHTML = '';
    controllerSelect.innerHTML = '';
    employeesList.forEach(emp => {
        const opt1 = document.createElement('option');
        opt1.value = emp.id;
        opt1.textContent = emp.full_name;
        responsibleSelect.appendChild(opt1);
        const opt2 = document.createElement('option');
        opt2.value = emp.id;
        opt2.textContent = emp.full_name;
        controllerSelect.appendChild(opt2);
    });
}

function initSearchFilters() {
    const responsibleSearch = document.getElementById('responsibleSearch');
    const controllerSearch = document.getElementById('controllerSearch');
    const responsibleSelect = document.getElementById('responsible');
    const controllerSelect = document.getElementById('controller');
    if (!responsibleSearch) return;
    function filterSelect(searchInput, selectElement) {
        const filter = searchInput.value.toLowerCase();
        for (let opt of selectElement.options) {
            opt.style.display = opt.textContent.toLowerCase().includes(filter) ? '' : 'none';
        }
    }
    responsibleSearch.addEventListener('input', () => filterSelect(responsibleSearch, responsibleSelect));
    controllerSearch.addEventListener('input', () => filterSelect(controllerSearch, controllerSelect));
}

async function loadEvents() {
    const loading = document.getElementById('loadingIndicator');
    const container = document.getElementById('cardsContainer');
    const emptyMsg = document.getElementById('emptyMessage');
    loading.classList.remove('d-none');
    container.innerHTML = '';
    emptyMsg.classList.add('d-none');
    let url = (currentFilterType === 'current-month') ? '/api/events/current-month' : `/api/events?filter_by=${currentFilterType}&value=${currentFilterValue}`;
    const resp = await fetch(url);
    const events = await resp.json();
    currentEvents = events;
    loading.classList.add('d-none');
    if (!events.length) { emptyMsg.classList.remove('d-none'); return; }
    renderCards(events);
}

function renderCards(events) {
    const container = document.getElementById('cardsContainer');
    container.innerHTML = '';
    const today = new Date().toISOString().slice(0,10);
    const serviceIcons = { "general":"🏛️","career":"🎓","admin":"🏢","social-ped":"🤝","methodical":"📚","bas":"✈️","external":"🌍","council":"👥","ict":"💻","academic":"📖","physical":"🏋️","organizational":"📋" };
    events.forEach(ev => {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 col-xl-3';
        const card = document.createElement('div');
        card.className = `event-card ${!ev.planned ? 'unplanned' : ''}`;
        card.style.borderLeftColor = ev.color || '#0d6efd';
        let dateObj = new Date(ev.date);
        let formattedDate = dateObj.toLocaleDateString('ru-RU', { day:'numeric', month:'long' });
        if (ev.date) formattedDate = `${formattedDate} ${ev.time ? 'в ' + ev.time.slice(0,5) : ''}`;
        let effectiveStatus = ev.status;
        if (ev.date === today && !['done','cancelled','postponed'].includes(ev.status)) effectiveStatus = 'today';
        let statusIcon = '', statusClass = '';
        switch(effectiveStatus) {
            case 'done': statusIcon='✅'; statusClass='status-done'; break;
            case 'postponed': statusIcon='🔄'; statusClass='status-postponed'; break;
            case 'today': statusIcon='📅'; statusClass='status-today'; break;
            case 'cancelled': statusIcon='❌'; statusClass='status-cancelled'; break;
            default: statusIcon='📋'; statusClass='status-plan';
        }
        const statusText = { done:'Завершено', postponed:'Перенесено', today:'Сегодня', cancelled:'Отменено', plan:'Запланировано' }[effectiveStatus] || '';
        const icon = serviceIcons[ev.service] || '📌';
        const responsibleText = Array.isArray(ev.responsible) ? ev.responsible.join(', ') : ev.responsible;
        card.innerHTML = `<div class="card-date">📅 ${formattedDate}</div><div class="card-title"><span class="service-icon">${icon}</span> <span>${escapeHtml(ev.title)}</span></div><div class="card-responsible"><i class="bi bi-person-badge"></i> ${escapeHtml(responsibleText)}</div><div class="card-status"><span class="status-badge ${statusClass}">${statusIcon} ${statusText}</span></div>`;
        card.addEventListener('click', (e) => { e.stopPropagation(); openEditModal(ev.id); });
        col.appendChild(card);
        container.appendChild(col);
    });
}

function openEditModal(id) {
    document.getElementById('eventForm').reset();
    document.getElementById('eventId').value = '';
    document.getElementById('deleteEventBtn').style.display = id ? 'inline-block' : 'none';
    if (id === null) {
        document.getElementById('modalTitle').innerText = '➕ Новое мероприятие';
        document.getElementById('planned').value = 'false';
        document.getElementById('color').value = '#ffffff';
        modalEvent.show();
    } else {
        const event = currentEvents.find(e => e.id == id);
        if (!event) return;
        document.getElementById('modalTitle').innerText = '✏️ Редактирование';
        document.getElementById('eventId').value = event.id;
        document.getElementById('title').value = event.title;
        document.getElementById('description').value = event.description || '';
        document.getElementById('date').value = event.date;
        document.getElementById('time').value = event.time;
        document.getElementById('participants_count').value = event.participants_count;
        document.getElementById('participants_details').value = event.participants_details;
        let statusVal = event.status;
        if (!['done','postponed','today','cancelled','plan'].includes(statusVal)) statusVal = 'plan';
        document.getElementById('status').value = statusVal;
        document.getElementById('color').value = event.color;
        document.getElementById('category').value = event.category || 'general';
        document.getElementById('service').value = event.service || 'general';
        document.getElementById('planned').value = event.planned ? 'true' : 'false';
        
        const responsibleSelect = document.getElementById('responsible');
        const controllerSelect = document.getElementById('controller');
        for (let opt of responsibleSelect.options) opt.selected = false;
        for (let opt of controllerSelect.options) opt.selected = false;
        
        const responsibleNames = Array.isArray(event.responsible) ? event.responsible : [event.responsible];
        const controllerNames = Array.isArray(event.controller) ? event.controller : [event.controller];
        
        responsibleNames.forEach(name => {
            const opt = Array.from(responsibleSelect.options).find(o => o.textContent === name);
            if (opt) opt.selected = true;
        });
        controllerNames.forEach(name => {
            const opt = Array.from(controllerSelect.options).find(o => o.textContent === name);
            if (opt) opt.selected = true;
        });
        
        modalEvent.show();
    }
}

async function saveEvent() {
    const id = document.getElementById('eventId').value;
    const responsibleSelect = document.getElementById('responsible');
    const controllerSelect = document.getElementById('controller');
    const responsible_ids = Array.from(responsibleSelect.selectedOptions).map(opt => parseInt(opt.value));
    const controller_ids = Array.from(controllerSelect.selectedOptions).map(opt => parseInt(opt.value));
    const data = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        date: document.getElementById('date').value,
        time: document.getElementById('time').value,
        participants_count: parseInt(document.getElementById('participants_count').value) || 0,
        participants_details: document.getElementById('participants_details').value,
        status: document.getElementById('status').value,
        color: document.getElementById('color').value,
        category: document.getElementById('category').value,
        service: document.getElementById('service').value,
        planned: document.getElementById('planned').value === 'true',
        responsible_ids, controller_ids
    };
    if (!data.title || !data.date || !data.time || responsible_ids.length===0 || controller_ids.length===0) {
        alert('Заполните обязательные поля: название, дата, время, хотя бы один ответственный и один контролирующий.');
        return;
    }
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/event/${id}` : '/api/event';
    const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) { modalEvent.hide(); loadEvents(); } else alert('Ошибка сохранения');
}

async function deleteCurrentEvent() {
    const id = document.getElementById('eventId').value;
    if (!id) return;
    if (!confirm('Удалить мероприятие?')) return;
    await fetch(`/api/event/${id}`, { method: 'DELETE' });
    modalEvent.hide();
    loadEvents();
}

async function loadEmployeesTable() {
    const resp = await fetch('/api/employees');
    const employees = await resp.json();
    const tbody = document.getElementById('employeesTableBody');
    tbody.innerHTML = '';
    employees.forEach(emp => {
        const row = tbody.insertRow();
        row.insertCell(0).textContent = emp.full_name;
        row.insertCell(1).textContent = emp.position || '';
        row.insertCell(2).textContent = emp.department || '';
        row.insertCell(3).textContent = emp.email || '';
        row.insertCell(4).textContent = emp.phone || '';
        const actions = row.insertCell(5);
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.onclick = () => openEmployeeEditModal(emp);
        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-sm btn-outline-danger';
        delBtn.innerHTML = '<i class="bi bi-trash"></i>';
        delBtn.onclick = async () => {
            if (confirm(`Удалить сотрудника ${emp.full_name}?`)) {
                await fetch(`/api/employee/${emp.id}`, { method: 'DELETE' });
                await loadEmployees();
                await loadEmployeesTable();
            }
        };
        actions.appendChild(editBtn);
        actions.appendChild(delBtn);
    });
}

function openEmployeeEditModal(employee) {
    document.getElementById('employeeForm').reset();
    document.getElementById('employeeId').value = '';
    if (employee) {
        document.getElementById('employeeModalTitle').innerText = 'Редактирование сотрудника';
        document.getElementById('employeeId').value = employee.id;
        document.getElementById('empFullName').value = employee.full_name;
        document.getElementById('empPosition').value = employee.position || '';
        document.getElementById('empDepartment').value = employee.department || '';
        document.getElementById('empEmail').value = employee.email || '';
        document.getElementById('empPhone').value = employee.phone || '';
    } else {
        document.getElementById('employeeModalTitle').innerText = 'Новый сотрудник';
    }
    modalEmployeeEdit.show();
}

async function saveEmployee() {
    const id = document.getElementById('employeeId').value;
    const data = {
        full_name: document.getElementById('empFullName').value,
        position: document.getElementById('empPosition').value,
        department: document.getElementById('empDepartment').value,
        email: document.getElementById('empEmail').value,
        phone: document.getElementById('empPhone').value
    };
    if (!data.full_name) { alert('Введите ФИО'); return; }
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/employee/${id}` : '/api/employee';
    const resp = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (resp.ok) {
        modalEmployeeEdit.hide();
        await loadEmployees();
        await loadEmployeesTable();
        populateEmployeeSelects();
    } else {
        const err = await resp.json();
        alert(err.error || 'Ошибка');
    }
}

async function importCSV() {
    const fileInput = document.getElementById('csvFile');
    if (!fileInput.files.length) { alert('Выберите CSV файл'); return; }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const resp = await fetch('/api/import', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) alert('Ошибка: ' + data.error);
    else alert(`Импортировано ${data.added} мероприятий`);
    importModal.hide();
    loadEvents();
    fileInput.value = '';
}

async function importEmployeesCSV() {
    const fileInput = document.getElementById('employeesCsvFile');
    if (!fileInput.files.length) { alert('Выберите CSV файл'); return; }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const resp = await fetch('/api/import-employees', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) alert('Ошибка: ' + data.error);
    else alert(`Добавлено: ${data.added}, пропущено (уже есть): ${data.skipped}`);
    await loadEmployees();
    await loadEmployeesTable();
    importEmployeesModal.hide();
    fileInput.value = '';
}

async function importUsersCSV() {
    const fileInput = document.getElementById('usersCsvFile');
    if (!fileInput.files.length) { alert('Выберите CSV файл'); return; }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    const resp = await fetch('/api/import-users', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.error) alert('Ошибка: ' + data.error);
    else alert(`Добавлено пользователей: ${data.added}, пропущено: ${data.skipped}`);
    importUsersModal.hide();
    fileInput.value = '';
}

async function loadUsersTable() {
    const resp = await fetch('/api/admin/users');
    const users = await resp.json();
    const tbody = document.getElementById('usersTableBody');
    tbody.innerHTML = '';
    users.forEach(user => {
        const row = tbody.insertRow();
        row.insertCell(0).textContent = user.login;
        row.insertCell(1).textContent = user.full_name;
        row.insertCell(2).textContent = user.role;
        row.insertCell(3).textContent = user.service_code || '';
        const actions = row.insertCell(4);
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary me-1';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.onclick = () => openUserEditModal(user);
        const delBtn = document.createElement('button');
        delBtn.className = 'btn btn-sm btn-outline-danger';
        delBtn.innerHTML = '<i class="bi bi-trash"></i>';
        delBtn.onclick = async () => {
            if (confirm(`Удалить пользователя ${user.login}?`)) {
                const resp = await fetch(`/api/admin/user/${user.id}`, { method: 'DELETE' });
                if (resp.ok) await loadUsersTable();
                else alert('Ошибка удаления');
            }
        };
        actions.appendChild(editBtn);
        actions.appendChild(delBtn);
    });
}

function openUserEditModal(user) {
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    if (user) {
        document.getElementById('userModalTitle').innerText = 'Редактирование пользователя';
        document.getElementById('userId').value = user.id;
        document.getElementById('userLogin').value = user.login;
        document.getElementById('userFullName').value = user.full_name;
        document.getElementById('userRole').value = user.role;
        document.getElementById('userServiceCode').value = user.service_code || '';
        document.getElementById('userPassword').required = false;
        document.getElementById('userPassword').placeholder = 'Оставьте пустым, чтобы не менять';
    } else {
        document.getElementById('userModalTitle').innerText = 'Новый пользователь';
        document.getElementById('userPassword').required = true;
        document.getElementById('userPassword').placeholder = 'Введите пароль';
    }
    userEditModal.show();
}

async function saveUser() {
    const id = document.getElementById('userId').value;
    const data = {
        login: document.getElementById('userLogin').value,
        full_name: document.getElementById('userFullName').value,
        role: document.getElementById('userRole').value,
        service_code: document.getElementById('userServiceCode').value
    };
    const password = document.getElementById('userPassword').value;
    if (password) data.password = password;
    if (!data.login || !data.full_name) {
        alert('Заполните логин и ФИО');
        return;
    }
    if (!id && !password) {
        alert('Для нового пользователя укажите пароль');
        return;
    }
    const method = id ? 'PUT' : 'POST';
    const url = id ? `/api/admin/user/${id}` : '/api/admin/user';
    const resp = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (resp.ok) {
        userEditModal.hide();
        await loadUsersTable();
    } else {
        const err = await resp.json();
        alert(err.error || 'Ошибка');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : (m === '<' ? '&lt;' : '&gt;'));
}