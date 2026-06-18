// Global State
let donors = [];
let filteredDonors = [];
let sentBirthdayCards = new Set();
let currentPage = 1;
const pageSize = 10;

let selectedBirthdayTab = 'today'; // 'today' or 'month'
let selectedBirthdayDonorId = null;

// Charts instances (to destroy before recreating)
let interestChartInstance = null;
let ageChartInstance = null;
let paymentChartInstance = null;

// Target Dates (Current date in context is 2026-06-18)
const CURRENT_DATE_OBJ = new Date('2026-06-18');
const CURRENT_MONTH = 6; // June
const CURRENT_DAY = 18;

// DOM Elements
const currentDateEl = document.getElementById('current-date');
const kpiTotalDonorsEl = document.getElementById('kpi-total-donors');
const kpiActiveRegularEl = document.getElementById('kpi-active-regular');
const kpiTotalAmountEl = document.getElementById('kpi-total-amount');
const kpiAvgAmountEl = document.getElementById('kpi-avg-amount');

const searchInput = document.getElementById('search-input');
const filterType = document.getElementById('filter-type');
const filterStatus = document.getElementById('filter-status');
const filterInterest = document.getElementById('filter-interest');
const resetFiltersBtn = document.getElementById('reset-filters');

const donorTableBody = document.getElementById('donor-table-body');
const filteredCountEl = document.getElementById('filtered-count');
const pageRangeEl = document.getElementById('page-range');
const prevPageBtn = document.getElementById('prev-page-btn');
const nextPageBtn = document.getElementById('next-page-btn');
const pageNumbersEl = document.getElementById('page-numbers');

const todayCountEl = document.getElementById('today-count');
const monthCountEl = document.getElementById('month-count');
const birthdayListEl = document.getElementById('birthday-list');
const messageTemplateSelect = document.getElementById('message-template');
const previewToEl = document.getElementById('preview-to');
const previewBodyEl = document.getElementById('preview-body');
const sendAllBtn = document.getElementById('send-all-btn');
const toastContainer = document.getElementById('toast-container');

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Set current date UI
  currentDateEl.textContent = CURRENT_DATE_OBJ.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  });
  
  loadData();
  setupEventListeners();
});

// Load Data from donors.json
async function loadData() {
  try {
    const response = await fetch('./donors.json');
    if (!response.ok) {
      throw new Error('데이터 파일을 불러오는 데 실패했습니다.');
    }
    donors = await response.json();
    filteredDonors = [...donors];
    
    updateKPIs();
    initCharts();
    renderBirthdaySection();
    renderDonorTable();
  } catch (error) {
    console.error('Data loading error:', error);
    showToast('데이터를 불러오는 중 오류가 발생했습니다.', 'error');
  }
}

// Setup Event Listeners
function setupEventListeners() {
  // Filters
  searchInput.addEventListener('input', () => { currentPage = 1; filterData(); });
  filterType.addEventListener('change', () => { currentPage = 1; filterData(); });
  filterStatus.addEventListener('change', () => { currentPage = 1; filterData(); });
  filterInterest.addEventListener('change', () => { currentPage = 1; filterData(); });
  resetFiltersBtn.addEventListener('click', resetFilters);
  
  // Pagination
  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderDonorTable();
    }
  });
  
  nextPageBtn.addEventListener('click', () => {
    const maxPage = Math.ceil(filteredDonors.length / pageSize);
    if (currentPage < maxPage) {
      currentPage++;
      renderDonorTable();
    }
  });

  // Birthday Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      selectedBirthdayTab = e.target.getAttribute('data-tab');
      selectedBirthdayDonorId = null;
      renderBirthdaySection();
    });
  });

  // Template change
  messageTemplateSelect.addEventListener('change', updateCardPreview);

  // Send Birthday Cards
  sendAllBtn.addEventListener('click', sendAllBirthdayCards);

  // Sidebar navigation scroll effect
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      
      const targetId = item.getAttribute('data-target');
      if (targetId === 'dashboard') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
  });
}

