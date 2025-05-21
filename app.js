document.addEventListener('DOMContentLoaded', function () {
    const imageUpload = document.getElementById('imageUpload');
    const processBtn = document.getElementById('processBtn');
    const originalPreview = document.getElementById('originalPreview');
    const processedPreview = document.getElementById('processedPreview');
    const originalSize = document.getElementById('originalSize');
    const processedSize = document.getElementById('processedSize');
    const compressionResults = document.querySelector('.compression-results');
    const downloadBtn = document.getElementById('downloadBtn');
    const customFields = document.getElementById('customFields');

    let selectedExam = null;

    // Exam option selection
    document.querySelectorAll('.exam-option').forEach(option => {
        option.addEventListener('click', function () {
            document.querySelectorAll('.exam-option').forEach(opt => {
                opt.classList.remove('border-primary', 'bg-light');
            });
            this.classList.add('border-primary', 'bg-light');
            selectedExam = this.getAttribute('data-exam');

            // Show/hide custom fields
            if (selectedExam === 'custom') {
                customFields.classList.remove('d-none');
            } else {
                customFields.classList.add('d-none');
            }
        });
    });

    // Image upload preview
    imageUpload.addEventListener('change', function (e) {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            const reader = new FileReader();

            reader.onload = function (event) {
                originalPreview.src = event.target.result;
                const fileSize = (file.size / 1024).toFixed(2);
                originalSize.textContent = `${fileSize} KB`;

                processedPreview.src = "https://via.placeholder.com/300x200";
                processedSize.textContent = "0 KB";
                compressionResults.classList.add('d-none');
            };

            reader.readAsDataURL(file);
        }
    });

    // Button click: send to backend
    processBtn.addEventListener('click', function () {
        const file = imageUpload.files[0];
        const algorithm = document.getElementById('algorithm').value;

        if (!file) {
            alert('Please upload an image first');
            return;
        }

        if (!selectedExam) {
            alert('Please select an exam type');
            return;
        }

        processImageBackend(file, algorithm, selectedExam);
    });

    // Backend interaction
    function processImageBackend(imageFile, algorithm, exam) {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('exam_type', exam);
        formData.append('algorithm', algorithm);

        if (exam === 'custom') {
            const width = document.getElementById('customWidth').value;
            const height = document.getElementById('customHeight').value;
            const maxSize = document.getElementById('customMaxSize').value;

            if (!width || !height || !maxSize) {
                alert('Please enter all custom dimension values.');
                return;
            }

            formData.append('custom_width', width);
            formData.append('custom_height', height);
            formData.append('custom_max_size', maxSize);
        }

        processBtn.disabled = true;
        processBtn.textContent = 'Processing...';

        fetch('http://localhost:5000/process_image', {
            method: 'POST',
            body: formData
        })
        .then(async response => {
            if (!response.ok) throw new Error('Compression failed');
            const blob = await response.blob();
            const imageURL = URL.createObjectURL(blob);

            // Display processed image
            processedPreview.src = imageURL;
            processedSize.textContent = `${(blob.size / 1024).toFixed(2)} KB`;

            // Display stats
            document.getElementById('originalSizeDetail').textContent = originalSize.textContent;
            document.getElementById('compressedSizeDetail').textContent = processedSize.textContent;

            const origSize = parseFloat(originalSize.textContent);
            const compSize = parseFloat(processedSize.textContent);
            const ratio = ((origSize - compSize) / origSize * 100).toFixed(2);
            document.getElementById('compressionRatio').textContent = `${ratio}%`;

            // Download
            downloadBtn.href = imageURL;
            downloadBtn.download = `exam_photo_${exam}.jpg`;

            compressionResults.classList.remove('d-none');
        })
        .catch(err => {
            alert('Error: ' + err.message);
        })
        .finally(() => {
            processBtn.disabled = false;
            processBtn.textContent = 'Process Image';
        });
    }
});
