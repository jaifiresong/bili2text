/**
 * B站视频转录与智能总结 - 前端交互逻辑
 *
 * 职责：
 * - Tab 切换：提交任务 / 任务列表 / 文档库
 * - URL 解析 → 分P选择 → 提交 → 5s 轮询结果
 * - 任务列表 + 点击查看详情
 * - 文档库 + 点击查看原始/加标点/总结文本
 */

// ============================================================
// 全局状态
// ============================================================

let currentVideoInfo = null;
let activeTab = "submit";
const pollingTimers = new Map();

// ============================================================
// Tab 切换
// ============================================================

function switchTab(name) {
  activeTab = name;
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    const isActive = btn.id === `tab-${name}`;
    btn.className = isActive
      ? "tab-btn flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition bg-bilibili-50 text-bilibili-600"
      : "tab-btn flex-1 px-4 py-2.5 text-sm font-medium rounded-md transition text-gray-600 hover:bg-gray-100";
  });
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.add("hidden"));
  const panel = document.getElementById(`panel-${name}`);
  if (panel) panel.classList.remove("hidden");

  if (name === "tasks") loadTaskList();
  if (name === "documents") loadDocList();
}

// ============================================================
// Toast 通知
// ============================================================

const TOAST_COLORS = {
  success: "bg-green-500",
  error: "bg-red-500",
  warning: "bg-amber-500",
  info: "bg-sky-500",
};