// Update KPI Metrics
function updateKPIs() {
  // 1. Total Donors
  kpiTotalDonorsEl.textContent = `${donors.length.toLocaleString()}명`;
  
  // 2. Active Regular Donors
  const activeRegular = donors.filter(d => d.donation_type === '정기후원' && d.status === '활성');
  kpiActiveRegularEl.textContent = `${activeRegular.length.toLocaleString()}명`;
  
  // 3. Total Monthly Amount
  // 정기후원 활성인 건들의 금액 합계 + 당월(2026년 6월)에 신규 가입하여 후원 완료된 일시후원금 합산
  const regularSum = activeRegular.reduce((sum, d) => sum + d.donation_amount, 0);
  
  const currentYearMonth = '2026-06';
  const oneTimeMonthly = donors.filter(d => 
    d.donation_type === '일시후원' && 
    d.join_date.startsWith(currentYearMonth) && 
    d.status === '완료'
  );
  const oneTimeSum = oneTimeMonthly.reduce((sum, d) => sum + d.donation_amount, 0);
  
  const totalMonthlyAmount = regularSum + oneTimeSum;
  kpiTotalAmountEl.textContent = `${totalMonthlyAmount.toLocaleString()}원`;
  
  // 4. Average Donation Amount
  const totalAmountSum = donors.reduce((sum, d) => sum + d.donation_amount, 0);
  const avgAmount = Math.round(totalAmountSum / donors.length);
  kpiAvgAmountEl.textContent = `${avgAmount.toLocaleString()}원`;
}

