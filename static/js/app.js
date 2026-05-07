/* ===== BARBERÍA APP JS ===== */

// ---- Booking Flow ----

let selectedBarber = null;
let selectedService = null;
let selectedDate = null;
let selectedSlot = null;

function initBookingFlow() {
  // Step 1: Barber + Service selection
  document.querySelectorAll('.barber-select-card').forEach(function(card) {
    card.addEventListener('click', function() {
      document.querySelectorAll('.barber-select-card').forEach(function(c) {
        c.classList.remove('selected');
      });
      card.classList.add('selected');
      var radio = card.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        selectedBarber = radio.value;
      }
      updateContinueBtn();
    });
  });

  document.querySelectorAll('.service-select-card').forEach(function(card) {
    card.addEventListener('click', function() {
      document.querySelectorAll('.service-select-card').forEach(function(c) {
        c.classList.remove('selected');
      });
      card.classList.add('selected');
      var radio = card.querySelector('input[type="radio"]');
      if (radio) {
        radio.checked = true;
        selectedService = radio.value;
      }
      updateContinueBtn();
    });
  });

  // Step 2: Date/time
  var dateInput = document.getElementById('date-picker');
  if (dateInput) {
    dateInput.addEventListener('change', function() {
      selectedDate = dateInput.value;
      selectedSlot = null;
      loadAvailableSlots();
    });
  }

  // Set today as default date
  if (dateInput && !dateInput.value) {
    var today = new Date();
    var yyyy = today.getFullYear();
    var mm = String(today.getMonth() + 1).padStart(2, '0');
    var dd = String(today.getDate()).padStart(2, '0');
    dateInput.value = yyyy + '-' + mm + '-' + dd;
    selectedDate = dateInput.value;
    // Load slots if barber already selected (step 2)
    var barberInput = document.getElementById('step2-barber-id');
    if (barberInput && barberInput.value) {
      selectedBarber = barberInput.value;
      loadAvailableSlots();
    }
  }
}

function updateContinueBtn() {
  var btn = document.getElementById('step1-continue');
  if (btn) {
    var hasBarber = document.querySelector('.barber-select-card.selected') !== null ||
                    document.getElementById('step2-barber-id') !== null;
    var hasService = document.querySelector('.service-select-card.selected') !== null;
    btn.disabled = !(hasBarber && hasService);
  }
}

function loadAvailableSlots() {
  var barberId = selectedBarber;
  var barberInput = document.getElementById('step2-barber-id');
  if (!barberId && barberInput) {
    barberId = barberInput.value;
  }
  var dateVal = selectedDate;
  var dateInput = document.getElementById('date-picker');
  if (!dateVal && dateInput) {
    dateVal = dateInput.value;
  }

  if (!barberId || !dateVal) return;

  var slotsContainer = document.getElementById('slots-container');
  var slotsGrid = document.getElementById('slots-grid');
  if (!slotsGrid) return;

  slotsGrid.innerHTML = '<p style="color:#888;font-size:13px;padding:8px 0;">Cargando horarios...</p>';
  if (slotsContainer) slotsContainer.style.display = 'block';

  fetch('/api/available-slots?barber_id=' + barberId + '&date=' + dateVal)
    .then(function(res) { return res.json(); })
    .then(function(data) {
      slotsGrid.innerHTML = '';
      if (!data.slots || data.slots.length === 0) {
        slotsGrid.innerHTML = '<p style="color:#888;font-size:13px;">No hay horarios disponibles para esta fecha.</p>';
        return;
      }
      data.slots.forEach(function(slot) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'slot-btn';
        btn.textContent = slot;
        btn.addEventListener('click', function() {
          document.querySelectorAll('.slot-btn').forEach(function(b) {
            b.classList.remove('selected');
          });
          btn.classList.add('selected');
          selectedSlot = slot;
          var hiddenSlot = document.getElementById('selected-slot-input');
          if (hiddenSlot) hiddenSlot.value = slot;
          updateStep2Btn();
        });
        slotsGrid.appendChild(btn);
      });
    })
    .catch(function(err) {
      slotsGrid.innerHTML = '<p style="color:#E8302A;font-size:13px;">Error al cargar horarios. Intentá de nuevo.</p>';
    });
}