const TOAST_ICONS = {
  success: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`,
  error: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`,
  warning: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M5.07 19H18.93A2 2 0 0020.07 16L14.07 4a2 2 0 00-3.46 0L3.93 16A2 2 0 005.07 19z"/></svg>`,
  info: `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
};

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const color = TOAST_COLORS[type] || TOAST_COLORS.info;
  const icon = TOAST_ICONS[type] || TOAST_ICONS.info;
  const el = document.createElement("div");
  el.className = `pointer-events-auto ${color} text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 text-sm min-w-[240px] max-w-sm transition-all duration-300 translate-x-full opacity-0`;
  el.innerHTML = `${icon}<span class="flex-1">${message}</span>`;
  container.appendChild(el);
  requestAnimationFrame(() => el.classList.remove("translate-x-full", "opacity-0"));
  setTimeout(() => {
    el.classList.add("translate-x-full", "opacity-0");
    el.addEventListener("transitionend", () => el.remove());
  }, 3000);
}

// ============================================================
// 1. URL 解析
// ============================================================

async function parseUrl() {
  const urlInput = document.getElementById("videoUrl");
  const url = urlInput.value.trim();
  if (!url) {
    showToast("请输入视频地址", "warning");
    return;
  }

  const btn = document.getElementById("parseBtn");
  btn.disabled = true;
  btn.textContent = "解析中...";

  try {
    const res = await fetch(`/api/v1/tasks/parse?video_url=${encodeURIComponent(url)}`);
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "解析失败");
    }
    const videoInfo = await res.json();
    if (!videoInfo.pages || videoInfo.pages.length === 0) {
      throw new Error("未获取到视频分P信息");
    }
    currentVideoInfo = videoInfo;

    if (videoInfo.pages.length === 1) {
      submitBatch(videoInfo.id, [videoInfo.pages[0].page]);
    } else {
      showPageModal(videoInfo);
    }
  } catch (e) {
    console.error(e);
    showToast(e.message || "网络错误，请检查后端服务是否运行", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "解析视频";
  }
}

// ============================================================
// 2. 多P 选择弹窗
// ============================================================

function showPageModal(videoInfo) {
  document.getElementById("modalVideoTitle").textContent = videoInfo.title || "选择要处理的分P";
  const list = document.getElementById("pageList");
  list.innerHTML = "";

  videoInfo.pages.forEach((page) => {
    const label = document.createElement("label");
    label.className = "flex items-center space-x-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer transition";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = page.page;
    checkbox.className = "page-checkbox w-5 h-5 text-sky-500 rounded focus:ring-sky-500";
    checkbox.checked = true;
    const text = document.createElement("span");
    text.className = "text-gray-700";
    text.textContent = `P${page.page}：${page.part}`;
    label.appendChild(checkbox);
    label.appendChild(text);
    list.appendChild(label);
  });

  document.getElementById("pageModal").classList.remove("hidden");
}

function closePageModal() {
  document.getElementById("pageModal").classList.add("hidden");
}

function selectAllPages() {
  document.querySelectorAll(".page-checkbox").forEach((cb) => (cb.checked = true));
}

function deselectAllPages() {
  document.querySelectorAll(".page-checkbox").forEach((cb) => (cb.checked = false));
}

async function submitSelectedPages() {
  const checkboxes = document.querySelectorAll(".page-checkbox:checked");
  if (checkboxes.length === 0) {
    showToast("请至少选择一集", "warning");
    return;
  }
  const pages = Array.from(checkboxes).map((cb) => parseInt(cb.value));
  closePageModal();
  await submitBatch(currentVideoInfo.id, pages);
}

// ============================================================
// 3. 批量提交
// ============================================================

async function submitBatch(videoId, pages) {
  try {
    const res = await fetch("/api/v1/tasks/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_id: videoId, pages }),
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "提交失败");
    }

    const task = await res.json();
    if (!task || !task.task_id) {
      showToast("未创建任何任务", "warning");
      return;
    }

    createPollingCard(task.task_id, currentVideoInfo?.title || task.video_id);
    startPolling(task.task_id);

    showToast("已创建任务，开始处理", "success");
  } catch (e) {
    console.error("提交任务失败:", e);
    showToast(e.message || "提交任务失败，请检查网络", "error");
  }
}

// ============================================================
// 4. 轮询卡片 + 5秒轮询
// ============================================================

function createPollingCard(taskId, title) {
  const container = document.getElementById("pollingContainer");
  const card = document.createElement("div");
  card.id = `poll-${taskId}`;
  card.className = "bg-white rounded-xl shadow-sm border border-gray-200 p-5 transition";
  card.innerHTML = `
    <div class="flex justify-between items-start mb-3">
      <h3 class="font-semibold text-gray-800 text-sm truncate pr-4" title="${title}">${title}</h3>
      <span class="poll-status text-xs font-medium px-2 py-1 rounded-full bg-sky-50 text-sky-600">处理中</span>
    </div>
    <div class="w-full bg-gray-100 rounded-full h-2 mb-2 overflow-hidden">
      <div class="poll-progress bg-sky-500 h-2 rounded-full transition-all duration-500" style="width:10%"></div>
    </div>
    <div class="poll-msg text-xs text-gray-400">等待流水线...</div>
    <div class="poll-result hidden mt-3 border-t border-gray-100 pt-3 space-y-2"></div>
  `;
  container.prepend(card);
}

function startPolling(taskId) {
  if (pollingTimers.has(taskId)) return;

  const timer = setInterval(() => pollTask(taskId), 5000);
  pollingTimers.set(taskId, timer);
  pollTask(taskId); // 立即执行一次
}

async function pollTask(taskId) {
  try {
    const res = await fetch(`/api/v1/tasks/${taskId}`);
    if (!res.ok) return;
    const data = await res.json();

    const card = document.getElementById(`poll-${taskId}`);
    if (!card) {
      stopPolling(taskId);
      return;
    }

    const progressBar = card.querySelector(".poll-progress");
    const statusBadge = card.querySelector(".poll-status");
    const msg = card.querySelector(".poll-msg");

    // 计算进度
    let done = 0, total = data.pages.length * 3;
    data.pages.forEach((p) => {
      if (p.raw_text) done++;
      if (p.punctuated_text) done++;
      if (p.summary) done++;
    });
    const pct = total > 0 ? Math.round((done / total) * 100) : 10;

    progressBar.style.width = pct + "%";
    msg.textContent = `已完成 ${done}/${total} 个处理步骤`;

    if (data.status === "completed") {
      progressBar.classList.replace("bg-sky-500", "bg-green-500");
      statusBadge.className = "poll-status text-xs font-medium px-2 py-1 rounded-full bg-green-50 text-green-600";
      statusBadge.textContent = "已完成";
      msg.textContent = "处理完成";
      renderPollResult(card, data);
      stopPolling(taskId);
    } else if (data.status === "failed") {
      progressBar.classList.replace("bg-sky-500", "bg-red-500");
      statusBadge.className = "poll-status text-xs font-medium px-2 py-1 rounded-full bg-red-50 text-red-600";
      statusBadge.textContent = "失败";
      stopPolling(taskId);
    }
  } catch (e) {
    // 轮询失败不提示，等下次重试
  }
}

function renderPollResult(card, data) {
  const resultArea = card.querySelector(".poll-result");
  resultArea.classList.remove("hidden");
  resultArea.innerHTML = "";

  data.pages.forEach((p) => {
    const block = document.createElement("div");
    block.className = "border border-gray-100 rounded-lg p-3";
    block.innerHTML = `
      <p class="text-xs font-medium text-gray-700 mb-2">P${p.page}：${p.part}</p>
      <div class="text-xs space-y-1">
        ${p.raw_text ? `<p class="cursor-pointer text-bilibili-500 hover:underline" onclick="showTextDetail('原始转录 - P${p.page}', ${JSON.stringify(p.raw_text).replace(/"/g, '&quot;')})">原始转录 (${p.raw_text.length} 字) ▶</p>` : '<p class="text-gray-300">原始转录：未生成</p>'}
        ${p.punctuated_text ? `<p class="cursor-pointer text-bilibili-500 hover:underline" onclick="showTextDetail('加标点文本 - P${p.page}', ${JSON.stringify(p.punctuated_text).replace(/"/g, '&quot;')})">加标点后 (${p.punctuated_text.length} 字) ▶</p>` : '<p class="text-gray-300">加标点：未生成</p>'}
        ${p.summary ? `<p class="cursor-pointer text-bilibili-500 hover:underline" onclick="showTextDetail('总结 - P${p.page}', ${JSON.stringify(p.summary).replace(/"/g, '&quot;')})">智能总结 (${p.summary.length} 字) ▶</p>` : '<p class="text-gray-300">总结：未生成</p>'}
      </div>
    `;
    resultArea.appendChild(block);
  });
}

function stopPolling(taskId) {
  const timer = pollingTimers.get(taskId);
  if (timer) {
    clearInterval(timer);
    pollingTimers.delete(taskId);
  }
}

// ============================================================
// 5. 任务列表
// ============================================================

async function loadTaskList() {
  const container = document.getElementById("taskListContainer");
  try {
    const res = await fetch("/api/v1/tasks/");
    const tasks = await res.json();
    if (!Array.isArray(tasks) || tasks.length === 0) {
      container.innerHTML = '<p class="text-sm text-gray-400 text-center py-8">暂无任务</p>';
      return;
    }

    container.innerHTML = "";
    tasks.reverse().forEach((task) => {
      const card = document.createElement("div");
      card.className = "bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:border-bilibili-300 transition cursor-pointer";
      card.onclick = () => loadTaskDetail(task.task_id);

      const date = task.created_at ? new Date(task.created_at).toLocaleString("zh-CN") : "";
      card.innerHTML = `
        <div class="flex justify-between items-center">
          <div>
            <p class="font-medium text-sm text-gray-800">${task.video_title || "未知视频"}</p>
            <p class="text-xs text-gray-400 mt-1">${date}</p>
          </div>
          <span class="text-xs text-bilibili-500">查看详情 →</span>
        </div>
        <div class="mt-2 flex gap-2">
          <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">P: ${(task.pages || []).join(", ")}</span>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (e) {
    container.innerHTML = '<p class="text-sm text-red-400 text-center py-8">加载失败</p>';
  }
}

