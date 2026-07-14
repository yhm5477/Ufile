// ── 상태 ──────────────────────────────────────────
// 로컬 FastAPI 백엔드 주소. FastAPI가 이 HTML을 직접 서빙하면 ''(빈 문자열)로 바꾸면 됨.
const API_BASE = 'http://127.0.0.1:8000';
const POLL_INTERVAL_MS = 1000; // 분석 진행률 폴링 주기 (1초)

const images = [];
let selectMode = false;
const selectedIds = new Set();

// ── DOM ───────────────────────────────────────────
const dropZone         = document.getElementById('drop-zone');
const fileInput        = document.getElementById('file-input');
const searchInput      = document.getElementById('search-input');
const clearSearch      = document.getElementById('clear-search');
const statusBar        = document.getElementById('status-bar');
const progressFill     = document.getElementById('progress-fill');
const statusText       = document.getElementById('status-text');
const summary          = document.getElementById('summary');
const summaryText      = document.getElementById('summary-text');
const gallery          = document.getElementById('gallery');
const noResults        = document.getElementById('no-results');
const lightbox         = document.getElementById('lightbox');
const lightboxImg      = document.getElementById('lightbox-img');
const lightboxClose    = document.getElementById('lightbox-close');
const selectToggle     = document.getElementById('select-toggle');
const selectAll        = document.getElementById('select-all');
const selectCount      = document.getElementById('select-count');
const downloadSelected = document.getElementById('download-selected');
const historyToggle    = document.getElementById('history-toggle');
const historyModal     = document.getElementById('history-modal');
const historyClose     = document.getElementById('history-close');
const historyList      = document.getElementById('history-list');
const historyEmpty     = document.getElementById('history-empty');

// ── 업로드 이벤트 ─────────────────────────────────
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  handleFiles(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')));
});
fileInput.addEventListener('change', () => {
  handleFiles(Array.from(fileInput.files));
  fileInput.value = '';
});

// ── 파일 처리: 백엔드 업로드 + 진행률 폴링 ────────
async function handleFiles(files) {
  if (!files.length) return;

  // 1) 미리보기 카드를 먼저 렌더링 (FileReader는 화면 표시용으로만 사용)
  const newItems = await Promise.all(files.map(readFile));
  images.push(...newItems);
  newItems.forEach(renderCard);
  updateSummary();

  // 2) UI 스레드 멈춤 방지를 위해 프로그레스 바 레이어 활성화
  statusBar.classList.remove('hidden');
  statusText.textContent = '서버에 업로드 중...';
  progressFill.style.width = '0%';

  // 3) 파일을 Multipart FormData로 패키징
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  try {
    // 4) 백엔드 태스크 큐 등록 API 호출 → task_id 발급
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(`업로드 실패 (HTTP ${res.status})`);
    const { task_id: taskId } = await res.json();

    // 5) task_id 기반 1초 주기 폴링 시작
    statusText.textContent = '분석 대기 중...';
    pollTaskStatus(taskId, newItems);
  } catch (e) {
    console.error('백엔드 비동기 통신 실패:', e);
    statusText.textContent = '분석 중 오류 발생 — 로컬 서버가 켜져 있는지 확인하세요.';
    markFailed(newItems);
  }
}