// Chart.js Implementations
function initCharts() {
  // Colors Palette
  const colors = {
    cream: '#fff4e4',
    cocoa: '#6d402c',
    terracotta: '#d96f4c',
    clay: '#e8a174',
    sage: '#679e76',
    rose: '#d97889',
    lavender: '#b883b8',
    blue: '#7ba7bd'
  };

  // Destroy previous charts if exist
  if (interestChartInstance) interestChartInstance.destroy();
  if (ageChartInstance) ageChartInstance.destroy();
  if (paymentChartInstance) paymentChartInstance.destroy();

  // 1. Interest Area Chart
  const interestData = {};
  donors.forEach(d => {
    interestData[d.interest_area] = (interestData[d.interest_area] || 0) + 1;
  });
  
  const interestCtx = document.getElementById('interestChart').getContext('2d');
  interestChartInstance = new Chart(interestCtx, {
    type: 'doughnut',
    data: {
      labels: Object.keys(interestData),
      datasets: [{
        data: Object.values(interestData),
        backgroundColor: [colors.terracotta, colors.clay, colors.sage, colors.rose, colors.lavender, colors.blue],
        borderColor: '#fff4e4',
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#6d402c', font: { family: 'Nunito Sans, Noto Sans KR, sans-serif', weight: '800' } }
        }
      }
    }
  });

  // 2. Age Range Chart
  const ageRanges = { '20대': 0, '30대': 0, '40대': 0, '50대': 0, '60대': 0, '70대 이상': 0 };
  donors.forEach(d => {
    const birthYear = parseInt(d.birthday.split('-')[0]);
    const age = 2026 - birthYear; // Based on local year 2026
    
    if (age >= 20 && age < 30) ageRanges['20대']++;
    else if (age >= 30 && age < 40) ageRanges['30대']++;
    else if (age >= 40 && age < 50) ageRanges['40대']++;
    else if (age >= 50 && age < 60) ageRanges['50대']++;
    else if (age >= 60 && age < 70) ageRanges['60대']++;
    else if (age >= 70) ageRanges['70대 이상']++;
  });

  const ageCtx = document.getElementById('ageChart').getContext('2d');
  ageChartInstance = new Chart(ageCtx, {
    type: 'bar',
    data: {
      labels: Object.keys(ageRanges),
      datasets: [{
        label: '인원수 (명)',
        data: Object.values(ageRanges),
        backgroundColor: colors.clay,
        borderColor: colors.cream,
        borderRadius: 14,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8f6954', font: { weight: '800' } } },
        y: { grid: { color: 'rgba(122, 72, 43, 0.12)' }, ticks: { color: '#8f6954', font: { weight: '800' } } }
      }
    }
  });

  // 3. Payment Method Chart
  const paymentData = {};
  donors.forEach(d => {
    paymentData[d.payment_method] = (paymentData[d.payment_method] || 0) + 1;
  });

  const paymentCtx = document.getElementById('paymentChart').getContext('2d');
  paymentChartInstance = new Chart(paymentCtx, {
    type: 'pie',
    data: {
      labels: Object.keys(paymentData),
      datasets: [{
        data: Object.values(paymentData),
        backgroundColor: [colors.terracotta, colors.sage, colors.lavender],
        borderColor: '#fff4e4',
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#6d402c', font: { family: 'Nunito Sans, Noto Sans KR, sans-serif', weight: '800' } }
        }
      }
    }
  });
}

// Filter Logic
function filterData() {
  const query = searchInput.value.toLowerCase().trim();
  const typeValue = filterType.value;
  const statusValue = filterStatus.value;
  const interestValue = filterInterest.value;
  
  filteredDonors = donors.filter(d => {
    // 1. Search Query
    const matchQuery = !query || 
      d.name.toLowerCase().includes(query) ||
      d.phone.includes(query) ||
      d.email.toLowerCase().includes(query);
      
    // 2. Donation Type Filter
    const matchType = !typeValue || d.donation_type === typeValue;
    
    // 3. Status Filter
    const matchStatus = !statusValue || d.status === statusValue;
    
    // 4. Interest Area Filter
    const matchInterest = !interestValue || d.interest_area === interestValue;
    
    return matchQuery && matchType && matchStatus && matchInterest;
  });
  
  renderDonorTable();
}

// Reset Filter Inputs
function resetFilters() {
  searchInput.value = '';
  filterType.value = '';
  filterStatus.value = '';
  filterInterest.value = '';
  currentPage = 1;
  filterData();
  showToast('필터가 초기화되었습니다.', 'info');
}

// Render Table
function renderDonorTable() {
  donorTableBody.innerHTML = '';
  filteredCountEl.textContent = filteredDonors.length;
  
  if (filteredDonors.length === 0) {
    donorTableBody.innerHTML = `<tr><td colspan="11" class="empty-state" style="border: none;">검색 조건에 맞는 후원자가 없습니다.</td></tr>`;
    pageRangeEl.textContent = '0-0';
    updatePaginationControls(0);
    return;
  }
  
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, filteredDonors.length);
  pageRangeEl.textContent = `${startIndex + 1}-${endIndex}`;
  
  const pageItems = filteredDonors.slice(startIndex, endIndex);
  
  pageItems.forEach(d => {
    const tr = document.createElement('tr');
    
    let typeClass = d.donation_type === '정기후원' ? 'regular' : 'onetime';
    let statusClass = 'stopped';
    if (d.status === '활성') statusClass = 'active';
    else if (d.status === '완료') statusClass = 'completed';
    
    tr.innerHTML = `
      <td><strong>${d.donor_id}</strong></td>
      <td>${d.name}</td>
      <td>${d.birthday}</td>
      <td>${d.phone}</td>
      <td>${d.email}</td>
      <td><span class="badge-type ${typeClass}">${d.donation_type}</span></td>
      <td>${d.donation_amount.toLocaleString()}원</td>
      <td>${d.payment_method}</td>
      <td>${d.join_date}</td>
      <td><span class="badge-status ${statusClass}">${d.status}</span></td>
      <td>${d.interest_area}</td>
    `;
    donorTableBody.appendChild(tr);
  });
  
  updatePaginationControls(filteredDonors.length);
}

