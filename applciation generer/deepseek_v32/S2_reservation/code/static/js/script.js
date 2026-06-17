// Gestion des créneaux horaires
document.addEventListener('DOMContentLoaded', function() {
    // Sélection de date pour la réservation
    const dateInput = document.getElementById('date');
    const roomIdInput = document.getElementById('room_id');
    const timeSlotsContainer = document.getElementById('time-slots');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    
    if (dateInput && roomIdInput && timeSlotsContainer) {
        dateInput.addEventListener('change', loadAvailableSlots);
        
        function loadAvailableSlots() {
            const date = dateInput.value;
            const roomId = roomIdInput.value;
            
            if (!date || !roomId) return;
            
            fetch(`/api/available_slots?room_id=${roomId}&date=${date}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        timeSlotsContainer.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                        return;
                    }
                    
                    if (data.slots.length === 0) {
                        timeSlotsContainer.innerHTML = '<div class="alert alert-warning">Aucun créneau disponible pour cette date</div>';
                        return;
                    }
                    
                    let html = '<div class="time-slots">';
                    data.slots.forEach(slot => {
                        html += `
                            <div class="time-slot" data-start="${slot.start}" data-end="${slot.end}">
                                ${slot.display}
                            </div>
                        `;
                    });
                    html += '</div>';
                    
                    timeSlotsContainer.innerHTML = html;
                    
                    // Ajouter les événements de clic sur les créneaux
                    document.querySelectorAll('.time-slot').forEach(slot => {
                        slot.addEventListener('click', function() {
                            // Désélectionner tous les créneaux
                            document.querySelectorAll('.time-slot').forEach(s => {
                                s.classList.remove('selected');
                            });
                            
                            // Sélectionner le créneau cliqué
                            this.classList.add('selected');
                            
                            // Remplir les champs cachés
                            startTimeInput.value = this.dataset.start;
                            endTimeInput.value = this.dataset.end;
                        });
                    });
                })
                .catch(error => {
                    console.error('Erreur:', error);
                    timeSlotsContainer.innerHTML = '<div class="alert alert-danger">Erreur de chargement des créneaux</div>';
                });
        }
        
        // Charger les créneaux si une date est déjà sélectionnée
        if (dateInput.value) {
            loadAvailableSlots();
        }
    }
    
    // Confirmation de suppression
    const cancelButtons = document.querySelectorAll('.cancel-booking');
    cancelButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Êtes-vous sûr de vouloir annuler cette réservation ?')) {
                e.preventDefault();
            }
        });
    });
    
    // Confirmation de désactivation de salle
    const toggleRoomButtons = document.querySelectorAll('.toggle-room');
    toggleRoomButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const action = this.dataset.action;
            if (!confirm(`Êtes-vous sûr de vouloir ${action} cette salle ?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Formatage des dates
    const dateElements = document.querySelectorAll('.format-date');
    dateElements.forEach(element => {
        const date = new Date(element.textContent);
        element.textContent = date.toLocaleDateString('fr-FR', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    });
});
