/* Pehredaar Web Interface Logic */

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
    ? 'http://localhost:8000'
    : '';  // Same origin in production

// ==================== Tab Switching ====================
function switchTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active', 'border-teal-600', 'text-teal-600');
        el.classList.add('border-transparent', 'text-gray-500');
    });
    document.getElementById(`content-${tab}`).classList.remove('hidden');
    const btn = document.getElementById(`tab-${tab}`);
    btn.classList.add('active', 'border-teal-600', 'text-teal-600');
    btn.classList.remove('border-transparent', 'text-gray-500');

    if (tab === 'citations') loadCitations();
}

// ==================== Helper Functions ====================
function formatINR(amount) {
    return '₹' + Number(amount).toLocaleString('en-IN');
}

function winnabilityBadge(level) {
    const classes = { green: 'badge-green', amber: 'badge-amber', red: 'badge-red' };
    const icons = { green: '✅', amber: '⚠️', red: '🔴' };
    const cls = classes[level] || 'badge-amber';
    const icon = icons[level] || '⚠️';
    return `<span class="${cls} px-2 py-1 text-xs font-medium rounded-full">${icon} ${level.toUpperCase()}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== Charge Row Management ====================
function addChargeRow(containerId) {
    const container = document.getElementById(containerId);
    const row = document.createElement('div');
    row.className = 'flex gap-2';
    row.innerHTML = `
        <input type="text" placeholder="Item name" class="input flex-1 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm charge-name">
        <input type="number" placeholder="Amount ₹" class="input w-32 px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm charge-amount">
        <button onclick="this.parentElement.remove()" class="text-red-500 hover:text-red-700 px-2">✕</button>
    `;
    container.appendChild(row);
}

function collectCharges(containerId) {
    const charges = {};
    const container = document.getElementById(containerId);
    container.querySelectorAll('div.flex').forEach(row => {
        const name = row.querySelector('.charge-name')?.value?.trim();
        const amount = parseFloat(row.querySelector('.charge-amount')?.value || '0');
        if (name && amount > 0) {
            charges[name] = amount;
        }
    });
    return charges;
}

// ==================== Policy Loading ====================
async function loadPolicies() {
    try {
        const response = await fetch(`${API_BASE}/policies`);
        const data = await response.json();
        if (data.success) {
            const select = document.getElementById('policy-name');
            data.plans.forEach(plan => {
                const option = document.createElement('option');
                option.value = plan.name;
                const capInfo = plan.room_cap_type === 'pct' ? `${plan.room_cap_value}% of SI` :
                               plan.room_cap_type === 'abs' ? `₹${plan.room_cap_value}/day` : 'No limit';
                option.textContent = `${plan.name} (${plan.insurer}) — Room: ${capInfo}`;
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.log('Policy list not available (API may not be running)');
    }
}

// ==================== Defender Analysis ====================
async function runDefenderAnalysis() {
    const resultsDiv = document.getElementById('defender-results');
    resultsDiv.innerHTML = '<div class="spinner"></div><p class="text-center mt-3 text-gray-400">Analyzing...</p>';

    const policyName = document.getElementById('policy-name').value;
    const sumInsured = parseInt(document.getElementById('sum-insured').value) || 500000;
    const roomCap = parseFloat(document.getElementById('room-cap').value) || null;
    const actualRoom = parseFloat(document.getElementById('actual-room').value) || 0;
    const days = parseInt(document.getElementById('days').value) || 1;
    const variableCharges = collectCharges('variable-charges');
    const fixedCharges = collectCharges('fixed-charges');

    // Build the calculation input
    const inputs = {
        sum_insured: sumInsured,
        actual_room_rent_per_day: actualRoom,
        days: days,
        variable_charges: variableCharges,
        fixed_charges: fixedCharges
    };

    if (roomCap) {
        inputs.room_cap_per_day = roomCap;
    }

    try {
        const response = await fetch(`${API_BASE}/defender/calculate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ inputs })
        });
        const data = await response.json();

        if (data.success) {
            displayDefenderResults(data.result, { policyName, sumInsured, roomCap, actualRoom, days });
        } else {
            resultsDiv.innerHTML = `<div class="text-red-500">Error: ${data.detail || 'Analysis failed'}</div>`;
        }
    } catch (e) {
        // If API not available, compute locally
        resultsDiv.innerHTML = `<div class="text-amber-500 text-sm mb-3">⚠️ API not running. Showing calculation result directly.</div>`;
        computeDefenderLocally(inputs, { policyName, sumInsured, roomCap, actualRoom, days });
    }
}