// Update Pagination Bar Controls
function updatePaginationControls(totalCount) {
  const maxPage = Math.ceil(totalCount / pageSize);
  pageNumbersEl.innerHTML = '';
  
  prevPageBtn.disabled = currentPage === 1;
  nextPageBtn.disabled = currentPage === maxPage || maxPage === 0;
  
  // Show page numbers
  for (let i = 1; i <= maxPage; i++) {
    const span = document.createElement('span');
    span.textContent = i;
    span.className = `page-num ${i === currentPage ? 'active' : ''}`;
    span.addEventListener('click', () => {
      currentPage = i;
      renderDonorTable();
    });
    pageNumbersEl.appendChild(span);
  }
}

// Birthday Logic & Render
function getBirthdayDonors() {
  const todayDonors = [];
  const monthDonors = [];
  
  donors.forEach(d => {
    const parts = d.birthday.split('-');
    const month = parseInt(parts[1]);
    const day = parseInt(parts[2]);
    
    if (month === CURRENT_MONTH) {
      monthDonors.push(d);
      if (day === CURRENT_DAY) {
        todayDonors.push(d);
      }
    }
  });
  
  return { today: todayDonors, month: monthDonors };
}

function renderBirthdaySection() {
  const { today, month } = getBirthdayDonors();
  
  todayCountEl.textContent = today.length;
  monthCountEl.textContent = month.length;
  
  const currentList = selectedBirthdayTab === 'today' ? today : month;
  birthdayListEl.innerHTML = '';
  
  if (currentList.length === 0) {
    birthdayListEl.innerHTML = `<div class="empty-state">생일 축하 대상자가 없습니다.</div>`;
    sendAllBtn.disabled = true;
    clearCardPreview();
    return;
  }
  
  sendAllBtn.disabled = false;
  
  // Set default selected donor if none is set
  if (!selectedBirthdayDonorId || !currentList.find(d => d.donor_id === selectedBirthdayDonorId)) {
    selectedBirthdayDonorId = currentList[0].donor_id;
  }
  
  currentList.forEach(d => {
    const isSent = sentBirthdayCards.has(d.donor_id);
    const parts = d.birthday.split('-');
    const day = parts[2];
    
    const div = document.createElement('div');
    div.className = `birthday-item ${d.donor_id === selectedBirthdayDonorId ? 'selected' : ''}`;
    
    // Calculate Age
    const birthYear = parseInt(parts[0]);
    const age = 2026 - birthYear;
    
    div.innerHTML = `
      <div class="birthday-info">
        <div class="avatar">${d.name[0]}</div>
        <div class="birthday-details">
          <h4>${d.name}<span class="badge">${age}세</span></h4>
          <p><i data-lucide="cake" style="width:12px;height:12px;"></i> ${parts[1]}월 ${parts[2]}일생</p>
        </div>
      </div>
      <div class="birthday-item-action">
        <span class="birth-badge-status ${isSent ? 'sent' : 'unsent'}">
          <i data-lucide="${isSent ? 'check-circle' : 'circle-ellipsis'}" style="width:14px;height:14px;"></i>
          ${isSent ? '발송완료' : '미발송'}
        </span>
        ${!isSent ? `<button class="btn btn-emerald btn-sm single-send-btn" data-id="${d.donor_id}">발송</button>` : ''}
      </div>
    `;
    
    // Item Click to select
    div.addEventListener('click', (e) => {
      if (e.target.classList.contains('single-send-btn')) return; // Avoid triggering select when clicking button
      selectedBirthdayDonorId = d.donor_id;
      
      // Update UI selection
      document.querySelectorAll('.birthday-item').forEach(el => el.classList.remove('selected'));
      div.classList.add('selected');
      
      updateCardPreview();
    });
    
    birthdayListEl.appendChild(div);
  });
  
  // Bind single send button events
  document.querySelectorAll('.single-send-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = btn.getAttribute('data-id');
      sendBirthdayCard(id);
    });
  });
  
  lucide.createIcons();
  updateCardPreview();
}