async function loadTaskDetail(taskId) {
  try {
    const res = await fetch(`/api/v1/tasks/${taskId}`);
    const data = await res.json();
    showDetailModal(data.video_title || "任务详情", data, "task");
  } catch (e) {
    showToast("加载任务详情失败", "error");
  }
}

// ============================================================
// 6. 文档库
// ============================================================

let currentDocData = null;

async function loadDocList() {
  const container = document.getElementById("docListContainer");
  try {
    const res = await fetch("/api/v1/documents/");
    const docs = await res.json();
    if (!Array.isArray(docs) || docs.length === 0) {
      container.innerHTML = '<p class="text-sm text-gray-400 text-center py-8">暂无已处理文档</p>';
      return;
    }

    container.innerHTML = "";
    docs.forEach((doc) => {
      if (!doc.has_content) return;
      const card = document.createElement("div");
      card.className = "bg-white rounded-lg shadow-sm border border-gray-200 p-4 hover:border-bilibili-300 transition cursor-pointer";
      card.onclick = () => openDocDetail(doc.id);

      card.innerHTML = `
        <div class="flex justify-between items-center">
          <div>
            <p class="font-medium text-sm text-gray-800">${doc.title}</p>
            <p class="text-xs text-gray-400 mt-1">BV: ${doc.bvid} · ${doc.page_count} 个分P</p>
          </div>
          <span class="text-xs text-bilibili-500">查看文本 →</span>
        </div>
      `;
      container.appendChild(card);
    });
    if (!container.children.length) {
      container.innerHTML = '<p class="text-sm text-gray-400 text-center py-8">暂无已处理文档</p>';
    }
  } catch (e) {
    container.innerHTML = '<p class="text-sm text-red-400 text-center py-8">加载失败</p>';
  }
}