function updateStep2Btn() {
  var btn = document.getElementById('step2-continue');
  if (btn) {
    btn.disabled = !selectedSlot;
  }
}

// ---- Reschedule Toggle ----

function toggleReschedule(apptId) {
  var form = document.getElementById('reschedule-' + apptId);
  if (form) {
    form.classList.toggle('visible');
  }
}

// ---- Flash message auto-dismiss ----

function initFlashMessages() {
  var alerts = document.querySelectorAll('.alert');
  alerts.forEach(function(alert) {
    setTimeout(function() {
      alert.style.transition = 'opacity 0.5s';
      alert.style.opacity = '0';
      setTimeout(function() {
        alert.remove();
      }, 500);
    }, 4000);
  });
}

// ---- Service modal for barber/services ----

function openServiceModal(mode, data) {
  var modal = document.getElementById('service-modal');
  if (!modal) return;

  var form = modal.querySelector('form');
  var title = modal.querySelector('.modal-title');

  if (mode === 'create') {
    title.textContent = 'Nuevo Servicio';
    form.action.value = 'create';
    form.querySelector('[name="service_id"]') && (form.querySelector('[name="service_id"]').value = '');
    form.querySelector('[name="name"]').value = '';
    form.querySelector('[name="duration_minutes"]').value = '30';
    form.querySelector('[name="price"]').value = '';
    form.querySelector('[name="description"]').value = '';
  } else if (mode === 'edit' && data) {
    title.textContent = 'Editar Servicio';
    form.querySelector('[name="action"]').value = 'edit';
    form.querySelector('[name="service_id"]').value = data.id;
    form.querySelector('[name="name"]').value = data.name;
    form.querySelector('[name="duration_minutes"]').value = data.duration;
    form.querySelector('[name="price"]').value = data.price;
    form.querySelector('[name="description"]').value = data.description;
  }

  modal.style.display = 'flex';
}

function closeServiceModal() {
  var modal = document.getElementById('service-modal');
  if (modal) modal.style.display = 'none';
}

// ---- Block modal ----

function openBlockModal() {
  var modal = document.getElementById('block-modal');
  if (modal) modal.style.display = 'flex';
}

function closeBlockModal() {
  var modal = document.getElementById('block-modal');
  if (modal) modal.style.display = 'none';
}

// ---- Close modals on overlay click ----

function initModals() {
  document.querySelectorAll('.modal-overlay').forEach(function(overlay) {
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) {
        overlay.style.display = 'none';
      }
    });
  });
}

// ---- Delete service confirm ----

function confirmDeleteService(serviceId, serviceName) {
  if (confirm('¿Eliminar el servicio "' + serviceName + '"? Esta acción no se puede deshacer.')) {
    var form = document.getElementById('delete-service-form-' + serviceId);
    if (form) form.submit();
  }
}

// ---- Complete appointment ----

function confirmComplete(apptId) {
  if (confirm('¿Marcar este turno como completado?')) {
    var form = document.getElementById('complete-form-' + apptId);
    if (form) form.submit();
  }
}

// ---- Step navigation for booking ----

function goToStep(stepNum, formData) {
  // Build URL for step navigation
  var url = '/client/book?step=' + stepNum;
  if (formData) {
    url += '&' + new URLSearchParams(formData).toString();
  }
  window.location.href = url;
}

// ---- Init ----

document.addEventListener('DOMContentLoaded', function() {
  initFlashMessages();
  initBookingFlow();
  initModals();

  // Auto-load slots on step 2
  var step2BarberInput = document.getElementById('step2-barber-id');
  var datePicker = document.getElementById('date-picker');
  if (step2BarberInput && datePicker) {
    selectedBarber = step2BarberInput.value;
    if (datePicker.value) {
      selectedDate = datePicker.value;
      loadAvailableSlots();
    }
  }
});
