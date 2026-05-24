// =============== Upload Logic ===============
const projectId = window.location.pathname.match(/\/my-projects\/(\d+)\/upload/)?.[1];

document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const folderInput = document.getElementById('folderInput');

    if (!dropZone) return;

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFiles(e.dataTransfer.files);
        }
    });
    dropZone.addEventListener('click', () => fileInput.click());

    // File input handlers
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFiles(fileInput.files);
            fileInput.value = '';
        }
    });
    folderInput.addEventListener('change', () => {
        if (folderInput.files.length > 0) {
            uploadFiles(folderInput.files);
            folderInput.value = '';
        }
    });
});

async function uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        // webkitdirectory gives full relative paths
        const relativePath = file.webkitRelativePath || file.name;
        formData.append('files', file, relativePath);
    }

    const progressDiv = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    // Simulate progress (can't track real progress without XHR)
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressText = document.getElementById('progressText');
    progressBar.style.width = '60%';
    progressPercent.textContent = '60%';
    progressText.textContent = `正在上传 ${files.length} 个文件...`;

    try {
        const data = await API.upload(`/api/projects/${projectId}/documents/upload`, formData);
        progressBar.style.width = '100%';
        progressPercent.textContent = '100%';
        progressText.textContent = '上传完成';

        // Show results
        const uploaded = data.documents || [];
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = `
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>文件名</th>
                            <th>大小</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${uploaded.map(d => `
                            <tr>
                                <td>${escapeHtml(d.original_filename)}</td>
                                <td>${formatSize(d.file_size)}</td>
                                <td><span class="tag tag-approved">${d.error ? escapeHtml(d.error) : '成功'}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            <div style="margin-top:var(--spacing-md);text-align:center;">
                <a href="/my-projects/${projectId}/url-rename" class="btn btn-outline">文件管理</a>
            </div>
        `;
        showToast(`成功上传 ${uploaded.length} 个文件`, 'success');
    } catch (err) {
        progressBar.style.width = '100%';
        progressBar.style.background = 'var(--error)';
        progressText.textContent = '上传失败';
        showToast(err.message || '上传失败', 'error');
    }

    setTimeout(() => {
        progressDiv.style.display = 'none';
        progressBar.style.width = '0%';
        progressBar.style.background = '';
    }, 3000);
}