async function openDocDetail(videoId) {
  try {
    const res = await fetch(`/api/v1/documents/${videoId}`);
    const data = await res.json();
    currentDocData = data;

    // 切换视图
    document.getElementById("docListView").classList.add("hidden");
    document.getElementById("docDetailView").classList.remove("hidden");
    document.getElementById("docDetailTitle").textContent = data.title;
    document.getElementById("docOriginalLink").href = data.url_value;

    // 渲染左侧分P菜单
    renderDocPageMenu(data.pages);

    // 默认选中第一个有内容的 page
    const firstWithContent = data.pages.find((p) => p.raw_text || p.punctuated_text || p.summary);
    if (firstWithContent) {
      selectDocPage(firstWithContent.page);
    } else if (data.pages.length > 0) {
      selectDocPage(data.pages[0].page);
    }
  } catch (e) {
    showToast("加载文档详情失败", "error");
  }
}

function renderDocPageMenu(pages) {
  const menu = document.getElementById("docPageMenu");
  menu.innerHTML = "";

  pages.forEach((p) => {
    const hasContent = p.raw_text || p.punctuated_text || p.summary;
    const item = document.createElement("div");
    item.id = `page-menu-${p.page}`;
    item.className = "doc-page-item px-4 py-2.5 cursor-pointer hover:bg-gray-50 transition border-l-2 border-transparent text-sm flex items-center gap-1.5";
    item.title = `P${p.page}：${p.part}`;
    item.innerHTML = `
      <span class="text-gray-700 truncate flex-1 min-w-0">P${p.page}：${p.part}</span>
      ${hasContent ? '<span class="shrink-0 text-xs text-green-500">✓</span>' : '<span class="shrink-0 text-xs text-gray-300">空</span>'}
      ${hasContent
        ? '<button class="shrink-0 text-xs text-red-400 hover:text-red-600 ml-1 px-1" title="删除该分P的处理文件">×</button>'
        : '<button class="shrink-0 text-xs text-bilibili-500 hover:text-bilibili-700 ml-1 px-1 font-bold" title="创建该分P的处理任务">＋</button>'}
    `;
    item.querySelector('button').onclick = (e) => {
      e.stopPropagation();
      handlePageAction(p.page, hasContent);
    };
    item.onclick = () => selectDocPage(p.page);
    menu.appendChild(item);
  });
}

