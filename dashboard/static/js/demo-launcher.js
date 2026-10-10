/**
 * HackCure — bouton « Lancer la démo » : choix du scénario (simulateur embarqué ou MQTT).
 */
const DemoLauncher = (() => {
    'use strict';
    const ICON = { full_demo: '🎬', fall_demo: '🚨', nurse_resolves: '🧑‍⚕️', sepsis_trend: '🌡️', iv_empty: '💧', fever_101: '🔥', normal_night: '🌙', stop: '⏹️' };
    let scenarios = [];
    let current = null;

    async function load() {
        try { const d = await Api.get('/api/demo/scenarios', { noRedirect: true }); scenarios = d.scenarios; current = d.current; } catch (_) { scenarios = []; }
    }

    function render() {
        const menu = document.getElementById('demo-menu'); if (!menu) return;
        const order = ['full_demo', 'fall_demo', 'nurse_resolves', 'fever_101', 'sepsis_trend', 'iv_empty', 'normal_night', 'stop'];
        const list = [...scenarios].sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name));
        menu.innerHTML = `<div class="notif-head"><span>Scénarios de démonstration</span>${current && current.name ? `<span class="tag tag-in_progress">en cours : ${current.name}</span>` : ''}</div>`
            + list.map(s => `<button data-name="${s.name}">${ICON[s.name] || '▶'} <b>${s.name}</b> <span class="muted small">(chambre ${s.room}${s.duration ? ', ' + s.duration + ' s' : ''})</span><span class="demo-desc">${Api.esc(s.description)}</span></button>`).join('');
        menu.querySelectorAll('button[data-name]').forEach(b => b.addEventListener('click', () => start(b.dataset.name)));
    }

    async function start(name) {
        document.getElementById('demo-menu')?.classList.add('hidden');
        try {
            const r = await Api.post('/api/demo/scenario', { name });
            current = r.scenario;
            Api.toast(`▶ Scénario « ${name} » lancé (${r.via})`, 'success');
            if (Views.current !== 'twin') Views.show('twin');
            const sc = scenarios.find(s => s.name === name);
            if (sc && sc.room && typeof HospitalScene !== 'undefined') HospitalScene.zoomToRoom(sc.room);
        } catch (e) { Api.toast('Scénario impossible : ' + e.message, 'critical'); }
    }

    function toggle() {
        const menu = document.getElementById('demo-menu'); if (!menu) return;
        const show = menu.classList.contains('hidden');
        document.getElementById('notif-dropdown')?.classList.add('hidden');
        if (show) { load().then(render); }
        menu.classList.toggle('hidden', !show);
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('btn-launch-demo')?.addEventListener('click', (e) => { e.stopPropagation(); toggle(); });
        document.addEventListener('click', (e) => { if (!e.target.closest('#demo-menu') && !e.target.closest('#btn-launch-demo')) document.getElementById('demo-menu')?.classList.add('hidden'); });
    });
    window.addEventListener('hackcure:ws', (e) => {
        const m = e.detail;
        if (m.type !== 'scenario') return;
        if (m.event === 'scenario_step') Api.toast(`🎬 ${m.name} · chambre ${m.room} · ${m.action}${m.params && m.params.posture ? ' → ' + m.params.posture : ''}`, 'info');
        else if (m.event === 'scenario_finished') { current = null; Api.toast(`🎬 Scénario « ${m.name} » terminé`, 'success'); }
        else if (m.event === 'scenario_started') current = { name: m.name, room: m.room };
    });
    return { start, load };
})();