// GET /api/status?task_id=xxx 를 주기적으로 호출해 진행률을 갱신하고,
// completed가 되면 폴링을 멈추고 결과를 화면에 반영한다.
function pollTaskStatus(taskId, localItems) {
  const timer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status?task_id=${encodeURIComponent(taskId)}`);
      if (!res.ok) throw new Error(`상태 조회 실패 (HTTP ${res.status})`);
      const data = await res.json();

      // 백엔드가 주는 progress_percent에 맞춰 프로그레스 바 동적 업데이트
      const percent = Math.max(0, Math.min(100, Number(data.progress_percent) || 0));
      progressFill.style.width = percent + '%';
      statusText.textContent = `분석 중... (${percent}%)`;

      if (data.status === 'completed') {
        clearInterval(timer);
        progressFill.style.width = '100%';
        applyResults(localItems, data.results || []);
        setTimeout(() => {
          statusBar.classList.add('hidden');
          progressFill.style.width = '0%';
        }, 600);
      } else if (data.status === 'failed') {
        clearInterval(timer);
        statusText.textContent = '분석 중 오류 발생: ' + (data.error || '알 수 없는 오류');
        markFailed(localItems);
      }
    } catch (e) {
      clearInterval(timer);
      console.error('백엔드 비동기 통신 실패:', e);
      statusText.textContent = '분석 중 오류 발생';
      markFailed(localItems);
    }
  }, POLL_INTERVAL_MS);
}

// 백엔드 분석 결과(태그·서버 item id)를 로컬 카드에 반영
function applyResults(localItems, results) {
  results.forEach((r, idx) => {
    // 업로드 순서 기준 매칭, 어긋나면 파일명으로 재탐색
    const item = localItems[idx]?.name === r.filename
      ? localItems[idx]
      : (localItems.find(i => i.name === r.filename && !i.analyzed) || localItems[idx]);
    if (!item) return;
    item.serverId = r.id;            // 다운로드/이력 API에서 사용할 서버측 ID
    item.tags = Array.isArray(r.tags) ? r.tags : [];
    item.analyzed = true;
    updateCard(item);
  });
  // 결과가 오지 않은 항목은 실패 처리해서 스피너가 무한 대기하지 않게 함
  markFailed(localItems);
  updateSummary();
  filterGallery();
}

function markFailed(localItems) {
  localItems.forEach(item => {
    if (item.analyzed) return;
    item.tags = ['분석 실패'];
    item.analyzed = true;
    updateCard(item);
  });
  updateSummary();
}

function readFile(file) {
  return new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => resolve({
      id: crypto.randomUUID(), // 화면(DOM)용 로컬 ID
      serverId: null,          // 백엔드 DB의 item ID (분석 완료 후 채워짐)
      name: file.name,
      dataUrl: e.target.result,
      tags: [],
      analyzed: false,
    });
    reader.readAsDataURL(file);
  });
}

// ── 검색 ──────────────────────────────────────────
searchInput.addEventListener('input', filterGallery);
clearSearch.addEventListener('click', () => { searchInput.value = ''; filterGallery(); });

function filterGallery() {
  const query = searchInput.value.trim().toLowerCase();
  let visible = 0;

  images.forEach(item => {
    const card = document.getElementById('card-' + item.id);
    const tagsEl = document.getElementById('tags-' + item.id);
    if (!card) return;

    if (!query) {
      card.classList.remove('hidden');
      if (tagsEl) { tagsEl.classList.remove('visible'); tagsEl.innerHTML = ''; }
      visible++;
      return;
    }

    const matchedTags = item.tags.filter(t => t.toLowerCase().includes(query));
    const matched = matchedTags.length > 0;
    card.classList.toggle('hidden', !matched);

    if (matched) {
      visible++;
      if (tagsEl) {
        tagsEl.classList.add('visible');
        tagsEl.innerHTML = matchedTags.map(t => `<span class="tag">${t}</span>`).join('');
      }
    } else {
      if (tagsEl) { tagsEl.classList.remove('visible'); tagsEl.innerHTML = ''; }
    }
  });

  noResults.classList.toggle('hidden', visible > 0 || images.length === 0);
  updateSummary(query, visible);
}

// ── 갤러리 렌더링 ─────────────────────────────────
function renderCard(item) {
  const card = document.createElement('div');
  card.id = 'card-' + item.id;
  card.className = 'image-card';
  card.innerHTML = `
    <div class="card-img-wrap">
      <img src="${item.dataUrl}" alt="${item.name}">
      <button class="delete-btn" title="삭제">✕</button>
      <div class="select-check">✓</div>
    </div>
    <div class="tags" id="tags-${item.id}"></div>
    <div class="analyzing-overlay" id="overlay-${item.id}">
      <div class="spinner"></div>
      <span>분석 중...</span>
    </div>
  `;
  card.querySelector('img').addEventListener('click', () => {
    if (!selectMode) openLightbox(item.dataUrl);
  });
  card.querySelector('.delete-btn').addEventListener('click', () => deleteImage(item.id));
  gallery.appendChild(card);
}

function updateCard(item) {
  document.getElementById('overlay-' + item.id)?.remove();
  const tagsEl = document.getElementById('tags-' + item.id);
  if (!tagsEl) return;
  if (item.tags.length === 0) {
    tagsEl.innerHTML = '<span class="tag tag-none">인식 불가</span>';
    return;
  }
  tagsEl.innerHTML = item.tags.map(t => `<span class="tag">${t}</span>`).join('');
}

// ── 삭제 ─────────────────────────────────────────
function deleteImage(id) {
  const idx = images.findIndex(i => i.id === id);
  if (idx !== -1) images.splice(idx, 1);
  document.getElementById('card-' + id)?.remove();
  filterGallery();
}

document.getElementById('delete-all').addEventListener('click', () => {
  if (selectedIds.size === 0) return;
  [...selectedIds].forEach(id => deleteImage(id));
  selectedIds.clear();
  updateSelectCount();
});

// ── 라이트박스 ────────────────────────────────────
function openLightbox(src) {
  lightboxImg.src = src;
  lightbox.classList.remove('hidden');
}
lightboxClose.addEventListener('click', () => lightbox.classList.add('hidden'));
lightbox.addEventListener('click', e => { if (e.target === lightbox) lightbox.classList.add('hidden'); });

// ── 요약 ─────────────────────────────────────────
function updateSummary(query, visible) {
  const total = images.length;
  if (total === 0) { summary.classList.add('hidden'); return; }
  summary.classList.remove('hidden');
  if (query) {
    summaryText.textContent = `"${query}" 검색 결과: ${visible}개 / 전체 ${total}개`;
  } else {
    const done = images.filter(i => i.analyzed).length;
    summaryText.textContent = `전체 ${total}개 · 분석 완료 ${done}개`;
  }
}

// ── 선택 모드 ─────────────────────────────────────
selectToggle.addEventListener('click', () => {
  selectMode = !selectMode;
  selectedIds.clear();
  gallery.classList.toggle('select-mode', selectMode);
  selectToggle.textContent = selectMode ? '취소' : '선택';
  selectToggle.classList.toggle('active', selectMode);
  selectAll.textContent = '전체 선택';
  selectAll.classList.toggle('hidden', !selectMode);
  selectCount.classList.toggle('hidden', !selectMode);
  downloadSelected.classList.add('hidden');
  // 모든 카드 선택 해제
  document.querySelectorAll('.image-card').forEach(c => c.classList.remove('selected'));
  updateSelectCount();
});

selectAll.addEventListener('click', () => {
  const visibleCards = [...document.querySelectorAll('.image-card:not(.hidden)')];
  if (selectedIds.size > 0) {
    visibleCards.forEach(c => { c.classList.remove('selected'); selectedIds.delete(c.id.replace('card-', '')); });
  } else {
    visibleCards.forEach(c => { c.classList.add('selected'); selectedIds.add(c.id.replace('card-', '')); });
  }
  updateSelectCount();
});

function toggleSelect(id) {
  const card = document.getElementById('card-' + id);
  if (!card) return;
  if (selectedIds.has(id)) {
    selectedIds.delete(id);
    card.classList.remove('selected');
  } else {
    selectedIds.add(id);
    card.classList.add('selected');
  }
  updateSelectCount();
}

// ── 드래그 선택 ───────────────────────────────────
let isDragging = false;
let dragSelectMode = null; // true=선택, false=해제

gallery.addEventListener('mousedown', e => {
  if (!selectMode) return;
  const card = e.target.closest('.image-card');
  if (!card) return;
  e.preventDefault();
  isDragging = true;
  const id = card.id.replace('card-', '');
  dragSelectMode = !selectedIds.has(id);
  applyDragSelect(id);
});

gallery.addEventListener('mouseover', e => {
  if (!isDragging || !selectMode) return;
  const card = e.target.closest('.image-card');
  if (!card) return;
  applyDragSelect(card.id.replace('card-', ''));
});

document.addEventListener('mouseup', () => { isDragging = false; dragSelectMode = null; });

function applyDragSelect(id) {
  const card = document.getElementById('card-' + id);
  if (!card || card.classList.contains('hidden')) return;
  if (dragSelectMode) {
    selectedIds.add(id);
    card.classList.add('selected');
  } else {
    selectedIds.delete(id);
    card.classList.remove('selected');
  }
  updateSelectCount();
}

function updateSelectCount() {
  const n = selectedIds.size;
  selectCount.textContent = `${n}장 선택됨`;
  downloadSelected.classList.toggle('hidden', n === 0);
  document.getElementById('delete-all').classList.toggle('hidden', n === 0);
  if (selectMode) {
    selectAll.textContent = n > 0 ? '전체 해제' : '전체 선택';
  }
}

// ── 다운로드 기록 (백엔드 SQLite 조회) ─────────────
async function renderHistory() {
  let history = [];
  try {
    const res = await fetch(`${API_BASE}/api/history`);
    if (res.ok) history = await res.json();
  } catch (e) {
    console.error('다운로드 기록 조회 실패:', e);
  }

  historyList.innerHTML = '';
  if (history.length === 0) {
    historyEmpty.classList.remove('hidden');
    historyList.classList.add('hidden');
    return;
  }
  historyEmpty.classList.add('hidden');
  historyList.classList.remove('hidden');

  history.forEach(entry => {
    const el = document.createElement('div');
    el.className = 'history-entry';
    el.dataset.id = entry.id;
    el.innerHTML = `
      <div class="history-entry-header">
        <div class="history-entry-check">✓</div>
        <span class="history-entry-arrow">▶</span>
        <div class="history-entry-info">
          <div class="history-entry-name">${entry.query || '검색어 없음'}</div>
          <div class="history-entry-meta">${entry.datetime}</div>
        </div>
        <span class="history-entry-count">${entry.files.length}장</span>
        <button class="history-entry-delete" title="삭제">✕</button>
      </div>
      <div class="history-thumbs">
        ${entry.files.map(f => `
          <div class="history-thumb" title="${f.name}">
            ${f.thumb_url ? `<img src="${API_BASE}${f.thumb_url}" alt="${f.name}">` : '<div style="width:100%;height:100%;background:#222"></div>'}
            <div class="history-thumb-name">${f.name}</div>
          </div>
        `).join('')}
      </div>
    `;
    el.querySelector('.history-entry-header').addEventListener('click', e => {
      if (e.target.closest('.history-entry-delete')) return;
      if (historyList.classList.contains('select-mode')) {
        el.classList.toggle('checked');
        updateHistoryDeleteBtn();
        return;
      }
      el.classList.toggle('open');
    });
    el.querySelector('.history-entry-delete').addEventListener('click', async () => {
      try {
        const res = await fetch(`${API_BASE}/api/history/${entry.id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`삭제 실패 (HTTP ${res.status})`);
      } catch (err) {
        console.error('기록 삭제 실패:', err);
        alert('기록 삭제에 실패했습니다. 서버 상태를 확인하세요.');
        return;
      }
      el.remove();
      if (historyList.querySelectorAll('.history-entry').length === 0) {
        historyEmpty.classList.remove('hidden');
        historyList.classList.add('hidden');
      }
    });
    // 썸네일 클릭 → 라이트박스
    el.querySelectorAll('.history-thumb').forEach((thumb, i) => {
      thumb.addEventListener('click', () => {
        if (entry.files[i].thumb_url) openLightbox(API_BASE + entry.files[i].thumb_url);
      });
    });
    historyList.appendChild(el);
  });
}

