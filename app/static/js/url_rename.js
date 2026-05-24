// =============== File Management ===============
async function loadUrlRenames(projectId) {
    const container = document.getElementById('fileManagerContent');
    try {
        const docsData = await API.get(`/api/projects/${projectId}/documents`);
        const mappingsData = await API.get(`/api/projects/${projectId}/url-mappings`);

        const documents = docsData.documents || [];
        const mappings = mappingsData.mappings || [];
        const mappingMap = {};
        mappings.forEach(m => { mappingMap[m.document_id] = m; });

        if (documents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📄</div>
                    <div class="empty-state-title">暂无文档</div>
                    <div class="empty-state-desc">请先上传文档</div>
                    <a href="/my-projects/${projectId}/upload" class="btn btn-primary">上传文档</a>
                </div>
            `;
            return;
        }

        let html = '<div class="table-container"><table><thead><tr>' +
            '<th>原文件路径</th>' +
            '<th>自定义 URL</th>' +
            '<th>详情描述</th>' +
            '<th style="width:60px;text-align:center;">显示</th>' +
            '<th>操作</th>' +
            '</tr></thead><tbody>';
        for (const doc of documents) {
            if (doc.is_directory) continue;
            const mapping = mappingMap[doc.id];
            const currentUrlName = mapping ? mapping.url_name : '';
            const hasRename = !!mapping;
            const desc = doc.description || '';

            const visible = doc.is_visible !== false;
            html += `
                <tr id="doc-row-${doc.id}">
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(doc.original_filename)}">${escapeHtml(doc.original_filename)}</td>
                    <td>
                        <input type="text" class="form-input" id="url-name-${doc.id}"
                               value="${escapeHtml(currentUrlName)}"
                               placeholder="留空使用原路径"
                               style="width:150px;font-size:var(--font-size-xs);"
                               oninput="updatePreview(${doc.id})">
                        <div style="font-size:var(--font-size-xs);color:var(--text-tertiary);font-family:monospace;margin-top:2px;">
                            <span id="url-preview-${doc.id}">${hasRename ? '/' + escapeHtml(currentUrlName) : '(使用原路径)'}</span>
                        </div>
                    </td>
                    <td>
                        <input type="text" class="form-input" id="desc-${doc.id}"
                               value="${escapeHtml(desc)}"
                               placeholder="文件描述（可选）"
                               style="width:180px;font-size:var(--font-size-xs);">
                    </td>
                    <td style="text-align:center;">
                        <label class="toggle-switch">
                            <input type="checkbox" id="visible-${doc.id}" ${visible ? 'checked' : ''} onchange="toggleVisibility(${projectId}, ${doc.id})">
                            <span class="toggle-slider"></span>
                        </label>
                    </td>
                    <td style="white-space:nowrap;">
                        <button class="btn btn-sm btn-outline" onclick="saveFileDetails(${projectId}, ${doc.id})">保存</button>
                        ${hasRename ? `<button class="btn btn-sm btn-ghost" onclick="clearUrlRename(${projectId}, ${doc.id})">清除URL</button>` : ''}
                        <button class="btn btn-sm btn-danger" onclick="deleteFile(${projectId}, ${doc.id}, '${escapeHtml(doc.original_filename)}')">删除</button>
                    </td>
                </tr>
            `;
        }
        html += '</tbody></table></div>';
        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-title">加载失败</div>
                <div class="empty-state-desc">${escapeHtml(err.message || '无法加载文件列表')}</div>
            </div>
        `;
    }
}

function updatePreview(docId) {
    const input = document.getElementById('url-name-' + docId);
    const preview = document.getElementById('url-preview-' + docId);
    preview.textContent = input.value ? '/' + input.value : '(使用原路径)';
}

async function saveFileDetails(projectId, docId) {
    const urlInput = document.getElementById('url-name-' + docId);
    const descInput = document.getElementById('desc-' + docId);
    const urlName = urlInput.value.trim();
    const description = descInput.value.trim();

    try {
        // Save URL rename if provided
        if (urlName) {
            await API.post(`/api/projects/${projectId}/documents/${docId}/rename`, { url_name: urlName });
        } else {
            // Clear rename if was empty and had one
            // We'll try to clear - will no-op if none existed
            try { await API.delete(`/api/projects/${projectId}/documents/${docId}/rename`); } catch(e) {}
        }
        // Save description
        await API.put(`/api/projects/${projectId}/documents/${docId}`, { description: description || null });
        showToast('保存成功', 'success');
        loadUrlRenames(projectId);
    } catch (err) {
        showToast(err.message || '保存失败', 'error');
    }
}

async function clearUrlRename(projectId, docId) {
    const ok = await showConfirm('确定清除这个 URL 重命名吗？', '确认清除');
    if (!ok) return;

    try {
        await API.delete(`/api/projects/${projectId}/documents/${docId}/rename`);
        showToast('URL 重命名已清除', 'info');
        loadUrlRenames(projectId);
    } catch (err) {
        showToast(err.message || '清除失败', 'error');
    }
}

async function deleteFile(projectId, docId, filename) {
    const ok = await showConfirm(`确定将文件 "${filename}" 移入回收站吗？`, '删除文件');
    if (!ok) return;

    try {
        await API.delete(`/api/projects/${projectId}/documents/${docId}`);
        showToast('文件已移入回收站', 'info');
        loadUrlRenames(projectId);
    } catch (err) {
        showToast(err.message || '删除失败', 'error');
    }
}

async function toggleVisibility(projectId, docId) {
    const checkbox = document.getElementById('visible-' + docId);
    const isVisible = checkbox.checked;
    try {
        await API.put(`/api/projects/${projectId}/documents/${docId}`, { is_visible: isVisible });
        showToast(isVisible ? '已设为显示' : '已设为隐藏', 'info');
    } catch (err) {
        showToast(err.message || '操作失败', 'error');
        checkbox.checked = !isVisible;
    }
}