function computeDefenderLocally(inputs, context) {
    // Simple local computation for demo when API is not available
    const factor = inputs.room_cap_per_day ? Math.min(1, inputs.room_cap_per_day / inputs.actual_room_rent_per_day) : 1;
    const roomCharges = inputs.actual_room_rent_per_day * inputs.days;
    const roomEligible = inputs.room_cap_per_day ? Math.min(inputs.actual_room_rent_per_day, inputs.room_cap_per_day) * inputs.days : roomCharges;
    const variableTotal = Object.values(inputs.variable_charges).reduce((a, b) => a + b, 0);
    const fixedTotal = Object.values(inputs.fixed_charges).reduce((a, b) => a + b, 0);
    const variableEligible = variableTotal * factor;
    const proportionateHit = variableTotal - variableEligible;
    const totalBill = roomCharges + variableTotal + fixedTotal;
    const totalEligible = roomEligible + variableEligible + fixedTotal;
    const totalOop = totalBill - totalEligible;

    displayDefenderResults({
        factor, room_charges: roomCharges, room_eligible: roomEligible,
        room_excess: roomCharges - roomEligible, variable_total: variableTotal,
        variable_eligible: variableEligible, proportionate_hit: proportionateHit,
        fixed_total: fixedTotal, fixed_eligible: fixedTotal,
        total_bill: totalBill, total_eligible: totalEligible, total_oop: totalOop
    }, context);
}

function displayDefenderResults(r, ctx) {
    const resultsDiv = document.getElementById('defender-results');
    const isDeduction = r.total_oop > 0;
    const exposureColor = isDeduction ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400';

    resultsDiv.innerHTML = `
        <h3 class="text-lg font-semibold mb-4">Analysis Results</h3>
        
        <div class="result-section">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Total Out-of-Pocket Exposure</p>
            <p class="result-exposure ${exposureColor}">${formatINR(r.total_oop)}</p>
            ${isDeduction ? '<p class="text-xs text-red-500">⚠️ This is money you may lose to proportionate deduction.</p>' : '<p class="text-xs text-green-500">✅ No proportionate deduction — you\'re within your policy cap.</p>'}
        </div>

        <div class="result-section">
            <p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Breakdown</p>
            <table class="w-full text-sm">
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Proportionate Factor</td><td class="py-1 text-right font-mono">${r.factor.toFixed(4)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Room Charges</td><td class="py-1 text-right font-mono">${formatINR(r.room_charges)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Room Eligible</td><td class="py-1 text-right font-mono">${formatINR(r.room_eligible)}</td></tr>
                <tr><td class="py-1 text-red-600 dark:text-red-400">Room Excess</td><td class="py-1 text-right font-mono text-red-600 dark:text-red-400">${formatINR(r.room_excess)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Variable Charges Total</td><td class="py-1 text-right font-mono">${formatINR(r.variable_total)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Variable Eligible</td><td class="py-1 text-right font-mono">${formatINR(r.variable_eligible)}</td></tr>
                <tr><td class="py-1 text-red-600 dark:text-red-400">Proportionate Hit (hidden)</td><td class="py-1 text-right font-mono text-red-600 dark:text-red-400">${formatINR(r.proportionate_hit)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Fixed Charges Total</td><td class="py-1 text-right font-mono">${formatINR(r.fixed_total)}</td></tr>
                <tr><td class="py-1 text-gray-600 dark:text-gray-400">Fixed Eligible (NOT cut)</td><td class="py-1 text-right font-mono">${formatINR(r.fixed_eligible)}</td></tr>
                <tr class="border-t border-gray-200 dark:border-gray-700"><td class="py-2 font-semibold">Total Bill</td><td class="py-2 text-right font-mono font-semibold">${formatINR(r.total_bill)}</td></tr>
                <tr><td class="py-1 font-semibold">Total Eligible</td><td class="py-1 text-right font-mono font-semibold">${formatINR(r.total_eligible)}</td></tr>
                <tr><td class="py-1 font-bold text-red-600 dark:text-red-400">Your Out-of-Pocket</td><td class="py-1 text-right font-mono font-bold text-red-600 dark:text-red-400">${formatINR(r.total_oop)}</td></tr>
            </table>
        </div>

        ${isDeduction ? `
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mt-4">
            <p class="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-2">⚠️ BEFORE YOU SIGN</p>
            <p class="text-xs text-amber-700 dark:text-amber-300 mb-2">Your room rent exceeds your policy cap. The insurer may apply <strong>proportionate deduction</strong> to your ENTIRE bill — not just the room.</p>
            <p class="text-xs text-amber-700 dark:text-amber-300">Per IRDAI guidelines (IRDAI/HLT/REG/CIR/151/06/2020), medicines, implants, and diagnostics <strong>CANNOT</strong> be proportionately deducted. If the insurer cuts these too, you have a strong refund case.</p>
        </div>
        ` : ''}

        <div class="mt-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-800 pt-3">
            <p>Informational only, not legal or insurance advice. Estimates based on policy terms and bill data. Verify with billing desk.</p>
        </div>
    `;
}

