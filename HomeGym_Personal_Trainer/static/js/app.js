/* ============================================
   HOME-GYM TACTICAL HUD — Application Logic
   Pure Vanilla JS — No frameworks
   ============================================ */

const API = '';

// ---- State ----
let selectedExperience = null;
let selectedPreference = null;
let selectedFrequency = null;

// ---- DOM References ----
const screens = {
    register: document.getElementById('screen-register'),
    session: document.getElementById('screen-session'),
    workout: document.getElementById('screen-workout'),
};

// ---- Utilities ----
function showScreen(name) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[name].classList.add('active');
    
    const statusMap = {
        register: 'REGISTRATION',
        session: 'SESSION CONFIG',
        workout: 'OPERATION ACTIVE',
    };
    document.getElementById('topbar-status').textContent = statusMap[name] || '';
}

function updateClock() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    document.getElementById('topbar-clock').textContent = `${h}:${m}:${s}`;
}
setInterval(updateClock, 1000);
updateClock();

// ---- Selector Buttons ----
function initSelectorGroups() {
    document.querySelectorAll('.selector-group').forEach(group => {
        group.querySelectorAll('.sel-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                group.querySelectorAll('.sel-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                
                const groupId = group.id;
                const val = btn.dataset.value;
                if (groupId === 'sel-experience') selectedExperience = val;
                if (groupId === 'sel-preference') selectedPreference = val;
                if (groupId === 'sel-frequency') selectedFrequency = val;
            });
        });
    });
}

// ---- Equipment Loading ----
async function loadEquipment() {
    try {
        const res = await fetch(`${API}/api/equipment`);
        const items = await res.json();
        const grid = document.getElementById('equipment-grid');
        grid.innerHTML = '';
        
        items.forEach(item => {
            const label = document.createElement('label');
            label.className = 'chk-label';
            label.innerHTML = `<input type="checkbox" value="${item.id}"><span class="chk-box"></span>${item.name.toUpperCase()}`;
            grid.appendChild(label);
        });
    } catch (err) {
        console.error('Failed to load equipment:', err);
    }
}

// ---- Energy Slider ----
function initEnergySlider() {
    const slider = document.getElementById('field-energy');
    const display = document.getElementById('energy-val');
    if (slider && display) {
        slider.addEventListener('input', () => {
            display.textContent = slider.value;
        });
    }
}

// ---- Feedback Box ----
function showFeedback(msg, isSuccess) {
    const box = document.getElementById('validation-feedback');
    box.textContent = msg;
    box.classList.remove('hidden', 'success');
    if (isSuccess) box.classList.add('success');
}

function hideFeedback() {
    document.getElementById('validation-feedback').classList.add('hidden');
}

