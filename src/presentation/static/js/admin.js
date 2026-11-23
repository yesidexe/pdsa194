let isUrnaOpen = false;
        let isTallied = false;
        let currentMode = "national";
        let candidateCache = [];
        let editingCandidateId = null;

        function showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            if (!container) return;
            const icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            const icon = document.createElement('i');
            icon.className = `fa-solid ${icons[type] || icons.info} mt-0.5`;
            const text = document.createElement('span');
            text.textContent = String(message ?? '');
            toast.append(icon, text);
            container.appendChild(toast);
            window.setTimeout(() => {
                toast.classList.add('toast-out');
                window.setTimeout(() => toast.remove(), 220);
            }, 4200);
        }

        function escapeHtml(value) {
            return String(value ?? '')
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        async function apiFetch(url, options = {}) {
            const response = await fetch(url, options);
            if (response.status === 401) {
                window.location.href = '/admin/login';
                throw new Error('Sesión expirada');
            }
            return response;
        }

        async function logoutAdmin() {
            try {
                await fetch('/api/admin/logout', { method: 'POST' });
            } finally {
                window.location.href = '/admin/login';
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            loadElectionMode();
            loadCandidates();
            loadAuditLogs();
            // Estado de urna, censo y bitácora se refrescan sin pulsar "Actualizar".
            window.setInterval(loadElectionMode, 10000);
            window.setInterval(loadAuditLogs, 10000);
        });

        async function loadElectionMode() {
            try {
                const res = await fetch('/api/election/mode');
                const data = await res.json();
                const modeChanged = currentMode !== data.mode;
                currentMode = data.mode;
                if (modeChanged) resetCandidateForm();
                isUrnaOpen = data.is_open;
                isTallied = Boolean(data.is_tallied);

                document.getElementById('adminSubheader').innerText = `${data.institution_name} • ${data.election_title}`;
                const badgeMode = document.getElementById('badgeCurrentMode');
                badgeMode.innerText = data.mode.toUpperCase() + ` (${data.document_type})`;

                const statusEl = document.getElementById('adminUrnaStatusText');
                const statusHint = document.getElementById('urnaStatusHint');
                const statusDot = document.getElementById('urnaStatusDot');
                const toggleButton = document.getElementById('btnToggleUrna');
                const toggleLabel = document.getElementById('btnToggleUrnaLabel');
                const toggleIcon = document.getElementById('btnToggleUrnaIcon');

                if (isTallied) {
                    statusEl.innerText = "Cerrada y escrutada";
                    statusEl.className = "text-lg font-bold text-indigo-700";
                    statusHint.innerText = "El acta ya fue generada. Reinicia la jornada para volver a votar.";
                    statusDot.className = "w-2.5 h-2.5 rounded-full bg-indigo-500 shrink-0";
                    toggleButton.disabled = true;
                    toggleLabel.innerText = "Jornada escrutada";
                    toggleIcon.className = "fa-solid fa-lock";
                } else {
                    toggleButton.disabled = false;
                    if (data.is_open) {
                        statusEl.innerText = "Abierta";
                        statusEl.className = "text-lg font-bold text-emerald-600";
                        statusHint.innerText = "Recibiendo votos.";
                        statusDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0";
                        toggleLabel.innerText = "Cerrar urna";
                        toggleIcon.className = "fa-solid fa-lock";
                    } else if (data.election_status === "DRAFT") {
                        statusEl.innerText = "Borrador";
                        statusEl.className = "text-lg font-bold text-amber-600";
                        statusHint.innerText = "Jornada en configuración. Abre la urna para recibir votos.";
                        statusDot.className = "w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0";
                        toggleLabel.innerText = "Abrir urna";
                        toggleIcon.className = "fa-solid fa-lock-open";
                    } else {
                        statusEl.innerText = "Cerrada";
                        statusEl.className = "text-lg font-bold text-rose-600";
                        statusHint.innerText = "No se reciben votos.";
                        statusDot.className = "w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0";
                        toggleLabel.innerText = "Abrir urna";
                        toggleIcon.className = "fa-solid fa-lock-open";
                    }
                }

                const cardNat = document.getElementById('cardModeNational');
                const cardUni = document.getElementById('cardModeUniversity');
                if (data.mode === 'university') {
                    cardUni.classList.add('ring-2', 'ring-emerald-500', 'border-emerald-500', 'bg-emerald-50/20');
                    cardNat.classList.remove('ring-2', 'ring-blue-500', 'border-blue-500', 'bg-blue-50/20');
                } else {
                    cardNat.classList.add('ring-2', 'ring-blue-500', 'border-blue-500', 'bg-blue-50/20');
                    cardUni.classList.remove('ring-2', 'ring-emerald-500', 'border-emerald-500', 'bg-emerald-50/20');
                }

                loadCensusVoters();
                loadCandidates();
            } catch (err) {
                console.error("Error al cargar modo:", err);
            }
        }

        async function switchElectionMode(newMode) {
            if (newMode === currentMode) {
                showToast(`El modo ${newMode.toUpperCase()} ya está activo.`, 'info');
                return;
            }
            if (!confirm(`¿Cambiar a modo ${newMode.toUpperCase()}? Los votos de cada modalidad se conservan por separado y la urna se abrirá para la modalidad seleccionada.`)) {
                return;
            }
            try {
                const res = await apiFetch('/api/election/switch-mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mode: newMode })
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(`Modo electoral actualizado: ${data.election_title}`, 'success');
                    loadElectionMode();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'Error al conmutar modo electoral.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al cambiar modo.', 'error');
            }
        }

        async function toggleUrna() {
            if (isTallied) {
                showToast('La jornada ya fue escrutada. Usa Reiniciar jornada para volver a abrir la urna.', 'info');
                return;
            }
            const endpoint = isUrnaOpen ? '/api/election/close' : '/api/election/open';
            try {
                const res = await apiFetch(endpoint, { method: 'POST' });
                if (res.ok) {
                    loadElectionMode();
                    loadAuditLogs();
                } else {
                    const err = await res.json();
                    showToast(err.detail || 'Error al alterar estado de urna.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión con el servidor.', 'error');
            }
        }

        async function resetElection() {
            if (!confirm("¿Reiniciar la jornada? Se borrarán TODOS los votos y participaciones de la elección activa. El censo se conserva.")) {
                return;
            }
            const confirmation = prompt('Escribe REINICIAR para confirmar:');
            if (confirmation !== 'REINICIAR') {
                return;
            }
            try {
                const res = await apiFetch('/api/admin/reset-election', { method: 'POST' });
                const data = await res.json();
                if (res.ok) {
                    showToast(`Jornada reiniciada. Papeletas eliminadas: ${data.removed_ballots}. Queda en borrador: abre la urna para votar.`, 'success');
                    loadElectionMode();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'No fue posible reiniciar la jornada.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al reiniciar la jornada.', 'error');
            }
        }

        async function generateOfficialTally() {
            if (!confirm("¿Cerrar la urna y generar el acta? Después de esto la jornada queda escrutada y no se puede reabrir sin reiniciarla.")) {
                return;
            }
            try {
                const res = await apiFetch('/api/tally/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        officer_signatures: ["JURADO-PRESIDENTE-TOKEN-991", "JURADO-VOCAL-TOKEN-882"]
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    const container = document.getElementById('tallyReportContainer');
                    const pre = document.getElementById('tallyFormattedSummary');
                    pre.innerText = data.formatted_summary;
                    container.classList.remove('hidden');
                    container.scrollIntoView({ behavior: 'smooth' });
                    loadElectionMode();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'Error al generar acta oficial.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al generar acta.', 'error');
            }
        }

        async function loadCandidates() {
            try {
                const res = await apiFetch('/api/admin/candidates');
                if (!res.ok) return;
                candidateCache = await res.json();
                const tbody = document.getElementById('candidateTableBody');
                if (!candidateCache.length) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-6 text-slate-400">No hay candidatos registrados.</td></tr>`;
                    return;
                }
                tbody.innerHTML = candidateCache.map(c => {
                    const badgeClass = c.is_active
                        ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                        : 'text-slate-600 bg-slate-100 border border-slate-200';
                    const actionClass = c.is_active
                        ? 'text-rose-600 hover:bg-rose-50 border-rose-200'
                        : 'text-emerald-600 hover:bg-emerald-50 border-emerald-200';
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="py-2.5 px-3 font-mono font-semibold text-slate-900">${escapeHtml(c.candidate_id)}</td>
                            <td class="py-2.5 px-3 text-slate-700">${escapeHtml(c.candidate_name)}</td>
                            <td class="py-2.5 px-3 text-slate-500">${escapeHtml(c.party_name)}</td>
                            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}">${c.is_active ? 'Activo' : 'Inactivo'}</span></td>
                            <td class="py-2.5 px-3 text-right whitespace-nowrap">
                                <button type="button" class="btn-edit-candidate text-[11px] font-semibold border px-2.5 py-1 rounded-lg transition text-indigo-600 hover:bg-indigo-50 border-indigo-200 mr-1" data-id="${escapeHtml(c.candidate_id)}">Editar</button>
                                <button type="button" class="btn-toggle-candidate text-[11px] font-semibold border px-2.5 py-1 rounded-lg transition ${actionClass}" data-id="${escapeHtml(c.candidate_id)}" data-active="${c.is_active}">${c.is_active ? 'Desactivar' : 'Activar'}</button>
                            </td>
                        </tr>
                    `;
                }).join('');

                tbody.querySelectorAll('.btn-edit-candidate').forEach(button => {
                    button.addEventListener('click', () => editCandidate(button.dataset.id));
                });
                tbody.querySelectorAll('.btn-toggle-candidate').forEach(button => {
                    button.addEventListener('click', () => toggleCandidateStatus(button.dataset.id, button.dataset.active !== 'true'));
                });
            } catch (err) {
                console.error("Error al cargar candidatos:", err);
            }
        }

        function resetCandidateForm() {
            editingCandidateId = null;
            document.getElementById('candidateFormTitle').innerText = 'Registrar candidato';
            const idInput = document.getElementById('candidateId');
            idInput.disabled = false;
            idInput.value = '';
            document.getElementById('candidateName').value = '';
            document.getElementById('candidateParty').value = '';
            document.getElementById('candidateSlogan').value = '';
            document.getElementById('candidateColor').value = '#2563EB';
            document.getElementById('candidateOrder').value = '0';
        }

        function editCandidate(candidateId) {
            const candidate = candidateCache.find(c => c.candidate_id === candidateId);
            if (!candidate) return;
            editingCandidateId = candidateId;
            document.getElementById('candidateFormTitle').innerText = `Editar ${candidateId}`;
            const idInput = document.getElementById('candidateId');
            idInput.value = candidateId;
            idInput.disabled = true;
            document.getElementById('candidateName').value = candidate.candidate_name;
            document.getElementById('candidateParty').value = candidate.party_name;
            document.getElementById('candidateSlogan').value = candidate.campaign_slogan || '';
            document.getElementById('candidateColor').value = candidate.party_color_hex || '#2563EB';
            document.getElementById('candidateOrder').value = candidate.display_order || 0;
        }

        async function handleCandidateSubmit(event) {
            event.preventDefault();
            const payload = {
                candidate_name: document.getElementById('candidateName').value.trim(),
                party_name: document.getElementById('candidateParty').value.trim(),
                campaign_slogan: document.getElementById('candidateSlogan').value.trim(),
                party_color_hex: document.getElementById('candidateColor').value,
                display_order: Number(document.getElementById('candidateOrder').value || 0),
            };
            const candidateId = document.getElementById('candidateId').value.trim();
            const isEditing = Boolean(editingCandidateId);
            if (!isEditing) payload.candidate_id = candidateId;
            if (isEditing) {
                const current = candidateCache.find(c => c.candidate_id === editingCandidateId);
                payload.photo_url = current ? current.photo_url : '/static/candidates/default.svg';
            }
            try {
                const url = isEditing
                    ? `/api/admin/candidates/${encodeURIComponent(editingCandidateId)}`
                    : '/api/admin/candidates';
                const res = await apiFetch(url, {
                    method: isEditing ? 'PUT' : 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload),
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(isEditing ? 'Candidato actualizado.' : 'Candidato registrado.', 'success');
                    resetCandidateForm();
                    loadCandidates();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'No fue posible guardar el candidato.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al guardar el candidato.', 'error');
            }
        }

        async function toggleCandidateStatus(candidateId, isActive) {
            try {
                const res = await apiFetch(`/api/admin/candidates/${encodeURIComponent(candidateId)}/status`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ is_active: isActive }),
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(`Candidato ${isActive ? 'activado' : 'desactivado'}.`, 'success');
                    loadCandidates();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'No fue posible cambiar el estado.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al cambiar el estado.', 'error');
            }
        }

        async function loadCensusVoters() {
            try {
                const res = await apiFetch(`/api/census/voters?election_type=${encodeURIComponent(currentMode)}`);
                const voters = await res.json();
                const tbody = document.getElementById('censusTableBody');

                if (!voters || voters.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-6 text-slate-400">No hay electores registrados en este censo.</td></tr>`;
                    return;
                }

                tbody.innerHTML = voters.map(v => {
                    const badgeClass = v.is_eligible
                        ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                        : 'text-rose-700 bg-rose-50 border border-rose-200';
                    const badgeText = v.is_eligible ? 'Habilitado' : 'Inhabilitado';
                    const btnClass = v.is_eligible
                        ? 'text-rose-600 hover:bg-rose-50 border-rose-200'
                        : 'text-emerald-600 hover:bg-emerald-50 border-emerald-200';
                    const btnText = v.is_eligible ? 'Inhabilitar' : 'Habilitar';
                    const targetStatus = !v.is_eligible;
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="py-2.5 px-3 font-mono font-semibold text-slate-900">${escapeHtml(v.document_id)}</td>
                            <td class="py-2.5 px-3 text-slate-700">${escapeHtml(v.full_name)}</td>
                            <td class="py-2.5 px-3 text-slate-500">${escapeHtml(v.assigned_station_id)}</td>
                            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}">${badgeText}</span></td>
                            <td class="py-2.5 px-3 text-right">
                                <button type="button"
                                    class="btn-toggle-status text-[11px] font-semibold border px-2.5 py-1 rounded-lg transition ${btnClass}"
                                    data-doc="${escapeHtml(v.document_id)}"
                                    data-status="${targetStatus}">
                                    ${btnText}
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');

                tbody.querySelectorAll('.btn-toggle-status').forEach((button) => {
                    button.addEventListener('click', () => {
                        toggleVoterStatus(button.dataset.doc, button.dataset.status === 'true');
                    });
                });
            } catch (err) {
                console.error("Error al cargar censo:", err);
            }
        }

        async function handleRegisterVoter(e) {
            e.preventDefault();
            const docId = document.getElementById('censusDocId').value.trim();
            const fullName = document.getElementById('censusFullName').value.trim();
            const station = document.getElementById('censusStation').value.trim();
            const pin = document.getElementById('censusPin').value.trim();
            const eligible = document.getElementById('censusEligible').value === 'true';

            try {
                const res = await apiFetch('/api/census/voters', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        document_id: docId,
                        full_name: fullName,
                        assigned_station_id: station,
                        is_eligible: eligible,
                        pin: pin,
                        election_type: currentMode.toUpperCase()
                    })
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(`Elector ${fullName} (${docId}) registrado. PIN: ${pin}`, 'success');
                    document.getElementById('censusDocId').value = '';
                    document.getElementById('censusFullName').value = '';
                    document.getElementById('censusPin').value = '1234';
                    loadCensusVoters();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'Error al inscribir elector.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al inscribir elector.', 'error');
            }
        }

        async function toggleVoterStatus(docId, newStatus) {
            try {
                const res = await apiFetch(`/api/census/voters/${encodeURIComponent(docId)}/status`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ is_eligible: newStatus })
                });
                const data = await res.json();
                if (res.ok) {
                    loadCensusVoters();
                    loadAuditLogs();
                } else {
                    showToast(data.detail || 'Error al modificar estado.', 'error');
                }
            } catch (err) {
                showToast('Error de conexión al modificar estado.', 'error');
            }
        }

        async function loadAuditLogs() {
            try {
                const res = await apiFetch('/api/security/audit-log');
                const logs = await res.json();
                const tbody = document.getElementById('auditTableBody');

                if (!logs || logs.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">Sin eventos auditados aún.</td></tr>`;
                    return;
                }

                tbody.innerHTML = logs.slice().reverse().map(l => {
                    const badgeColor = l.status === 'AUTORIZADO' || l.status === 'EXITOSO' || l.status === 'CONCLUIDO'
                        ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                        : (l.status === 'RECHAZADO' || l.status === 'FALLIDO' ? 'text-rose-700 bg-rose-50 border border-rose-200' : 'text-blue-700 bg-blue-50 border border-blue-200');
                    const time = String(l.timestamp || '').split('T')[1]?.slice(0, 8) || '';
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="py-2.5 px-3 text-slate-400">${escapeHtml(time)}</td>
                            <td class="py-2.5 px-3 font-semibold text-slate-800">${escapeHtml(l.action)}</td>
                            <td class="py-2.5 px-3">${escapeHtml(l.user_id)}</td>
                            <td class="py-2.5 px-3 text-slate-500">${escapeHtml(l.role)}</td>
                            <td class="py-2.5 px-3"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor}">${escapeHtml(l.status)}</span></td>
                            <td class="py-2.5 px-3 text-slate-500 truncate max-w-xs" title="${escapeHtml(l.details)}">${escapeHtml(l.details)}</td>
                        </tr>
                    `;
                }).join('');
            } catch (err) {
                console.error("Error al cargar auditoría:", err);
            }
        }