// ==================== ClaimBack Analysis ====================
async function runClaimBackAnalysis() {
    const resultsDiv = document.getElementById('claimback-results');
    const letterText = document.getElementById('rejection-text').value.trim();

    if (!letterText) {
        resultsDiv.innerHTML = '<div class="text-amber-500 text-sm">Please paste the rejection letter text first.</div>';
        return;
    }

    resultsDiv.innerHTML = '<div class="spinner"></div><p class="text-center mt-3 text-gray-400">Analyzing rejection & drafting appeal...</p>';

    const continuousMonths = parseInt(document.getElementById('continuous-months').value) || 0;
    const claimAmount = parseFloat(document.getElementById('claim-amount').value) || 0;

    const context = {};
    if (continuousMonths > 0) context.continuous_cover_months = continuousMonths;
    if (claimAmount > 0) context.claim_amount = claimAmount;

    try {
        const response = await fetch(`${API_BASE}/claimback/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ letter_text: letterText, context })
        });
        const data = await response.json();

        if (data.success) {
            displayClaimBackResults(data.result);
        } else {
            resultsDiv.innerHTML = `<div class="text-red-500">Error: ${data.detail || 'Analysis failed'}</div>`;
        }
    } catch (e) {
        resultsDiv.innerHTML = `<div class="text-amber-500 text-sm">⚠️ API not running. Please start the server with <code>python main.py</code></div>`;
    }
}

function displayClaimBackResults(result) {
    const resultsDiv = document.getElementById('claimback-results');
    const cls = result.classification;
    const appeal = result.appeal;
    const route = result.escalation_route;

    resultsDiv.innerHTML = `
        <h3 class="text-lg font-semibold mb-4">Analysis Results</h3>

        <div class="result-section">
            <p class="text-xs text-gray-500 uppercase tracking-wide">Classification</p>
            <div class="flex items-center gap-2 mt-1">
                <span class="font-semibold">${cls.reason_code}</span>
                ${winnabilityBadge(cls.winnability)}
            </div>
            <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">${cls.rationale || ''}</p>
            <p class="text-xs mt-1"><span class="text-gray-500">Governing clause:</span> <code class="text-teal-600">${cls.clause}</code></p>
        </div>

        <div class="result-section">
            <p class="text-xs text-gray-500 uppercase tracking-wide mb-2">Escalation Route</p>
            ${route.escalation_steps.map(step => `
                <div class="flag-item">
                    <p class="text-sm font-medium">Step ${step.step}: ${step.authority}</p>
                    <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">${step.action}</p>
                    ${step.deadline ? `<p class="text-xs text-gray-500 mt-1">⏰ ${step.deadline}</p>` : ''}
                    ${step.monetary_limit ? `<p class="text-xs text-gray-500">💰 ${step.monetary_limit}</p>` : ''}
                </div>
            `).join('')}
        </div>

        <div class="result-section">
            <div class="flex items-center justify-between mb-2">
                <p class="text-xs text-gray-500 uppercase tracking-wide">Draft Appeal Letter</p>
                <button onclick="copyAppeal()" class="text-xs text-teal-600 hover:underline">📋 Copy</button>
            </div>
            <div class="appeal-letter" id="appeal-text">${escapeHtml(appeal.draft_letter)}</div>
            <p class="text-xs text-gray-500 mt-2">✅ Citations validated: ${appeal.citations_valid ? 'All valid' : 'WARNING: invalid citations'} | Clause: ${appeal.clause_id}</p>
        </div>

        <div class="mt-4 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-800 pt-3">
            <p>${cls.disclaimer || 'Informational only, not legal or insurance advice.'}</p>
        </div>
    `;
}

function copyAppeal() {
    const text = document.getElementById('appeal-text').textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert('Appeal letter copied to clipboard!');
    });
}

// ==================== Citations ====================
async function loadCitations() {
    const listDiv = document.getElementById('citations-list');
    try {
        const response = await fetch(`${API_BASE}/citations`);
        const data = await response.json();
        if (data.success) {
            listDiv.innerHTML = data.citations.map(c => `
                <div class="card bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
                    <div class="flex items-start justify-between mb-2">
                        <code class="text-teal-600 font-mono text-sm font-bold">${c.clause_id}</code>
                        <span class="text-xs px-2 py-0.5 rounded-full ${c.legal_status === 'legally_binding' ? 'badge-green' : 'badge-amber'}">${c.legal_status === 'legally_binding' ? 'Binding' : 'Reference'}</span>
                    </div>
                    <p class="text-sm font-semibold mb-1">${c.title}</p>
                    <p class="text-xs text-gray-600 dark:text-gray-400">${c.source}</p>
                    <p class="text-xs text-gray-500 mt-1">📅 ${c.date} | 📄 ${c.section}</p>
                    ${c.url && c.url !== 'N/A — refer to your policy document' ? `<a href="${c.url}" target="_blank" class="text-xs text-teal-600 hover:underline mt-1 inline-block">View source →</a>` : ''}
                </div>
            `).join('');
        }
    } catch (e) {
        listDiv.innerHTML = '<div class="text-center text-gray-400 col-span-2"><p>Unable to load citations. API may not be running.</p></div>';
    }
}

// ==================== Init ====================
window.addEventListener('DOMContentLoaded', () => {
    loadPolicies();
});