// ---- Onboarding Submit ----
async function handleOnboarding(e) {
    e.preventDefault();
    hideFeedback();

    const nickname = document.getElementById('field-nickname').value.trim();
    const age = parseInt(document.getElementById('field-age').value);
    const weight_kg = parseFloat(document.getElementById('field-weight').value);
    const height_cm = parseFloat(document.getElementById('field-height').value);

    const equipmentChecks = document.querySelectorAll('#equipment-grid input:checked');
    const equipment_list = Array.from(equipmentChecks).map(c => c.value);

    const objectiveChecks = document.querySelectorAll('#objectives-grid input:checked');
    const objectives = Array.from(objectiveChecks).map(c => c.value);

    const payload = {
        nickname,
        age,
        weight_kg,
        height_cm,
        experience_level: selectedExperience,
        training_preference: selectedPreference,
        frequency: selectedFrequency,
        equipment_list,
        objectives,
    };

    const btn = document.getElementById('btn-register');
    btn.disabled = true;
    btn.querySelector('.btn-icon').textContent = '⟳';

    try {
        const res = await fetch(`${API}/api/onboard`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (data.success) {
            showFeedback(data.message, true);
            setTimeout(() => {
                renderProfileBar(payload);
                showScreen('session');
            }, 800);
        } else {
            showFeedback(data.message, false);
        }
    } catch (err) {
        showFeedback('COMMS ERROR: Failed to reach server.', false);
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-icon').textContent = '▸';
    }
}

// ---- Profile Bar ----
function renderProfileBar(profile) {
    const bar = document.getElementById('profile-bar');
    const tags = [
        ['CALLSIGN', profile.nickname],
        ['AGE', profile.age],
        ['MASS', `${profile.weight_kg}kg`],
        ['HEIGHT', `${profile.height_cm}cm`],
        ['LEVEL', profile.experience_level],
        ['TYPE', profile.training_preference],
        ['FREQ', profile.frequency],
    ];
    bar.innerHTML = tags.map(([k, v]) =>
        `<span class="profile-tag">${k}<span class="tag-value">${v}</span></span>`
    ).join('');
}

// ---- Session Submit ----
async function handleSession(e) {
    e.preventDefault();

    const energy = parseInt(document.getElementById('field-energy').value);
    const time = parseInt(document.getElementById('field-time').value);
    const goals = document.getElementById('field-goals').value.trim() || null;
    const injuriesRaw = document.getElementById('field-injuries').value.trim();
    const injuries = injuriesRaw ? injuriesRaw.split(',').map(s => s.trim()).filter(Boolean) : [];

    const payload = {
        current_energy: energy,
        time_available: time,
        session_goals: goals,
        local_injuries: injuries,
    };

    const btn = document.getElementById('btn-generate');
    const loader = document.getElementById('loading-indicator');
    btn.disabled = true;
    loader.classList.remove('hidden');

    try {
        const res = await fetch(`${API}/api/session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (data.success || data.workout_plan) {
            renderWorkoutPlan(data.workout_plan);
            showScreen('workout');
        } else {
            alert('Failed to compile plan: ' + (data.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('COMMS ERROR: Failed to reach server.');
    } finally {
        btn.disabled = false;
        loader.classList.add('hidden');
    }
}

// ---- Workout Renderer ----
function renderWorkoutPlan(plan) {
    const container = document.getElementById('workout-content');
    container.innerHTML = '';

    // Title & Meta
    const title = document.getElementById('workout-title');
    const meta  = document.getElementById('workout-meta');
    title.textContent = `OPERATION // ${(plan.athlete_nickname || 'ATHLETE').toUpperCase()}`;

    // Build time breakdown string
    const warmupMin    = plan.warm_up?.duration_minutes || 5;
    const strengthMin  = plan.strength_circuit?.duration_minutes || 0;
    const cardioMin    = plan.cardio_finisher?.duration_minutes || 0;
    const totalMin     = plan.estimated_duration_minutes || (warmupMin + strengthMin + cardioMin);
    let breakdown = `${warmupMin}min warmup`;
    if (strengthMin > 0) breakdown += ` + ${strengthMin}min strength`;
    if (cardioMin   > 0) breakdown += ` + ${cardioMin}min cardio`;
    meta.textContent = `LEVEL: ${(plan.experience_level || '?').toUpperCase()} | ${breakdown} = ${totalMin} MIN TOTAL`;

    // Warm-up
    if (plan.warm_up) {
        const section = createSection('WARMUP', plan.warm_up.title, `${plan.warm_up.duration_minutes} MIN`);
        const ul = document.createElement('ul');
        ul.className = 'warmup-list';
        const instructions = plan.warm_up.instructions || [];
        instructions.forEach(instr => {
            const li = document.createElement('li');
            li.textContent = instr;
            ul.appendChild(li);
        });
        section.appendChild(ul);
        container.appendChild(section);
    }

    // Strength Circuit
    if (plan.strength_circuit) {
        const sc = plan.strength_circuit;
        const durationStr = sc.duration_minutes ? `${sc.duration_minutes} MIN` : '';
        const exCount = (sc.exercises || []).length;
        const section = createSection(
            'STRENGTH',
            sc.title,
            durationStr,
            exCount ? `${exCount} EXERCISE${exCount !== 1 ? 'S' : ''}` : ''
        );
        const exercises = sc.exercises || [];
        exercises.forEach((ex, i) => {
            const row = document.createElement('div');
            row.className = 'exercise-row';
            row.innerHTML = `
                <div class="exercise-num">${String(i + 1).padStart(2, '0')}</div>
                <div class="exercise-body">
                    <div class="exercise-name">${(ex.name || '').toUpperCase()}</div>
                    <div class="exercise-stats">
                        <span>SETS <span class="stat-value">${ex.sets || '?'}</span></span>
                        <span>REPS <span class="stat-value">${ex.reps || '?'}</span></span>
                        <span>LOAD <span class="stat-value">${ex.load || 'BW'}</span></span>
                        ${ex.bench_angle ? `<span>ANGLE <span class="stat-value">${ex.bench_angle}</span></span>` : ''}
                    </div>
                    ${ex.notes ? `<div class="exercise-notes">"${ex.notes}"</div>` : ''}
                </div>
            `;
            section.appendChild(row);
        });
        container.appendChild(section);
    }

    // Cardio Finisher
    if (plan.cardio_finisher) {
        const cf = plan.cardio_finisher;
        const section = createSection('CARDIO', cf.title, `${cf.duration_minutes} MIN`);
        const block = document.createElement('div');
        block.className = 'cardio-block';
        block.innerHTML = `
            <span class="cardio-bpm">${cf.target_heart_rate_bpm || 130}</span>
            <span class="cardio-bpm-label">TARGET BPM</span>
            <div class="cardio-instructions">${cf.instructions || ''}</div>
        `;
        section.appendChild(block);
        container.appendChild(section);
    }
}


function createSection(tag, title, duration, badge) {
    const section = document.createElement('div');
    section.className = 'workout-section';
    section.innerHTML = `
        <div class="workout-section-header">
            <span class="section-index">${tag}</span>
            <span class="section-title">${(title || '').toUpperCase()}</span>
            <div class="section-header-right">
                ${badge ? `<span class="section-badge">${badge}</span>` : ''}
                ${duration ? `<span class="section-duration">${duration}</span>` : ''}
            </div>
        </div>
    `;
    return section;
}


// ---- Reset ----
async function handleReset() {
    if (!confirm('CONFIRM SYSTEM RESET?\nThis will erase your profile and return to registration.')) return;
    try {
        await fetch(`${API}/api/reset`, { method: 'POST' });
        // Reset local state
        selectedExperience = null;
        selectedPreference = null;
        selectedFrequency = null;
        document.querySelectorAll('.sel-btn.selected').forEach(b => b.classList.remove('selected'));
        document.getElementById('onboarding-form').reset();
        hideFeedback();
        showScreen('register');
    } catch (err) {
        alert('Reset failed.');
    }
}

// ---- Init ----
async function init() {
    initSelectorGroups();
    initEnergySlider();
    await loadEquipment();

    document.getElementById('onboarding-form').addEventListener('submit', handleOnboarding);
    document.getElementById('session-form').addEventListener('submit', handleSession);
    document.getElementById('btn-reset').addEventListener('click', handleReset);
    document.getElementById('btn-new-session').addEventListener('click', () => showScreen('session'));

    // Check if already onboarded
    try {
        const res = await fetch(`${API}/api/state`);
        const state = await res.json();
        if (state.is_onboarded && state.user_profile) {
            renderProfileBar(state.user_profile);
            showScreen('session');
        } else {
            showScreen('register');
        }
    } catch {
        showScreen('register');
    }
}

document.addEventListener('DOMContentLoaded', init);