historyToggle.addEventListener('click', () => {
  renderHistory();
  historyModal.classList.remove('hidden');
  historyToggle.classList.add('active');
});

historyClose.addEventListener('click', () => {
  historyModal.classList.add('hidden');
  historyToggle.classList.remove('active');
});

historyModal.addEventListener('click', e => {
  if (e.target === historyModal) {
    historyModal.classList.add('hidden');
    historyToggle.classList.remove('active');
  }
});

const historySelectToggle = document.getElementById('history-select-toggle');
const historySelectAll    = document.getElementById('history-select-all');
const historyDeleteAll    = document.getElementById('history-delete-all');

function updateHistoryDeleteBtn() {
  const entries = [...historyList.querySelectorAll('.history-entry')];
  const checked = entries.filter(e => e.classList.contains('checked'));
  historyDeleteAll.classList.toggle('hidden', checked.length === 0);
  historySelectAll.textContent = checked.length > 0 ? '전체 해제' : '전체 선택';
}

historySelectToggle.addEventListener('click', () => {
  const isSelect = historyList.classList.toggle('select-mode');
  historySelectToggle.textContent = isSelect ? '취소' : '선택';
  historySelectToggle.classList.toggle('active', isSelect);
  historySelectAll.classList.toggle('hidden', !isSelect);
  if (!isSelect) {
    historyList.querySelectorAll('.history-entry').forEach(e => e.classList.remove('checked'));
    historyDeleteAll.classList.add('hidden');
    historySelectAll.textContent = '전체 선택';
  }
});