function selectDocPage(pageNum) {
  // 高亮当前选中项
  document.querySelectorAll(".doc-page-item").forEach((el) => {
    el.classList.remove("border-l-bilibili-500", "bg-bilibili-50");
    el.classList.add("border-l-transparent");
  });
  document.querySelectorAll(".doc-page-item span.truncate").forEach((el) => {
    el.classList.remove("text-bilibili-600");
  });
  const activeItem = document.getElementById(`page-menu-${pageNum}`);
  if (activeItem) {
    activeItem.classList.add("border-l-bilibili-500", "bg-bilibili-50");
    activeItem.querySelector("span.truncate").classList.add("text-bilibili-600");
  }

  if (!currentDocData) return;
  const page = currentDocData.pages.find((p) => p.page === pageNum);
  if (!page) return;

  const content = document.getElementById("docPageContent");
  content.innerHTML = "";

  if (!page.raw_text && !page.punctuated_text && !page.summary) {
    content.innerHTML = '<p class="text-sm text-gray-400 text-center py-12">该分P暂无文本内容</p>';
    return;
  }

  // 构建可选 tab 列表
  const tabs = [];
  if (page.raw_text) tabs.push({ key: "raw", label: "原始转录", text: page.raw_text, isMd: false });
  if (page.punctuated_text) tabs.push({ key: "punct", label: "加标点后", text: page.punctuated_text, isMd: true });
  if (page.summary) tabs.push({ key: "summary", label: "智能总结", text: page.summary, isMd: true });

  // 存储当前 page 数据到 content 元素上
  content._docTabs = tabs;

  // 工具栏：tab 按钮 + 复制按钮
  const toolbar = document.createElement("div");
  toolbar.className = "flex items-center justify-between mb-4 border-b border-gray-200 pb-0";

  const tabBar = document.createElement("div");
  tabBar.className = "flex items-center gap-1";

  tabs.forEach((t, i) => {
    const btn = document.createElement("button");
    btn.className = "doc-text-tab px-4 py-2 text-sm font-medium rounded-t-md transition border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300";
    btn.textContent = `${t.label} (${t.text.length} 字)`;
    btn.onclick = () => switchDocTextTab(content, i);
    tabBar.appendChild(btn);
  });
  toolbar.appendChild(tabBar);

  const copyBtn = document.createElement("button");
  copyBtn.className = "mb-1 px-3 py-1.5 text-xs font-medium text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 transition flex items-center gap-1";
  copyBtn.innerHTML = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 012-2v-8a2 2 0 01-2-2h-8a2 2 0 01-2 2v8a2 2 0 012 2z"/></svg>复制内容`;
  copyBtn.onclick = () => copyCurrentDocText(content);
  toolbar.appendChild(copyBtn);

  content.appendChild(toolbar);

  // 内容容器
  const body = document.createElement("div");
  body.className = "doc-text-body";
  content.appendChild(body);

  // 默认选中智能总结，没有则选最后一个
  const defaultIdx = tabs.findIndex(t => t.key === "summary");
  switchDocTextTab(content, defaultIdx >= 0 ? defaultIdx : tabs.length - 1);
}

function switchDocTextTab(contentEl, index) {
  const tabs = contentEl._docTabs;
  if (!tabs || index >= tabs.length) return;
  contentEl._activeTabIdx = index;

  // 更新 tab 按钮样式
  const buttons = contentEl.querySelectorAll(".doc-text-tab");
  buttons.forEach((btn, i) => {
    if (i === index) {
      btn.className = "doc-text-tab px-4 py-2 text-sm font-medium rounded-t-md transition border-b-2 border-bilibili-500 text-bilibili-600 bg-white";
    } else {
      btn.className = "doc-text-tab px-4 py-2 text-sm font-medium rounded-t-md transition border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300";
    }
  });

  // 渲染内容
  const body = contentEl.querySelector(".doc-text-body");
  if (!body) return;

  const t = tabs[index];
  body.innerHTML = "";

  if (t.isMd) {
    const wrapper = document.createElement("div");
    wrapper.className = "doc-markdown text-sm leading-relaxed text-gray-800";
    wrapper.innerHTML = marked.parse(t.text);
    body.appendChild(wrapper);
  } else {
    const pre = document.createElement("pre");
    pre.className = "bg-gray-50 rounded-lg p-4 text-sm whitespace-pre-wrap break-words max-h-[70vh] overflow-y-auto leading-relaxed text-gray-700 font-mono";
    pre.textContent = t.text;
    body.appendChild(pre);
  }
}

async function copyCurrentDocText(contentEl) {
  const tabs = contentEl._docTabs;
  const idx = contentEl._activeTabIdx;
  if (!tabs || idx === undefined || idx >= tabs.length) return;
  const text = tabs[idx].text;
  try {
    await navigator.clipboard.writeText(text);
    showToast("内容已复制到剪贴板", "success");
  } catch (e) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      showToast("内容已复制到剪贴板", "success");
    } catch (err) {
      showToast("复制失败，请手动复制", "error");
    }
    document.body.removeChild(textarea);
  }
}