// Card Message Preview Logic
const messageTemplates = {
  '1': (name) => `${name} 후원자님께\n\n후원자님의 따뜻한 동행 덕분에 세상이 더욱 밝아집니다. 뜻깊은 생일을 진심으로 축하드리며, 오늘 하루 행복이 가득하시기를 바랍니다.\n\n- 행복복지재단 임직원 일동 -`,
  '2': (name) => `${name} 후원자님께\n\n나눔을 실천해 주시는 아름다운 마음이 바로 오늘의 주인공입니다. 후원자님의 특별한 날을 진심으로 기념하며, 생일을 축하드립니다.\n\n- 행복복지재단 임직원 일동 -`,
  '3': (name) => `${name} 후원자님께\n\n생일을 진심으로 축하드립니다! 언제나 아낌없는 성원을 보내주셔서 감사드리며, 즐겁고 기쁨 가득한 생일날 보내시길 기원합니다.\n\n- 행복복지재단 임직원 일동 -`
};

function updateCardPreview() {
  const currentList = selectedBirthdayTab === 'today' ? getBirthdayDonors().today : getBirthdayDonors().month;
  const currentDonor = currentList.find(d => d.donor_id === selectedBirthdayDonorId);
  
  if (!currentDonor) {
    clearCardPreview();
    return;
  }
  
  previewToEl.textContent = `${currentDonor.name} 후원자님께`;
  
  const templateId = messageTemplateSelect.value;
  const templateFn = messageTemplates[templateId];
  const fullText = templateFn(currentDonor.name);
  
  // Extracted body (removing TO and FROM parts for preview mockup)
  const bodyText = fullText.split('\n\n')[1];
  previewBodyEl.textContent = bodyText;
}

function clearCardPreview() {
  previewToEl.textContent = '후원자님께';
  previewBodyEl.textContent = '생일 대상자를 선택하시면 생일 축하 카드의 미리보기가 제공됩니다.';
}

// Send Birthday Card to Single Donor
function sendBirthdayCard(id) {
  const donor = donors.find(d => d.donor_id === id);
  if (!donor) return;
  
  sentBirthdayCards.add(id);
  showToast(`🎉 ${donor.name} 후원자님께 생일 축하 카드가 발송되었습니다! (이메일 및 SMS 전송 완료)`, 'success');
  
  // Refresh Views
  renderBirthdaySection();
}

// Send all birthday cards for the current list
function sendAllBirthdayCards() {
  const { today, month } = getBirthdayDonors();
  const currentList = selectedBirthdayTab === 'today' ? today : month;
  
  let sentCount = 0;
  currentList.forEach(d => {
    if (!sentBirthdayCards.has(d.donor_id)) {
      sentBirthdayCards.add(d.donor_id);
      sentCount++;
    }
  });
  
  if (sentCount > 0) {
    showToast(`🎉 총 ${sentCount}명의 생일자에게 생일 축하 카드가 일괄 발송되었습니다!`, 'success');
  } else {
    showToast('이미 모든 생일자에게 발송을 완료했습니다.', 'info');
  }
  
  renderBirthdaySection();
}

// Toast Alert System
function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const iconName = type === 'success' ? 'check-circle' : (type === 'error' ? 'alert-triangle' : 'info');
  
  toast.innerHTML = `
    <i data-lucide="${iconName}" class="toast-icon"></i>
    <span class="toast-message">${message}</span>
  `;
  
  toastContainer.appendChild(toast);
  lucide.createIcons();
  
  // Remove Toast after 4 seconds
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s forwards reverse cubic-bezier(0.175, 0.885, 0.32, 1.275)';
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}