historySelectAll.addEventListener('click', () => {
  const entries = [...historyList.querySelectorAll('.history-entry')];
  const anyChecked = entries.some(e => e.classList.contains('checked'));
  if (anyChecked) {
    entries.forEach(e => e.classList.remove('checked'));
  } else {
    entries.forEach(e => e.classList.add('checked'));
  }
  updateHistoryDeleteBtn();
});

historyDeleteAll.addEventListener('click', async () => {
  const checked = [...historyList.querySelectorAll('.history-entry.checked')];
  if (checked.length === 0) return;
  if (!confirm(`선택한 ${checked.length}개의 기록을 삭제할까요?`)) return;
  const checkedIds = checked.map(el => Number(el.dataset.id));
  try {
    const res = await fetch(`${API_BASE}/api/history/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: checkedIds }),
    });
    if (!res.ok) throw new Error(`삭제 실패 (HTTP ${res.status})`);
  } catch (err) {
    console.error('기록 일괄 삭제 실패:', err);
    alert('기록 삭제에 실패했습니다. 서버 상태를 확인하세요.');
    return;
  }
  checked.forEach(el => el.remove());
  historyDeleteAll.classList.add('hidden');
  if (historyList.querySelectorAll('.history-entry').length === 0) {
    historyList.classList.remove('select-mode');
    historyList.classList.add('hidden');
    historySelectToggle.textContent = '선택';
    historySelectToggle.classList.remove('active');
    historyEmpty.classList.remove('hidden');
  }
});

// ── 선택 다운로드: 백엔드에 파일 이동 요청 ─────────
// 브라우저 showDirectoryPicker 대신 백엔드 POST /api/download를 호출한다.
// 실제 파일 재배치와 SQLite DB 이력 저장은 파이썬 서버가 수행한다.
downloadSelected.addEventListener('click', async () => {
  const items = images.filter(i => selectedIds.has(i.id));
  if (items.length === 0) return;

  // 서버 분석이 끝나야 serverId가 생기므로 미완료 항목은 막는다
  const notReady = items.filter(i => !i.serverId);
  if (notReady.length > 0) {
    alert('아직 서버 분석이 끝나지 않은 사진이 포함되어 있습니다. 잠시 후 다시 시도하세요.');
    return;
  }

  const targetDir = prompt('사진을 저장할 폴더 경로를 입력하세요.', 'C:\\ImageSearch\\결과');
  if (!targetDir) return;

  downloadSelected.disabled = true;
  downloadSelected.textContent = '저장 요청 중...';

  try {
    const res = await fetch(`${API_BASE}/api/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selected_item_ids: items.map(i => i.serverId),
        target_output_dir: targetDir,
        query: searchInput.value.trim(), // SQLite 이력에 함께 기록할 검색어
      }),
    });
    if (!res.ok) throw new Error(`다운로드 요청 실패 (HTTP ${res.status})`);
    const data = await res.json();
    alert(`${data.moved_count ?? items.length}장이 "${targetDir}" 폴더에 저장되었습니다.`);
  } catch (e) {
    console.error('백엔드 다운로드 요청 실패:', e);
    alert('저장 요청에 실패했습니다. 로컬 서버가 켜져 있는지 확인하세요.');
  }

  downloadSelected.disabled = false;
  downloadSelected.textContent = '⬇ 다운로드';
});