function backToDocList() {
  document.getElementById("docDetailView").classList.add("hidden");
  document.getElementById("docListView").classList.remove("hidden");
  currentDocData = null;
  loadDocList();
}

async function handlePageAction(pageNum, hasContent) {
  if (hasContent) {
    const ok = await showConfirm(`确认删除 P${pageNum} 的所有处理文件？`);
    if (!ok) return;
    try {
      const res = await fetch(`/api/v1/documents/${currentDocData.id}/pages/${pageNum}`, { method: "DELETE" });
      if (res.ok) {
        showToast(`P${pageNum} 已删除`, "success");
        openDocDetail(currentDocData.id);
      } else {
        const data = await res.json();
        showToast(data.detail || "删除失败", "error");
      }
    } catch (e) {
      showToast("删除失败", "error");
    }
  } else {
    const ok = await showConfirm(`为 P${pageNum} 创建处理任务？`);
    if (!ok) return;
    await submitBatch(currentDocData.id, [pageNum]);
  }
}

// ============================================================
// 8. 自定义确认弹窗
// ============================================================

let _confirmResolve = null;

function showConfirm(message) {
  return new Promise((resolve) => {
    _confirmResolve = resolve;
    document.getElementById("confirmMsg").textContent = message;
    document.getElementById("confirmModal").classList.remove("hidden");
  });
}

function closeConfirm(result) {
  document.getElementById("confirmModal").classList.add("hidden");
  if (_confirmResolve) {
    _confirmResolve(result);
    _confirmResolve = null;
  }
}

// ============================================================
// 7. 详情弹窗
// ============================================================

function showDetailModal(title, data, type) {
  document.getElementById("detailTitle").textContent = title;
  const content = document.getElementById("detailContent");
  content.innerHTML = "";

  (data.pages || []).forEach((p) => {
    const block = document.createElement("div");
    block.className = "mb-4 border border-gray-100 rounded-lg overflow-hidden";

    const header = document.createElement("div");
    header.className = "bg-gray-50 px-4 py-2 border-b border-gray-100";
    header.innerHTML = `<span class="text-sm font-medium text-gray-700">P${p.page}：${p.part}</span>`;
    block.appendChild(header);

    const body = document.createElement("div");
    body.className = "p-4 space-y-3 text-sm";

    if (p.raw_text) {
      body.innerHTML += detailSection("原始转录", p.raw_text);
    }
    if (p.punctuated_text) {
      body.innerHTML += detailSection("加标点后", p.punctuated_text);
    }
    if (p.summary) {
      body.innerHTML += `
        <div>
          <p class="font-medium text-gray-600 mb-1">智能总结</p>
          <div class="bg-gray-50 rounded-lg p-3 text-xs whitespace-pre-wrap break-words max-h-80 overflow-y-auto leading-relaxed markdown-body">${escapeHtml(p.summary)}</div>
        </div>
      `;
    }
    if (!p.raw_text && !p.punctuated_text && !p.summary) {
      body.innerHTML += '<p class="text-gray-400 text-xs">暂无文本内容</p>';
    }

    block.appendChild(body);
    content.appendChild(block);
  });

  document.getElementById("detailModal").classList.remove("hidden");
}

function detailSection(label, text) {
  const escaped = escapeHtml(text);
  return `
    <div>
      <p class="font-medium text-gray-600 mb-1">${label} <span class="text-xs text-gray-400">(${text.length} 字)</span></p>
      <pre class="bg-gray-50 rounded-lg p-3 text-xs whitespace-pre-wrap break-words max-h-60 overflow-y-auto leading-relaxed">${escaped}</pre>
    </div>
  `;
}

function showTextDetail(title, text) {
  showDetailModal(title, { pages: [{ page: "", part: "", summary: text }] }, "text");
}

function closeDetailModal() {
  document.getElementById("detailModal").classList.add("hidden");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ============================================================
// 初始化
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  switchTab("submit");
});
